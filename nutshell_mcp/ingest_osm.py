"""Pipeline OpenStreetMap (§7.3) : extraits Geofabrik → POI → comptages par zone.

Dérisqué par un spike technique (voir ``spike-report.md``, section A) exécuté
réellement sur l'extrait Luxembourg. Trois pièges y ont été identifiés et sont
traités ici :

1. ``osmium tags-filter`` : ``-R`` signifie *omettre* les objets référencés,
   pas l'inverse. On ne l'utilise donc jamais — sans lui, les nœuds portant la
   géométrie des ways/relations sont conservés automatiquement.
2. ``osmium export`` matche « n'importe quel tag » : il exporte aussi des
   nœuds référencés porteurs d'un tag non ciblé (ex. ``barrier=gate`` sur le
   portail d'une école). On refiltre donc en aval sur ``properties[clé] ==
   valeur`` (égalité exacte, pas simple présence de la clé) avant d'écrire le
   GeoParquet — deux niveaux de filtrage par égalité : ici sur l'union de
   toutes les paires (clé, valeur) du registre, puis par indicateur précis à
   l'agrégation (:func:`_aggregate`, pour distinguer par ex. ``amenity=school``
   d'``amenity=hospital`` au sein du même fichier).
3. Débordement transfrontalier : un extrait pays Geofabrik déborde toujours
   un peu sur les pays voisins. Sans clip, ingérer deux extraits limitrophes
   (LU + BE) compterait deux fois les POI proches de la frontière. On ne
   retient donc, pour un extrait donné, que les POI tombant dans des zones
   dont le préfixe pays du ``geo_code`` correspond au pays déclaré de
   l'extrait (voir :data:`GEOFABRIK_COUNTRY`).

Séquence par synchronisation (§7.3, appliquée à l'union des extraits
configurés) :

1. Périmètre : liste d'extraits Geofabrik dans ``NUTSHELL_OSM_EXTRACTS``
   (défaut : ``europe/luxembourg`` seul — jamais un gros extrait par défaut).
2. Téléchargement ``httpx`` en streaming, vérifié contre le sidecar ``.md5``.
   Optimisation : le sidecar (quelques octets) est comparé à l'état local
   *avant* tout téléchargement du ``.pbf`` (potentiellement volumineux) — un
   md5 inchangé implique un contenu inchangé, donc un ``timestamp`` d'en-tête
   inchangé, sans avoir à retélécharger pour le vérifier.
3. Signal de fraîcheur définitif une fois le fichier téléchargé : ``osmium
   fileinfo -e -g header.option.timestamp`` (timestamp embarqué dans le
   fichier, plus fiable que le ``Last-Modified`` HTTP qui dépend du CDN
   Geofabrik).
4. Une seule passe ``osmium tags-filter`` combinant les expressions
   ``n/k=v w/k=v r/k=v`` de tous les indicateurs OSM du registre, puis
   ``osmium export`` en GeoJSON (points et polygones uniquement), puis
   refiltrage DuckDB et conversion en GeoParquet
   (``mirror/osm/poi_{extrait}.parquet``).
5. Jointure spatiale ``ST_Within(centroïde(poi), zone)`` par niveau
   (``spec.geo_levels``), avec le clip transfrontalier du point 3 ci-dessus,
   et zéro explicite pour toute zone du périmètre sans POI correspondant.
6. Écriture de la partition canonique (union de tous les extraits
   configurés), ``quality = "osm_completeness_unknown"`` systématique.

Limite connue, documentée mais non traitée (voir ``DECISIONS.md``, section
« Lot 2 — OSM ») : les doublons node/way d'une même entité physique (ex. un
hôpital mappé à la fois comme nœud et comme empreinte de bâtiment) ne sont pas
dédupliqués — aucun tag OSM standard ne relie formellement les deux
représentations.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import duckdb
import httpx

from . import config, geo, indicators, store
from .sync import SyncReport

GEOFABRIK_BASE = "https://download.geofabrik.de"

#: Extraits synchronisés par défaut si `NUTSHELL_OSM_EXTRACTS` est absent.
#: Volontairement restreint à un petit pays : ne jamais déclencher un gros
#: téléchargement par accident (§7.3, note d'environnement).
DEFAULT_EXTRACTS = ("europe/luxembourg",)

#: Préfixe pays (convention NUTS/Eurostat, PAS l'ISO 3166-1) par nom court
#: d'extrait Geofabrik (dernier segment du chemin, ex. "luxembourg" pour
#: "europe/luxembourg"). La Grèce (EL, pas GR) et le Royaume-Uni (UK, pas GB)
#: illustrent pourquoi la convention NUTS est nécessaire : le clip
#: transfrontalier compare ce code au préfixe du `geo_code` (§4), qui suit
#: toujours NUTS. Seuls luxembourg/belgium sont exercés en pratique
#: (contrainte d'environnement) ; les autres entrées sont fournies pour
#: l'extensibilité future du périmètre.
GEOFABRIK_COUNTRY = {
    "albania": "AL", "andorra": "AD", "austria": "AT", "belarus": "BY",
    "belgium": "BE", "bosnia-herzegovina": "BA", "bulgaria": "BG",
    "croatia": "HR", "cyprus": "CY", "czech-republic": "CZ", "denmark": "DK",
    "estonia": "EE", "finland": "FI", "france": "FR", "georgia": "GE",
    "germany": "DE", "greece": "EL", "hungary": "HU", "iceland": "IS",
    "ireland-and-northern-ireland": "IE", "italy": "IT", "kosovo": "XK",
    "latvia": "LV", "liechtenstein": "LI", "lithuania": "LT",
    "luxembourg": "LU", "macedonia": "MK", "malta": "MT", "moldova": "MD",
    "monaco": "MC", "montenegro": "ME", "netherlands": "NL", "norway": "NO",
    "poland": "PL", "portugal": "PT", "romania": "RO", "serbia": "RS",
    "slovakia": "SK", "slovenia": "SI", "spain": "ES", "sweden": "SE",
    "switzerland": "CH", "turkey": "TR", "ukraine": "UA",
    "united-kingdom": "UK",
}

#: Lettre de préfixe `osmium tags-filter` par type de géométrie OSM.
_OSMIUM_PREFIX = {"node": "n", "way": "w", "relation": "r"}

_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


# ------------------------------------------------------------------- config

def configured_extracts() -> list[str]:
    """Extraits Geofabrik à synchroniser (``continent/pays``), depuis l'environnement.

    ``NUTSHELL_OSM_EXTRACTS="europe/luxembourg,europe/belgium"``. Défaut :
    :data:`DEFAULT_EXTRACTS`.
    """
    raw = os.environ.get("NUTSHELL_OSM_EXTRACTS", "")
    if not raw.strip():
        return list(DEFAULT_EXTRACTS)
    return [e.strip() for e in raw.split(",") if e.strip()]


def _extract_name(extract: str) -> str:
    """Nom court d'un extrait (``europe/luxembourg`` → ``luxembourg``).

    Utilisé pour les noms de fichiers et les clés `sync_state`. On suppose
    l'absence de collision entre continents (non pertinent : périmètre Europe
    uniquement, §7.3).
    """
    return extract.rsplit("/", 1)[-1]


def _extract_country(name: str) -> str:
    country = GEOFABRIK_COUNTRY.get(name)
    if country is None:
        raise RuntimeError(
            f"pays inconnu pour l'extrait Geofabrik '{name}' : ajouter une entrée "
            f"dans ingest_osm.GEOFABRIK_COUNTRY (code NUTS/Eurostat, pas ISO)."
        )
    return country


# ------------------------------------------------------------ osmium (§7.3)

def _require_osmium() -> None:
    if shutil.which("osmium") is None:
        raise RuntimeError(
            "outil 'osmium' introuvable dans le PATH. Installer : brew install osmium-tool"
        )


def _tag_pairs(specs: list) -> list[tuple[str, str]]:
    """Paires (clé, valeur) distinctes de tous les indicateurs OSM du registre."""
    pairs: set[tuple[str, str]] = set()
    for spec in specs:
        for tag in spec.extraction.tags:
            pairs.add((tag.key, tag.value))
    return sorted(pairs)


def _tag_filter_expressions(specs: list) -> list[str]:
    """Expressions `osmium tags-filter` combinées de tous les indicateurs OSM.

    Une seule passe pour tout le registre (§7.3 point 2) : chaque expression
    est ``<n|w|r>/<clé>=<valeur>``. Jamais ``-R`` (voir docstring de module).
    """
    exprs: set[str] = set()
    for spec in specs:
        for gtype in spec.extraction.geometry:
            prefix = _OSMIUM_PREFIX[gtype]
            for tag in spec.extraction.tags:
                exprs.add(f"{prefix}/{tag.key}={tag.value}")
    return sorted(exprs)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"échec de '{' '.join(cmd[:2])}' : {result.stderr.strip() or result.stdout.strip()}"
        )


def _parse_timestamp(raw: str) -> str:
    """Valide la sortie de `osmium fileinfo -g header.option.timestamp`.

    Fonction pure (testable sur une sortie figée sans invoquer osmium).
    """
    ts = raw.strip()
    if not _TIMESTAMP_RE.fullmatch(ts):
        raise RuntimeError(
            f"timestamp d'en-tête osmium inattendu ou absent (sortie : {raw!r}). "
            f"L'extrait Geofabrik est peut-être corrompu ou incomplet."
        )
    return ts


def _fileinfo_timestamp(pbf_path: Path) -> str:
    result = subprocess.run(
        ["osmium", "fileinfo", "-e", "-g", "header.option.timestamp", str(pbf_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"'osmium fileinfo' a échoué : {result.stderr.strip()}")
    return _parse_timestamp(result.stdout)


# --------------------------------------------------------------- téléchargement

def _fetch_md5(client: httpx.Client, url: str) -> str:
    r = client.get(url)
    r.raise_for_status()
    return r.text.strip().split()[0]


def _download_pbf(client: httpx.Client, url: str, dest: Path, expected_md5: str) -> None:
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5()  # vérification d'intégrité (fournie par Geofabrik), pas cryptographique
    with client.stream("GET", url) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
                digest.update(chunk)
    if digest.hexdigest() != expected_md5:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"md5 invalide pour {dest.name} (attendu {expected_md5}, obtenu {digest.hexdigest()})"
        )
    tmp.replace(dest)


# ---------------------------------------------------------------- par extrait

def _sync_extract(
    extract: str, full: bool, tag_exprs: list[str], tag_pairs: list[tuple[str, str]],
    report: SyncReport,
) -> dict[str, Any]:
    """Synchronise un extrait : téléchargement, filtrage, GeoParquet des POI.

    ``extract`` est le chemin Geofabrik complet (``europe/luxembourg``).
    Renvoie ``{"country", "timestamp", "month", "poi_path", "changed"}``. Ne
    lève pas : les erreurs sont consignées dans ``report`` par l'appelant
    (:func:`sync`), qui capture les exceptions de cette fonction.
    """
    name = _extract_name(extract)
    country = _extract_country(name)
    poi_path = config.mirror_dir() / "osm" / f"poi_{name}.parquet"
    md5_key = f"extract:{name}:md5"
    ts_key = f"extract:{name}:timestamp"
    stored_md5 = store.get_sync_state("osm", md5_key)
    stored_ts = store.get_sync_state("osm", ts_key)

    pbf_url = f"{GEOFABRIK_BASE}/{extract}-latest.osm.pbf"
    md5_url = pbf_url + ".md5"

    if config.offline():
        if poi_path.exists() and stored_ts:
            report.unchanged(f"extract:{name}")
            return {"country": country, "timestamp": stored_ts, "month": stored_ts[:7],
                    "poi_path": poi_path, "changed": False}
        raise RuntimeError(
            f"mode hors ligne actif et l'extrait '{name}' n'est pas encore synchronisé ; "
            f"lancer sync --source osm sans NUTSHELL_OFFLINE=1"
        )

    with httpx.Client(timeout=600, follow_redirects=True) as client:
        remote_md5 = _fetch_md5(client, md5_url)
        if not full and remote_md5 == stored_md5 and poi_path.exists() and stored_ts:
            report.unchanged(f"extract:{name}")
            return {"country": country, "timestamp": stored_ts, "month": stored_ts[:7],
                    "poi_path": poi_path, "changed": False}

        work = config.work_dir() / "osm"
        work.mkdir(parents=True, exist_ok=True)
        pbf_path = work / f"{name}.osm.pbf"
        filtered_pbf = work / f"{name}.filtered.osm.pbf"
        filtered_geojson = work / f"{name}.filtered.geojson"
        try:
            _download_pbf(client, pbf_url, pbf_path, remote_md5)
            timestamp = _fileinfo_timestamp(pbf_path)
            _run(["osmium", "tags-filter", "-o", str(filtered_pbf), str(pbf_path),
                  *tag_exprs, "--overwrite"])
            _run(["osmium", "export", "-f", "geojson", "-a", "type,id",
                  "--geometry-types", "point,polygon",
                  "-o", str(filtered_geojson), str(filtered_pbf), "--overwrite"])
            n = _refilter_to_geoparquet(filtered_geojson, tag_pairs, poi_path)
        finally:
            # work/ est purgeable : le .pbf source (le plus volumineux) est
            # re-téléchargeable, seul le GeoParquet filtré (quelques Ko-Mo) est pérenne.
            for tmp in (pbf_path, filtered_pbf, filtered_geojson):
                tmp.unlink(missing_ok=True)

    store.set_sync_state("osm", md5_key, remote_md5)
    store.set_sync_state("osm", ts_key, timestamp)
    report.updated(f"extract:{name}", f"{n:,} POI, en-tête {timestamp}")
    return {"country": country, "timestamp": timestamp, "month": timestamp[:7],
            "poi_path": poi_path, "changed": True}


def _refilter_to_geoparquet(
    geojson_path: Path, tag_pairs: list[tuple[str, str]], out_path: Path
) -> int:
    """Refiltre le GeoJSON exporté sur `properties[clé]==valeur` puis écrit du GeoParquet.

    Piège n°2 du spike : `osmium export` matche "any tag" et exporte aussi des
    nœuds référencés porteurs d'un tag non ciblé (ex. `barrier=gate` sur le
    portail d'une école référencée par un way). On ne garde que les objets
    dont au moins une des paires (clé, valeur) demandées par le registre est
    vérifiée par égalité exacte — pas simple présence de la clé.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"CREATE TABLE poi_raw AS SELECT * FROM ST_Read('{geojson_path.as_posix()}')")
    existing = {d[0] for d in con.execute("SELECT * FROM poi_raw LIMIT 0").description}
    clauses: list[str] = []
    params: list[str] = []
    for key, value in tag_pairs:
        if key in existing:
            clauses.append(f'"{key}" = ?')
            params.append(value)
    if not clauses:
        con.execute("CREATE TABLE poi AS SELECT * FROM poi_raw WHERE 1=0")
    else:
        where_sql = " OR ".join(clauses)
        con.execute(
            f"""
            CREATE TABLE poi AS
            SELECT * EXCLUDE (geom),
                   ST_SetCRS(
                       CASE WHEN ST_GeometryType(geom) = 'POINT'
                            THEN geom ELSE ST_Centroid(geom) END,
                       'EPSG:4326'
                   ) AS geom
            FROM poi_raw
            WHERE {where_sql}
            """,
            params,
        )
    n = con.execute("SELECT count(*) FROM poi").fetchone()[0]
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    con.execute(f"COPY poi TO '{tmp.as_posix()}' (FORMAT PARQUET)")
    con.close()
    tmp.replace(out_path)
    return n


