"""Table canonique `indicators` (§6.1) : zone × indicateur × période.

Grain unique de toute interrogation croisée (P4). Neuf colonnes, partitionnement
Hive par indicateur, compression zstd :

``mirror/indicators/indicator={id}/part-0.parquet``

| colonne       | type      | description                                        |
|---------------|-----------|----------------------------------------------------|
| ``indicator`` | string    | id du registre                                     |
| ``geo_code``  | string    | code de zone du référentiel                        |
| ``time``      | string    | période Eurostat (``2023``, ``2023-Q1``, ``2023-01``)|
| ``value``     | double    | valeur                                             |
| ``unit``      | string    | unité dénormalisée depuis le registre              |
| ``quality``   | string    | vide, flag Eurostat, ``recoded``, ``partial_coverage``… |
| ``source``    | string    | ``eurostat`` / ``copernicus`` / ``osm``            |
| ``source_date``| string   | date des données à la source                       |
| ``ingested_at``| timestamp| date de matérialisation locale                     |

La colonne ``indicator`` est portée à la fois par le chemin (partition Hive) et
par le fichier : DuckDB peut donc élaguer par partition **et** la lecture d'un
seul fichier reste auto-suffisante.

Interface pour les pipelines d'ingestion (lots 2 et 3)
------------------------------------------------------
Un pipeline n'écrit jamais de Parquet lui-même : il appelle
:func:`write_partition` avec la spec du registre et les lignes calculées.

.. code-block:: python

    from nutshell_mcp import indicators, registry

    spec = registry.get("hospitals_count")
    rows = [
        {"geo_code": "FRK2", "time": "2026-08", "value": 41.0,
         "quality": "osm_completeness_unknown"},
        ...
    ]
    n = indicators.write_partition(spec, rows, source_date="2026-08-01")

``rows`` accepte une liste de dictionnaires, un ``pyarrow.Table`` ou tout objet
exposant ``.fetchall()`` / ``.arrow()`` (relation DuckDB). Les colonnes
``indicator``, ``unit``, ``source``, ``source_date`` et ``ingested_at`` sont
remplies par la fonction ; ``quality`` vaut la chaîne vide si absente.
L'écriture est atomique : un répertoire ``.tmp`` est rempli puis renommé, un
indicateur n'est donc jamais lisible à moitié re-matérialisé.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import config

#: Schéma exact de la table canonique.
SCHEMA = pa.schema(
    [
        pa.field("indicator", pa.string()),
        pa.field("geo_code", pa.string()),
        pa.field("time", pa.string()),
        pa.field("value", pa.float64()),
        pa.field("unit", pa.string()),
        pa.field("quality", pa.string()),
        pa.field("source", pa.string()),
        pa.field("source_date", pa.string()),
        pa.field("ingested_at", pa.timestamp("us")),
    ]
)

COLUMNS = tuple(SCHEMA.names)
PART_FILE = "part-0.parquet"
DEFAULT_LAST_N_PERIODS = 3


# ------------------------------------------------------------------- chemins

def partition_dir(indicator_id: str) -> Path:
    """Répertoire de partition Hive d'un indicateur."""
    return config.indicators_dir() / f"indicator={indicator_id}"


def partition_path(indicator_id: str) -> Path:
    """Fichier Parquet d'un indicateur."""
    return partition_dir(indicator_id) / PART_FILE


def materialized_ids() -> list[str]:
    """Indicateurs effectivement présents sur disque."""
    root = config.indicators_dir()
    if not root.is_dir():
        return []
    return sorted(
        p.name.split("=", 1)[1]
        for p in root.iterdir()
        if p.is_dir() and p.name.startswith("indicator=") and (p / PART_FILE).exists()
    )


