"""Projection Eurostat vers le grain canonique (§7.1).

Après matérialisation du Parquet natif d'un dataset, chaque indicateur du
registre pointant vers ce dataset est re-matérialisé :

1. DuckDB lit ``mirror/eurostat/{dataset}.parquet`` et applique les ``filters``
   du registre ;
2. la dimension ``value_dim`` (``geo`` par défaut) est renommée ``geo_code`` ;
3. jointure avec la table `geo` : seuls les codes du référentiel sont conservés,
   et seulement aux niveaux déclarés dans ``geo_levels`` — les agrégats Eurostat
   (``EU27_2020``, ``EA19``…) disparaissent donc naturellement ;
4. gestion du millésime : un indicateur déclaré en NUTS 2021 dont le code est
   recodé de façon bijective vers NUTS 2024 est converti et marqué
   ``quality = 'recoded'`` ; sinon la ligne est conservée telle quelle ;
5. ``quality`` reprend le flag Eurostat, ``unit`` vient du registre,
   ``source_date`` du « last update of data » du TOC.
"""

from __future__ import annotations

import sqlite3

import duckdb
import pyarrow as pa

from . import config, geo, indicators, registry, store


class ProjectionError(Exception):
    """Projection impossible : message destiné au rapport de synchronisation."""


def native_path(dataset: str):
    """Chemin du Parquet natif d'un dataset dans le miroir Eurostat."""
    return config.eurostat_mirror_dir() / f"{dataset}.parquet"


def indicators_for_dataset(dataset: str) -> list:
    """Indicateurs du registre qui projettent ``dataset``."""
    return [
        spec
        for spec in registry.load_all(source="eurostat")
        if spec.extraction.dataset == dataset
    ]


def _geo_table(levels: list[str]) -> pa.Table:
    with store.connect() as c:
        try:
            rows = c.execute(
                "SELECT geo_code FROM geo WHERE level IN ("
                + ",".join("?" * len(levels))
                + ")",
                levels,
            ).fetchall()
        except sqlite3.OperationalError as exc:  # table geo absente
            raise ProjectionError(
                "référentiel geo absent — lancer : "
                "python -m territorial_mcp.sync --source geo"
            ) from exc
    return pa.table({"geo_code": pa.array([r[0] for r in rows], type=pa.string())})


def project(spec, source_date: str | None = None) -> int:
    """Re-matérialise la partition canonique d'un indicateur Eurostat.

    Renvoie le nombre de lignes écrites. Lève :class:`ProjectionError` si le
    miroir natif ou le référentiel geo manquent, ou si les filtres ne
    correspondent à aucune dimension du dataset.
    """
    dataset = spec.extraction.dataset
    path = native_path(dataset)
    if not path.exists():
        raise ProjectionError(
            f"miroir natif absent pour '{dataset}' — lancer : "
            f"python -m territorial_mcp.mirror --datasets {dataset}"
        )

    allowed = _geo_table(list(spec.geo_levels))
    if allowed.num_rows == 0:
        raise ProjectionError(
            f"aucune zone du référentiel aux niveaux {', '.join(spec.geo_levels)}"
        )

    con = duckdb.connect()
    con.register("geo_ref", allowed)
    columns = [
        f[0]
        for f in con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]
        ).fetchall()
    ]
    value_dim = spec.extraction.value_dim
    time_dim = spec.extraction.time_dim
    if value_dim not in columns:
        raise ProjectionError(
            f"dimension '{value_dim}' absente de {dataset} "
            f"(colonnes : {', '.join(columns)})"
        )
    if time_dim not in columns:
        raise ProjectionError(f"dimension temporelle '{time_dim}' absente de {dataset}")

    where, args = [], [str(path)]
    for dim, value in spec.extraction.filters.items():
        if dim not in columns:
            raise ProjectionError(
                f"filtre '{dim}' absent de {dataset} (colonnes : {', '.join(columns)})"
            )
        where.append(f'"{dim}" = ?')
        args.append(value)
    # Conversion de millésime : uniquement les correspondances bijectives.
    mapping = (
        geo.recoding_map(spec.nuts_vintage)
        if spec.nuts_vintage != config.DEFAULT_NUTS_VINTAGE
        else {}
    )
    con.register(
        "recode_map",
        pa.table(
            {
                "old_code": pa.array(list(mapping), type=pa.string()),
                "new_code": pa.array(list(mapping.values()), type=pa.string()),
            }
        ),
    )

    flag_expr = 'nullif(trim("flag"), \'\')' if "flag" in columns else "NULL"
    sql = f"""
        WITH src AS (
            SELECT "{value_dim}" AS raw_code, "{time_dim}" AS time,
                   value, {flag_expr} AS flag
            FROM read_parquet(?)
            {"WHERE " + " AND ".join(where) if where else ""}
        ), recoded AS (
            SELECT coalesce(m.new_code, s.raw_code) AS geo_code, s.time, s.value,
                   concat_ws(',', CASE WHEN m.new_code IS NOT NULL THEN 'recoded' END,
                             s.flag) AS quality
            FROM src s LEFT JOIN recode_map m ON m.old_code = s.raw_code
        )
        SELECT r.geo_code, r.time, r.value, r.quality
        FROM recoded r JOIN geo_ref g ON g.geo_code = r.geo_code
        WHERE r.value IS NOT NULL
        ORDER BY r.geo_code, r.time
    """
    table = con.execute(sql, args).arrow()

    if source_date is None:
        source_date = _source_date(dataset)
    return indicators.write_partition(spec, table, source_date=source_date)


def _source_date(dataset: str) -> str:
    """Date des données à la source : « last update of data » du TOC."""
    from . import mirror

    info = mirror.mirror_info(dataset)
    if info and info.get("last_update"):
        return str(info["last_update"])
    return store.catalog_last_update(dataset) or ""


def project_dataset(dataset: str, source_date: str | None = None) -> list[tuple[str, int | str]]:
    """Projette tous les indicateurs d'un dataset.

    Renvoie une liste ``(id, lignes)`` ou ``(id, message d'erreur)`` — un échec
    d'indicateur n'interrompt jamais le lot (§7).
    """
    out: list[tuple[str, int | str]] = []
    for spec in indicators_for_dataset(dataset):
        try:
            out.append((spec.id, project(spec, source_date)))
        except Exception as exc:
            out.append((spec.id, str(exc)))
    return out