# -------------------------------------------------------------- agrégation

def _aggregate(spec: Any, extract_info: dict[str, dict], snapshot_time: str) -> list[dict]:
    """Comptage POI par zone pour un indicateur, union de tous les extraits.

    Zéro explicite pour toute zone du périmètre (pays couvert par au moins un
    extrait configuré) sans POI correspondant ; les zones hors périmètre
    n'apparaissent pas du tout (§7.3 point 5). Clip transfrontalier : un POI
    d'un extrait n'est compté que dans une zone dont le pays correspond à
    celui de l'extrait (piège n°3 du spike). Plusieurs tags du même indicateur
    (``extraction.tags``) sont combinés en OR.
    """
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    in_scope_countries = {info["country"] for info in extract_info.values()}
    rows: list[dict] = []

    for level in spec.geo_levels:
        geom_path = geo.geometry_path(level)
        if not geom_path.exists():
            raise RuntimeError(
                f"géométries absentes pour {level} ({geom_path}) ; "
                f"lancer : python -m nutshell_mcp.sync --source geo"
            )
        code_prop = geo.geometry_code_property(level)
        target_codes = {
            z["geo_code"] for z in geo.zones(level) if z["geo_code"][:2] in in_scope_countries
        }
        counts: dict[str, int] = dict.fromkeys(target_codes, 0)

        table = f"zones_{level.lower()}"
        con.execute(
            f'CREATE OR REPLACE TABLE {table} AS '
            f'SELECT "{code_prop}" AS geo_code, ST_SetCRS(geom, \'EPSG:4326\') AS geom '
            f"FROM ST_Read('{geom_path.as_posix()}')"
        )

        for info in extract_info.values():
            poi_path = info["poi_path"]
            if not poi_path.exists():
                continue
            cols = {
                d[0] for d in
                con.execute(f"SELECT * FROM read_parquet('{poi_path.as_posix()}') LIMIT 0")
                .description
            }
            clauses, params = [], []
            for tag in spec.extraction.tags:
                if tag.key in cols:
                    clauses.append(f'p."{tag.key}" = ?')
                    params.append(tag.value)
            if not clauses:
                continue
            where_sql = " OR ".join(clauses)
            # `::GEOMETRY` : un GeoParquet sans aucune ligne perd le typage GEOMETRY de
            # la colonne (repli sur BLOB) — inoffensif mais nécessite un cast explicite
            # avant `ST_SetCRS`. `ST_SetCRS` (sans transformation) aligne la géométrie
            # POI sur la même étiquette CRS que la géométrie de zone lue par `ST_Read`
            # (EPSG:4326 vs OGC:CRS84 : même WGS84 lon/lat, étiquette différente selon
            # la source, sans quoi `ST_Within` refuse de comparer les deux).
            sql = f"""
                SELECT z.geo_code, count(*)
                FROM read_parquet('{poi_path.as_posix()}') p
                JOIN {table} z ON ST_Within(ST_SetCRS(p.geom::GEOMETRY, 'EPSG:4326'), z.geom)
                WHERE ({where_sql}) AND substr(z.geo_code, 1, 2) = ?
                GROUP BY z.geo_code
            """
            for geo_code, n in con.execute(sql, [*params, info["country"]]).fetchall():
                if geo_code in counts:
                    counts[geo_code] += n

        rows.extend(
            {
                "geo_code": geo_code, "time": snapshot_time, "value": float(n),
                "quality": "osm_completeness_unknown",
            }
            for geo_code, n in counts.items()
        )
    con.close()
    return rows