def materialized_info(indicator_id: str) -> dict | None:
    """Métadonnées de matérialisation d'un indicateur, ou ``None`` s'il est absent.

    Renvoie ``{"path", "rows", "source", "source_date", "ingested_at",
    "time_min", "time_max"}``.
    """
    path = partition_path(indicator_id)
    if not path.exists():
        return None
    row = duckdb.execute(
        """
        SELECT count(*), any_value(source), max(source_date), max(ingested_at),
               min(time), max(time)
        FROM read_parquet(?)
        """,
        [str(path)],
    ).fetchone()
    if row is None or not row[0]:
        return None
    return {
        "path": str(path),
        "rows": row[0],
        "source": row[1],
        "source_date": row[2],
        "ingested_at": row[3],
        "time_min": row[4],
        "time_max": row[5],
    }


# ------------------------------------------------------------------ écriture

def _to_table(rows: Any) -> pa.Table:
    """Normalise l'entrée d'un pipeline en ``pyarrow.Table``."""
    if isinstance(rows, pa.Table):
        return rows
    if isinstance(rows, pa.RecordBatchReader):  # DuckDB ≥ 1.5 : .arrow() streame
        return rows.read_all()
    if hasattr(rows, "fetch_arrow_table"):  # relation / résultat DuckDB
        return rows.fetch_arrow_table()
    if hasattr(rows, "arrow"):
        return _to_table(rows.arrow())
    if isinstance(rows, dict):
        return pa.table(rows)
    rows = list(rows)
    if not rows:
        return pa.table({name: pa.array([], type=SCHEMA.field(name).type)
                         for name in ("geo_code", "time", "value", "quality")})
    if isinstance(rows[0], dict):
        keys = list(rows[0])
        return pa.table({k: [r.get(k) for r in rows] for k in keys})
    raise TypeError(
        "write_partition attend une liste de dicts, un pyarrow.Table "
        "ou une relation DuckDB."
    )


