"""Orchestration des pipelines d'ingestion (§7.4).

Point d'entrée unique, idempotent, conçu pour un cron quotidien (Eurostat),
hebdomadaire (Copernicus) et mensuel (OSM + référentiel geo) :

.. code-block:: console

    python -m nutshell_mcp.sync --source geo
    python -m nutshell_mcp.sync --source eurostat
    python -m nutshell_mcp.sync --source osm --indicators hospitals_count
    python -m nutshell_mcp.sync --source all --full

Un échec sur un indicateur n'interrompt jamais le lot : le rapport final liste
mis à jour / inchangés / échecs avec la raison (§7).

Contrat pour les pipelines des lots 2 et 3
------------------------------------------
Un pipeline de source vit dans son propre module — ``nutshell_mcp.ingest_osm``
pour OSM, ``nutshell_mcp.ingest_cds`` pour Copernicus — importé
paresseusement ici, de sorte que le serveur et les autres pipelines démarrent
sans les extras lourds. Chaque module doit exposer exactement :

.. code-block:: python

    def sync(specs: list[IndicatorSpec], full: bool) -> SyncReport: ...

où ``specs`` est la liste des indicateurs du registre déclarant cette source
(déjà filtrée par ``--indicators`` le cas échéant) et ``full`` demande une
re-matérialisation complète en ignorant les signaux de fraîcheur locaux.

Tout ce dont un pipeline a besoin est fourni par le socle :

===============================  ====================================================
Besoin                           Appel
===============================  ====================================================
Specs du registre                ``registry.load_all(source="osm")``
Fichier de géométries            ``geo.geometry_path("NUTS3")`` → GeoJSON 4326, 01M
Nom de la propriété du code      ``geo.geometry_code_property("NUTS3")`` → ``NUTS_ID``
Liste des zones d'un niveau      ``geo.zones("NUTS3")`` → dicts ``geo_code``/``name``
Écrire une partition             ``indicators.write_partition(spec, rows, source_date)``
Lire / écrire l'état de sync     ``store.get_sync_state(src, key)`` / ``set_sync_state``
Répertoire temporaire            ``config.work_dir()``
===============================  ====================================================

Le pipeline construit son :class:`SyncReport` en appelant ``report.updated(id)``,
``report.unchanged(id)`` ou ``report.failed(id, raison)`` ; il ne lève pas
d'exception pour un indicateur en échec.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys
from dataclasses import dataclass, field

from . import config, geo, indicators, registry

SOURCES = ("geo", "eurostat", "copernicus", "osm")
#: Modules d'ingestion attendus pour les sources non natives.
PIPELINE_MODULES = {
    "osm": "nutshell_mcp.ingest_osm",
    "copernicus": "nutshell_mcp.ingest_cds",
}


@dataclass
class SyncReport:
    """Compte-rendu d'un lot d'ingestion pour une source."""

    source: str
    updated_items: list[str] = field(default_factory=list)
    unchanged_items: list[str] = field(default_factory=list)
    failed_items: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def updated(self, item: str, detail: str = "") -> None:
        self.updated_items.append(f"{item} ({detail})" if detail else item)

    def unchanged(self, item: str) -> None:
        self.unchanged_items.append(item)

    def failed(self, item: str, reason: str) -> None:
        self.failed_items.append((item, reason))

    def note(self, message: str) -> None:
        self.notes.append(message)

    @property
    def ok(self) -> bool:
        return not self.failed_items

    def render(self) -> str:
        lines = [f"[{self.source}] {len(self.updated_items)} mis à jour, "
                 f"{len(self.unchanged_items)} inchangés, "
                 f"{len(self.failed_items)} échecs"]
        for item in self.updated_items:
            lines.append(f"  ✓ {item}")
        for item, reason in self.failed_items:
            lines.append(f"  ✗ {item} : {reason}")
        for note in self.notes:
            lines.append(f"  · {note}")
        return "\n".join(lines)


# ------------------------------------------------------------------ sources

def sync_geo(full: bool = False) -> SyncReport:
    """Référentiel géographique GISCO : géométries, table `geo`, correspondances."""
    report = SyncReport("geo")
    try:
        result = geo.ingest(force=full)
    except Exception as exc:
        report.failed("gisco", str(exc))
        return report
    for name in result["updated"]:
        report.updated(name)
    for name in result["unchanged"]:
        report.unchanged(name)
    for name, reason in result["failed"]:
        report.failed(name, reason)
    report.note(f"{result['zones']} zones dans la table geo, "
                f"{result['changes']} correspondances de millésime")
    return report


async def sync_eurostat(specs: list, full: bool, rate: float) -> SyncReport:
    """Miroir natif des datasets requis par le registre, puis projection (§7.1).

    Piloté par le TOC : un dataset dont le « last update of data » n'a pas bougé
    n'est pas retéléchargé, mais ses indicateurs sont reprojetés si leur
    partition canonique manque.
    """
    from . import eurostat_client as api
    from . import mirror, project_eurostat, store

    report = SyncReport("eurostat")
    if not specs:
        report.note("aucun indicateur eurostat dans le registre")
        return report

    datasets: dict[str, list] = {}
    for spec in specs:
        datasets.setdefault(spec.extraction.dataset, []).append(spec)

    try:
        toc = await api.fetch_toc()
        store.replace_catalog(toc)
        toc_by_code = {}
        for row in toc:
            toc_by_code.setdefault(row["code"], row)
    except Exception as exc:
        if not config.offline():
            report.failed("toc", f"catalogue Eurostat injoignable ({exc})")
        toc_by_code = {}

    import time as _time

    for dataset, dataset_specs in datasets.items():
        toc_row = toc_by_code.get(dataset)
        info = mirror.mirror_info(dataset)
        needs_download = toc_row is not None and (
            full or info is None or info["last_update"] != toc_row["last_update"]
        )
        if needs_download and not config.offline():
            t0 = _time.time()
            try:
                n = await mirror.sync_dataset(dataset, toc_row["last_update"])
                report.updated(dataset, f"{n:,} lignes natives")
            except Exception as exc:
                report.failed(dataset, str(exc))
                continue
            await asyncio.sleep(max(0.0, 1.0 / rate - (_time.time() - t0)))
        elif info is None:
            report.failed(
                dataset,
                "miroir natif absent et téléchargement impossible "
                "(mode offline ou dataset absent du TOC)",
            )
            continue
        else:
            report.unchanged(dataset)

        for spec in dataset_specs:
            try:
                rows = project_eurostat.project(spec)
                report.updated(spec.id, f"{rows:,} lignes canoniques")
            except Exception as exc:
                report.failed(spec.id, str(exc))
    return report


def sync_pipeline(source: str, specs: list, full: bool) -> SyncReport:
    """Délègue à ``ingest_osm`` / ``ingest_cds``, absents tant que le lot n'est pas livré."""
    report = SyncReport(source)
    module_name = PIPELINE_MODULES[source]
    lot = "lot 2" if source == "osm" else "lot 3"
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        if module_name.split(".")[-1] in str(exc):
            report.note(
                f"pipeline non implémenté ({lot}) : le module {module_name} n'existe "
                f"pas encore. Les {len(specs)} indicateur(s) '{source}' du registre "
                f"restent non matérialisés."
            )
        else:
            report.failed(
                module_name,
                f"dépendance manquante ({exc}) — installer les extras : "
                f"pip install -e \".[{source if source == 'osm' else 'copernicus'}]\"",
            )
        return report
    if not hasattr(module, "sync"):
        report.failed(module_name, "le module n'expose pas sync(specs, full)")
        return report
    if not specs:
        report.note(f"aucun indicateur '{source}' dans le registre")
        return report
    try:
        result = module.sync(specs, full)
    except Exception as exc:
        report.failed(source, str(exc))
        return report
    return result if isinstance(result, SyncReport) else report