# ------------------------------------------------------------------- entrée

def sync(specs: list, full: bool) -> SyncReport:
    """Point d'entrée attendu par `nutshell_mcp.sync` (contrat de `sync.py`)."""
    report = SyncReport("osm")
    if not specs:
        report.note("aucun indicateur osm dans le registre")
        return report
    try:
        _require_osmium()
    except RuntimeError as exc:
        report.failed("osmium", str(exc))
        return report

    tag_exprs = _tag_filter_expressions(specs)
    tag_pairs = _tag_pairs(specs)
    extract_info: dict[str, dict] = {}
    for extract in configured_extracts():
        name = _extract_name(extract)
        try:
            extract_info[name] = _sync_extract(extract, full, tag_exprs, tag_pairs, report)
        except Exception as exc:
            report.failed(f"extract:{name}", str(exc))

    if not extract_info:
        report.failed("osm", "aucun extrait Geofabrik synchronisé avec succès")
        return report

    global_month = max(info["month"] for info in extract_info.values())
    global_source_date = f"extrait {global_month}"
    any_changed = full or any(info["changed"] for info in extract_info.values())

    for spec in specs:
        forced = full or any_changed or indicators.materialized_info(spec.id) is None
        if not forced:
            report.unchanged(spec.id)
            continue
        try:
            rows = _aggregate(spec, extract_info, global_month)
            n = indicators.write_partition(spec, rows, source_date=global_source_date)
            report.updated(spec.id, f"{n:,} zones ({global_month})")
        except Exception as exc:
            report.failed(spec.id, str(exc))
    return report
