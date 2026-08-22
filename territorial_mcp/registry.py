"""Registre d'indicateurs (§5) : contrat central du grain canonique.

Un indicateur = un fichier ``registry/{id}.yaml``. Aucun code à écrire pour en
ajouter un : le pipeline de la source concernée lit le registre, matérialise, et
``search_indicators`` l'expose immédiatement.

Le schéma est une union discriminée sur ``source`` : chaque source impose sa
propre section ``extraction``, validée par pydantic v2.

.. code-block:: yaml

    id: gdp_per_capita              # doit être égal au nom du fichier
    label: "PIB par habitant (prix courants)"
    unit: EUR_HAB
    source: eurostat                # eurostat | copernicus | osm
    frequency: A                    # A | Q | M | SNAPSHOT
    geo_levels: [NUTS0, NUTS1, NUTS2]
    nuts_vintage: 2024              # optionnel, défaut 2024
    description: "…"                # optionnel, indexé pour la recherche
    extraction:
      dataset: nama_10r_2gdp
      filters: { freq: A, unit: EUR_HAB }
      value_dim: geo

Validation en CI :

.. code-block:: console

    python -m territorial_mcp.registry validate

Interface pour les pipelines d'ingestion (lots 2 et 3)
------------------------------------------------------
.. code-block:: python

    from territorial_mcp import registry

    specs = registry.load_all(source="osm")   # list[IndicatorSpec], YAML validés
    for spec in specs:
        spec.id, spec.unit, spec.geo_levels, spec.extraction.tags
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from . import config, store

SOURCES = ("eurostat", "copernicus", "osm")
GeoLevel = Literal["NUTS0", "NUTS1", "NUTS2", "NUTS3", "CITY"]
LEVELS = ("NUTS0", "NUTS1", "NUTS2", "NUTS3", "CITY")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS registry (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS registry_fts USING fts5(id, label, description);
CREATE TABLE IF NOT EXISTS registry_meta (key TEXT PRIMARY KEY, value TEXT);
"""


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ------------------------------------------------------------- extractions

class EurostatExtraction(_Base):
    """Projection d'un cube SDMX Eurostat vers le grain canonique (§7.1)."""

    dataset: str
    filters: dict[str, str] = Field(default_factory=dict)
    value_dim: str = "geo"
    time_dim: str = "time"


class TemporalAgg(_Base):
    """Agrégation temporelle d'un produit raster avant statistique zonale."""

    months: list[int] = Field(default_factory=list)
    stat: Literal["mean", "min", "max", "sum"] = "mean"

    @field_validator("months")
    @classmethod
    def _check_months(cls, v: list[int]) -> list[int]:
        if any(m < 1 or m > 12 for m in v):
            raise ValueError("months doit contenir des entiers entre 1 et 12")
        return v


class CopernicusExtraction(_Base):
    """Statistique zonale d'un produit Copernicus (§7.2)."""

    product: str
    variable: str
    temporal_agg: TemporalAgg
    zonal_stat: Literal["mean", "min", "max", "sum", "count", "median"] = "mean"


class OsmTag(_Base):
    key: str
    value: str


class OsmExtraction(_Base):
    """Agrégation d'objets OpenStreetMap par zone (§7.3)."""

    tags: list[OsmTag] = Field(min_length=1)
    geometry: list[Literal["node", "way", "relation"]] = Field(min_length=1)
    aggregation: Literal["count"] = "count"


# -------------------------------------------------------------- indicateurs

class _IndicatorBase(_Base):
    id: str
    label: str
    unit: str
    frequency: Literal["A", "Q", "M", "SNAPSHOT"]
    geo_levels: list[GeoLevel] = Field(min_length=1)
    nuts_vintage: int = config.DEFAULT_NUTS_VINTAGE
    description: str | None = None

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v or not all(ch.isalnum() or ch == "_" for ch in v):
            raise ValueError("id doit être en minuscules alphanumériques avec '_'")
        return v

    @field_validator("nuts_vintage")
    @classmethod
    def _check_vintage(cls, v: int) -> int:
        allowed = (config.DEFAULT_NUTS_VINTAGE, config.PREVIOUS_NUTS_VINTAGE)
        if v not in allowed:
            raise ValueError(f"nuts_vintage doit valoir {' ou '.join(map(str, allowed))}")
        return v


class EurostatIndicator(_IndicatorBase):
    source: Literal["eurostat"]
    extraction: EurostatExtraction


class CopernicusIndicator(_IndicatorBase):
    source: Literal["copernicus"]
    extraction: CopernicusExtraction


class OsmIndicator(_IndicatorBase):
    source: Literal["osm"]
    extraction: OsmExtraction


IndicatorSpec = Annotated[
    Union[EurostatIndicator, CopernicusIndicator, OsmIndicator],
    Field(discriminator="source"),
]


class _SpecAdapter(BaseModel):
    spec: IndicatorSpec


def parse(payload: dict) -> EurostatIndicator | CopernicusIndicator | OsmIndicator:
    """Valide un dictionnaire brut et renvoie l'indicateur typé."""
    return _SpecAdapter(spec=payload).spec


class RegistryError(Exception):
    """Registre invalide : le message est destiné à la console / la CI."""


# ------------------------------------------------------------------ lecture

def _yaml_files(directory: Path | None = None) -> list[Path]:
    directory = directory or config.registry_dir()
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.yaml"))