# --------------------------------------------------------------------- main

def run(source: str, indicator_ids: list[str] | None, full: bool, rate: float) -> int:
    """Exécute la synchronisation demandée et affiche le rapport. Renvoie un code retour."""
    config.ensure_dirs()
    try:
        registry.materialize()
    except registry.RegistryError as exc:
        print(f"Registre invalide, synchronisation annulée :\n{exc}", file=sys.stderr)
        return 1

    selected = registry.load_all()
    if indicator_ids:
        known = {s.id for s in selected}
        unknown = [i for i in indicator_ids if i not in known]
        if unknown:
            print(
                f"Indicateur(s) inconnu(s) : {', '.join(unknown)}. "
                f"Registre : {', '.join(sorted(known))}",
                file=sys.stderr,
            )
            return 1
        selected = [s for s in selected if s.id in indicator_ids]

    targets = SOURCES if source == "all" else (source,)
    reports: list[SyncReport] = []
    for target in targets:
        specs = [s for s in selected if s.source == target]
        if target == "geo":
            if source == "all" or not indicator_ids:
                reports.append(sync_geo(full))
        elif target == "eurostat":
            reports.append(asyncio.run(sync_eurostat(specs, full, rate)))
        else:
            reports.append(sync_pipeline(target, specs, full))

    print()
    for report in reports:
        print(report.render())
    materialized = indicators.materialized_ids()
    print(
        f"\nTable canonique : {len(materialized)} indicateurs matérialisés "
        f"({', '.join(materialized) if materialized else 'aucun'}) dans "
        f"{config.indicators_dir()}"
    )
    return 0 if all(r.ok for r in reports) else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m nutshell_mcp.sync",
        description="Synchronisation des données territoriales (idempotente)",
    )
    parser.add_argument(
        "--source", default="all", choices=(*SOURCES, "all"),
        help="source à synchroniser (défaut : all)",
    )
    parser.add_argument(
        "--indicators", default="",
        help="restreint à ces ids d'indicateurs, séparés par des virgules",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="ignore les signaux de fraîcheur et re-matérialise tout",
    )
    parser.add_argument("--rate", type=float, default=2.0,
                        help="requêtes Eurostat par seconde (défaut 2)")
    args = parser.parse_args(argv)
    ids = [i.strip() for i in args.indicators.split(",") if i.strip()]
    return run(args.source, ids or None, args.full, args.rate)


if __name__ == "__main__":
    # Exécuté par `python -m nutshell_mcp.sync`, ce fichier est chargé sous le nom
    # `__main__` ; un pipeline qui fait `from .sync import SyncReport` déclencherait
    # alors un *second* import du module, avec une classe SyncReport distincte — et
    # le rapport renvoyé serait rejeté par le `isinstance` de sync_pipeline. On
    # délègue donc à l'unique module canonique.
    from nutshell_mcp.sync import main as _main

    raise SystemExit(_main())