def write_partition(
    spec: Any,
    rows: Any,
    source_date: str,
    ingested_at: datetime | None = None,
) -> int:
    """Écrit (ou remplace) la partition d'un indicateur, atomiquement.

    ``spec`` est un indicateur du registre (voir :mod:`nutshell_mcp.registry`).
    Les colonnes obligatoires côté pipeline sont ``geo_code``, ``time`` et
    ``value`` ; ``quality`` est optionnelle. Renvoie le nombre de lignes écrites.
    """
    table = _to_table(rows)
    missing = {"geo_code", "time", "value"} - set(table.column_names)
    if missing:
        raise ValueError(
            f"colonnes manquantes pour '{spec.id}' : {', '.join(sorted(missing))}"
        )
    n = table.num_rows
    # UTC naïf : évite la dépendance pytz de DuckDB sur les timestamptz.
    stamp = (ingested_at or datetime.now(UTC)).replace(tzinfo=None)

    def constant(value, kind):
        return pa.array([value] * n, type=kind)

    quality = (
        table.column("quality").cast(pa.string())
        if "quality" in table.column_names
        else constant("", pa.string())
    )
    quality = pc.fill_null(quality, "")
    out = pa.table(
        {
            "indicator": constant(spec.id, pa.string()),
            "geo_code": table.column("geo_code").cast(pa.string()),
            "time": table.column("time").cast(pa.string()),
            "value": table.column("value").cast(pa.float64()),
            "unit": constant(spec.unit, pa.string()),
            "quality": quality,
            "source": constant(spec.source, pa.string()),
            "source_date": constant(source_date, pa.string()),
            "ingested_at": constant(stamp, pa.timestamp("us")),
        },
        schema=SCHEMA,
    )

    target = partition_dir(spec.id)
    tmp = target.with_name(target.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    pq.write_table(out, tmp / PART_FILE, compression="zstd")
    if target.exists():
        shutil.rmtree(target)
    tmp.replace(target)
    return n


def drop_partition(indicator_id: str) -> bool:
    """Supprime la partition d'un indicateur. Renvoie vrai si elle existait."""
    target = partition_dir(indicator_id)
    if not target.exists():
        return False
    shutil.rmtree(target)
    return True


# ------------------------------------------------------------------- lecture

def _glob(indicator_ids: Sequence[str]) -> list[str]:
    """Chemins existants, en conservant le préfixe de partition pour le pruning."""
    return [str(partition_path(i)) for i in indicator_ids if partition_path(i).exists()]


def _time_clause(time_from: str, time_to: str) -> tuple[str, list[str]]:
    """Filtre temporel inclusif (§8.3).

    ``time_to = "2023"`` couvre ``2023``, ``2023-Q4`` et ``2023-12`` ;
    ``time_from = "2023"`` couvre les mêmes.
    """
    clauses, args = [], []
    if time_from:
        clauses.append("(time >= ? OR time LIKE ?)")
        args += [time_from, f"{time_from}-%"]
    if time_to:
        clauses.append("(time <= ? OR time LIKE ?)")
        args += [time_to, f"{time_to}-%"]
    return (" AND ".join(clauses), args)


def query(
    indicators: Sequence[str],
    zones: Sequence[str],
    time_from: str = "",
    time_to: str = "",
    last_n_periods: int = DEFAULT_LAST_N_PERIODS,
    snapshot_indicators: Sequence[str] = (),
) -> tuple[list[str], list[list[str]], dict[str, dict]]:
    """Interroge la table canonique et renvoie les lignes **pivotées**.

    Renvoie ``(colonnes, lignes, provenance)`` où :

    - ``colonnes`` = ``["geo_code", "time", indicateur_1, …]`` ;
    - ``lignes`` = valeurs formatées, triées par zone puis période décroissante ;
    - ``provenance`` = ``{indicateur: {"source", "source_date", "ingested_at"}}``,
      complété de ``"snapshot_time"`` et ``"snapshot_quality"`` pour les instantanés.

    Sans filtre temporel, seules les ``last_n_periods`` dernières périodes
    présentes (toutes zones et indicateurs périodiques confondus) sont renvoyées.

    Les ``snapshot_indicators`` (fréquence ``SNAPSHOT``, ex. comptages OSM datés
    du mois de l'extrait) décrivent l'état courant d'une zone, pas une période :
    ils ne sont pas filtrés par ``time_from``/``time_to``, ne comptent pas dans
    les dernières périodes, et leur valeur la plus récente est **répétée sur
    chaque ligne de période de la zone** avec le marqueur ``[snapshot AAAA-MM]``.
    Une zone qui n'a que des instantanés garde une ligne datée de l'instantané.
    """
    snapshots = [i for i in indicators if i in set(snapshot_indicators)]
    periodic = [i for i in indicators if i not in set(snapshots)]
    empty: tuple[list[str], list[list[str]], dict[str, dict]] = (
        ["geo_code", "time", *indicators], [], {},
    )

    con = duckdb.connect()
    select = (
        "SELECT indicator, geo_code, time, value, unit, quality, source, "
        "source_date, ingested_at "
        "FROM read_parquet(?, hive_partitioning=true, union_by_name=true) WHERE "
    )

    def _fetch(ids: list[str], with_time: bool) -> list[tuple]:
        paths = _glob(ids)
        if not paths:
            return []
        where = ["indicator IN (" + ",".join("?" * len(ids)) + ")"]
        args: list[Any] = list(ids)
        if zones:
            where.append("geo_code IN (" + ",".join("?" * len(zones)) + ")")
            args += list(zones)
        if with_time:
            clause, targs = _time_clause(time_from, time_to)
            if clause:
                where.append(clause)
                args += targs
        return con.execute(select + " AND ".join(where), [paths, *args]).fetchall()

    rows = _fetch(periodic, with_time=True) if periodic else []
    snap_rows = _fetch(snapshots, with_time=False) if snapshots else []
    if not rows and not snap_rows:
        return empty

    if rows and not time_from and not time_to and last_n_periods > 0:
        periods = sorted({r[2] for r in rows}, key=_period_key, reverse=True)[:last_n_periods]
        keep = set(periods)
        rows = [r for r in rows if r[2] in keep]

    provenance: dict[str, dict] = {}

    def _note_provenance(indicator, source, src_date, ing):
        prev = provenance.get(indicator)
        if prev is None or (src_date or "") > (prev["source_date"] or ""):
            provenance[indicator] = {
                "source": source, "source_date": src_date, "ingested_at": ing,
            }

    pivot: dict[tuple[str, str], dict[str, str]] = {}
    for indicator, geo_code, time, value, _unit, quality, source, src_date, ing in rows:
        cell = _format(value)
        if quality:
            cell += f" [{quality}]"
        pivot.setdefault((geo_code, time), {})[indicator] = cell
        _note_provenance(indicator, source, src_date, ing)

    # Instantanés : dernière valeur par (indicateur, zone), répétée sur les
    # lignes périodiques de la zone ; ligne propre si la zone n'en a aucune.
    latest: dict[tuple[str, str], tuple] = {}
    for r in snap_rows:
        key = (r[0], r[1])
        if key not in latest or _period_key(r[2]) > _period_key(latest[key][2]):
            latest[key] = r
    zones_with_periods = {k[0] for k in pivot}
    for (indicator, geo_code), r in latest.items():
        _, _, time, value, _unit, quality, source, src_date, ing = r
        _note_provenance(indicator, source, src_date, ing)
        meta = provenance[indicator]
        meta["snapshot_time"] = max(time, meta.get("snapshot_time") or "")
        if quality:
            meta.setdefault("snapshot_quality", set()).add(quality)
        if geo_code in zones_with_periods:
            meta["snapshot_repeated"] = True
            cell = f"{_format(value)} [snapshot {time}]"
            for key, cells in pivot.items():
                if key[0] == geo_code:
                    cells[indicator] = cell
        else:
            cell = _format(value)
            if quality:
                cell += f" [{quality}]"
            pivot.setdefault((geo_code, time), {})[indicator] = cell

    # Toutes les colonnes demandées sont conservées, même sans valeur sur la
    # fenêtre : une colonne vide est une information, une colonne disparue non.
    columns = ["geo_code", "time", *indicators]
    # Zone croissante, période décroissante : la valeur la plus récente d'abord.
    ordered = sorted(pivot, key=lambda k: (k[0], _period_desc(k[1])))
    out = []
    for key in ordered:
        cells = pivot[key]
        out.append([key[0], key[1]] + [cells.get(i, "") for i in columns[2:]])
    return columns, out, provenance


def _period_key(period: str) -> tuple[int, int, int]:
    """Tri chronologique naturel d'une période Eurostat.

    ``2023`` → (2023, 0, 0) ; ``2023-S2`` → (2023, 7, 1) ; ``2023-Q4`` → (2023, 10, 2) ;
    ``2023-10`` → (2023, 10, 3). Le troisième terme distingue la granularité, de
    sorte que ``2023-Q4`` et ``2023-10`` (octobre) ne partagent jamais la même clé.
    """
    year_s, _, sub = period.partition("-")
    try:
        year = int(year_s)
    except ValueError:
        return (0, 0, 0)
    if not sub:
        return (year, 0, 0)
    if sub[0] == "S" and sub[1:].isdigit():
        return (year, (int(sub[1:]) - 1) * 6 + 1, 1)
    if sub[0] == "Q" and sub[1:].isdigit():
        return (year, (int(sub[1:]) - 1) * 3 + 1, 2)
    if sub.isdigit():
        return (year, int(sub), 3)
    return (year, 0, 9)


def _period_desc(period: str) -> tuple[int, int, int]:
    """Clé de tri décroissant sur la période (le plus récent en premier)."""
    return tuple(-p for p in _period_key(period))  # type: ignore[return-value]


def _format(value: float | None) -> str:
    if value is None:
        return ""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.6g}"


def available_zone_levels(indicator_id: str) -> list[str]:
    """Niveaux de zones réellement présents dans la partition (diagnostic)."""
    info = materialized_info(indicator_id)
    if info is None:
        return []
    rows = duckdb.execute(
        "SELECT DISTINCT length(geo_code) FROM read_parquet(?)", [info["path"]]
    ).fetchall()
    mapping = {2: "NUTS0", 3: "NUTS1", 4: "NUTS2", 5: "NUTS3", 6: "CITY"}
    return sorted({mapping[r[0]] for r in rows if r[0] in mapping})


def iter_partitions() -> Iterable[tuple[str, Path]]:
    """(id, chemin) de chaque partition matérialisée."""
    for indicator_id in materialized_ids():
        yield indicator_id, partition_path(indicator_id)