def load_all(
    source: str | None = None, directory: Path | None = None
) -> list[EurostatIndicator | CopernicusIndicator | OsmIndicator]:
    """Charge et valide tout le registre. Lève :class:`RegistryError` si invalide."""
    specs = []
    errors: list[str] = []
    for path in _yaml_files(directory):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{path.name} : YAML illisible ({exc})")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{path.name} : le document doit être un mapping YAML")
            continue
        if payload.get("id") != path.stem:
            errors.append(
                f"{path.name} : id '{payload.get('id')}' ≠ nom de fichier '{path.stem}'"
            )
            continue
        try:
            specs.append(parse(payload))
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(x) for x in err["loc"] if x != "spec")
                errors.append(f"{path.name} : {loc or '<racine>'} — {err['msg']}")
    if errors:
        raise RegistryError("\n".join(errors))
    ids = [s.id for s in specs]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise RegistryError(f"ids en double : {', '.join(sorted(duplicates))}")
    return [s for s in specs if source is None or s.source == source]


def registry_fingerprint(directory: Path | None = None) -> str:
    """Empreinte du registre sur disque (nom + mtime + taille de chaque YAML)."""
    parts = []
    for path in _yaml_files(directory):
        st = path.stat()
        parts.append(f"{path.name}:{int(st.st_mtime)}:{st.st_size}")
    return "|".join(parts)


# ------------------------------------------------------------ matérialisation

def _conn():
    conn = store.connect()
    conn.executescript(_SCHEMA)
    return conn


def materialize(directory: Path | None = None) -> int:
    """Écrit le registre validé dans SQLite (`registry` + FTS5). Idempotent."""
    specs = load_all(directory=directory)
    with _conn() as c:
        c.execute("DELETE FROM registry")
        c.execute("DELETE FROM registry_fts")
        c.executemany(
            "INSERT INTO registry VALUES (?,?,?)",
            [(s.id, s.source, s.model_dump_json()) for s in specs],
        )
        c.executemany(
            "INSERT INTO registry_fts VALUES (?,?,?)",
            [(s.id, s.label, s.description or "") for s in specs],
        )
        c.execute(
            "INSERT OR REPLACE INTO registry_meta VALUES ('fingerprint', ?)",
            (registry_fingerprint(directory),),
        )
    return len(specs)


def ensure_materialized() -> None:
    """Re-matérialise le registre si les YAML ont changé depuis la dernière fois.

    Appelé par le serveur : le registre reste utilisable sans lancer de sync.
    """
    fingerprint = registry_fingerprint()
    with _conn() as c:
        row = c.execute(
            "SELECT value FROM registry_meta WHERE key='fingerprint'"
        ).fetchone()
    if row is not None and row[0] == fingerprint:
        return
    try:
        materialize()
    except RegistryError:
        # Un registre invalide ne doit pas empêcher le serveur de servir
        # ce qui a déjà été matérialisé.
        pass


def get(indicator_id: str):
    """Un indicateur matérialisé, ou ``None``."""
    with _conn() as c:
        row = c.execute(
            "SELECT payload FROM registry WHERE id = ?", (indicator_id,)
        ).fetchone()
    return parse(json.loads(row[0])) if row else None


def all_ids() -> list[str]:
    with _conn() as c:
        return [r[0] for r in c.execute("SELECT id FROM registry ORDER BY id")]


def search(query: str, source: str = "", limit: int = 10) -> list[dict]:
    """Recherche FTS5 sur id + label + description, filtre optionnel par source."""
    where, args = [], []
    if query.strip():
        terms = " OR ".join(f'"{t}"*' for t in query.split())
        sql = (
            "SELECT r.id, r.payload FROM registry_fts f JOIN registry r ON r.id = f.id "
            "WHERE registry_fts MATCH ?"
        )
        args.append(terms)
    else:
        sql = "SELECT r.id, r.payload FROM registry r WHERE 1=1"
    if source:
        where.append("r.source = ?")
        args.append(source)
    if where:
        sql += " AND " + " AND ".join(where)
    sql += " ORDER BY rank" if query.strip() else " ORDER BY r.id"
    sql += " LIMIT ?"
    args.append(max(1, min(limit, 50)))
    with _conn() as c:
        try:
            rows = c.execute(sql, args).fetchall()
        except Exception:
            return []
    return [json.loads(payload) for _, payload in rows]


# ---------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m territorial_mcp.registry",
        description="Validation et matérialisation du registre d'indicateurs",
    )
    parser.add_argument(
        "command", choices=("validate", "materialize", "list"),
        help="validate : contrôle les YAML ; materialize : écrit dans SQLite ; "
             "list : affiche le registre",
    )
    args = parser.parse_args(argv)
    try:
        specs = load_all()
    except RegistryError as exc:
        print(f"Registre invalide ({config.registry_dir()}) :\n{exc}", file=sys.stderr)
        return 1
    if args.command == "validate":
        print(f"Registre valide : {len(specs)} indicateurs dans {config.registry_dir()}.")
        return 0
    if args.command == "materialize":
        n = materialize()
        print(f"{n} indicateurs matérialisés dans {config.db_path()}.")
        return 0
    for spec in specs:
        print(f"{spec.id} | {spec.label} | {spec.unit} | {spec.frequency} | "
              f"{','.join(spec.geo_levels)} | {spec.source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
