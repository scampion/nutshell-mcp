"""Serveur MCP Eurostat — 4 tools pensés pour un modèle local (Qwen3.8-27B).

Principes :
- Le modèle ne construit jamais d'URL SDMX : query_data valide chaque
  dimension et chaque code contre le DSD avant d'appeler Eurostat.
- Erreurs actionnables avec suggestions (difflib) plutôt que 400 bruts.
- Sorties compactées : codelists tronquées, tableaux plafonnés à
  MAX_CELLS cellules.

Lancement :
    python -m territorial_mcp.server            # stdio (client local)
    MCP_TRANSPORT=http python -m territorial_mcp.server   # streamable HTTP
"""

from __future__ import annotations

import difflib
import os

try:  # SDK >= 2.0
    from mcp.server import MCPServer as FastMCP
except ImportError:  # SDK 1.x
    from mcp.server.fastmcp import FastMCP

import duckdb

from . import eurostat_client as api
from . import mirror
from . import store

mcp = FastMCP("eurostat")

MAX_CODES_SHOWN = 25   # codes affichés par dimension dans get_structure
MAX_CELLS = 400        # cellules max renvoyées par query_data
# EUROSTAT_OFFLINE=1 : ne jamais toucher au réseau (miroir + caches seulement)
OFFLINE_ONLY = os.environ.get("EUROSTAT_OFFLINE") == "1"


def _query_mirror(info: dict, params_filters: dict[str, list[str]],
                  time_from: str, time_to: str, last_update: str) -> str:
    """Interroge le Parquet local via DuckDB. Zéro réseau."""
    where, args = [], []
    for dim, codes in params_filters.items():
        where.append(f"{dim} IN ({','.join('?' * len(codes))})")
        args.extend(codes)
    if time_from:
        where.append("time >= ?")
        args.append(time_from)
    if time_to:
        # inclut les sous-périodes : time_to="2023" couvre "2023-Q4"
        where.append("(time <= ? OR time LIKE ?)")
        args.extend([time_to, f"{time_to}-%"])
    sql = (f"SELECT * FROM read_parquet(?) "
           f"{'WHERE ' + ' AND '.join(where) if where else ''} "
           f"ORDER BY time LIMIT {MAX_CELLS + 1}")
    rows = duckdb.execute(sql, [info["path"], *args]).fetchall()
    cols = [d[0] for d in duckdb.execute(
        "SELECT * FROM read_parquet(?) LIMIT 0", [info["path"]]).description]
    truncated = len(rows) > MAX_CELLS
    rows = rows[:MAX_CELLS]
    if not rows:
        return "Aucune valeur pour ces filtres (données locales)."
    out = [" | ".join(cols)]
    out += [" | ".join("" if v is None else str(v) for v in r) for r in rows]
    if truncated:
        out.append(f"[Tronqué à {MAX_CELLS} lignes — ajoutez des filtres.]")
    out.append(f"[Source : miroir local, données Eurostat du {last_update}]")
    return "\n".join(out)


# ----------------------------------------------------------------- helpers

async def _structure(dataset: str) -> dict:
    cached = store.get_structure(dataset, ignore_ttl=OFFLINE_ONLY)
    if cached is not None:
        return cached
    if OFFLINE_ONLY:
        raise api.EurostatError(
            f"Structure de '{dataset}' absente du cache et mode offline actif. "
            f"Lancer : python -m territorial_mcp.mirror --datasets {dataset}")
    try:
        structure = await api.fetch_structure(dataset)
    except api.EurostatError:
        raise
    except Exception:
        stale = store.get_structure(dataset, ignore_ttl=True)
        if stale is not None:
            return stale  # serve-stale-on-error
        raise api.EurostatError(
            f"Eurostat injoignable et '{dataset}' absent du cache local.")
    store.put_structure(dataset, structure)
    return structure


def _suggest(value: str, candidates: list[str]) -> str:
    close = difflib.get_close_matches(value.upper(), [c.upper() for c in candidates], n=3)
    return f" Vouliez-vous : {', '.join(close)} ?" if close else ""


def _rows_from_jsonstat(js: dict) -> tuple[list[str], list[list[str]]]:
    """Aplatis un JSON-stat 2.0 en (en-têtes, lignes)."""
    dim_ids: list[str] = js["id"]
    sizes: list[int] = js["size"]
    labels = {
        d: list(js["dimension"][d]["category"].get(
            "label", {c: c for c in js["dimension"][d]["category"]["index"]}
        ).keys())
        for d in dim_ids
    }
    # index -> code, trié par position
    order = {
        d: sorted(js["dimension"][d]["category"]["index"].items(), key=lambda kv: kv[1])
        for d in dim_ids
    }
    values = js["value"]  # dict {index_lineaire: valeur} ou liste
    if isinstance(values, list):
        values = {i: v for i, v in enumerate(values)}

    rows = []
    for flat_idx, val in values.items():
        flat_idx = int(flat_idx)
        coords, rem = [], flat_idx
        for size in reversed(sizes):
            coords.append(rem % size)
            rem //= size
        coords.reverse()
        row = [order[d][c][0] for d, c in zip(dim_ids, coords)]
        row.append(str(val))
        rows.append(row)
    return dim_ids + ["value"], rows


# ------------------------------------------------------------------- tools

@mcp.tool()
async def search_datasets(query: str, limit: int = 10) -> str:
    """Recherche full-text dans le catalogue Eurostat (~7000 datasets).

    Renvoie code, titre et période couverte. Utiliser ensuite
    get_structure(code) avant toute requête de données.
    """
    if store.catalog_is_stale() and not OFFLINE_ONLY:
        try:
            store.replace_catalog(await api.fetch_toc())
        except Exception:
            pass  # serve-stale : le catalogue local reste utilisable
    hits = store.search_catalog(query, min(limit, 25))
    if not hits:
        return "Aucun dataset trouvé. Essayez des termes plus généraux, en anglais."
    return "\n".join(f"{h['code']} | {h['title']} | {h['period']}" for h in hits)


@mcp.tool()
async def get_structure(dataset: str) -> str:
    """Dimensions et codes d'un dataset (codelists tronquées).

    À appeler avant query_data. Si une dimension affiche '… et N autres',
    utiliser list_codes pour la parcourir.
    """
    try:
        structure = await _structure(dataset)
    except api.EurostatError as e:
        return str(e)
    lines = [f"Dataset {dataset} — dimensions :"]
    for dim, info in structure.items():
        codes = info["codes"]
        shown = list(codes.items())[:MAX_CODES_SHOWN]
        extra = len(codes) - len(shown)
        body = ", ".join(f"{c} ({l})" for c, l in shown)
        if extra > 0:
            body += f" … et {extra} autres (voir list_codes)"
        lines.append(f"- {dim} [{info['label']}] : {body}")
    return "\n".join(lines)


@mcp.tool()
async def list_codes(dataset: str, dimension: str, contains: str = "") -> str:
    """Liste les codes d'une dimension, filtrable par sous-chaîne.

    Exemple : list_codes("nama_10_gdp", "geo", contains="fr").
    """
    try:
        structure = await _structure(dataset)
    except api.EurostatError as e:
        return str(e)
    if dimension not in structure:
        return (f"Dimension '{dimension}' inconnue."
                + _suggest(dimension, list(structure)))
    codes = structure[dimension]["codes"]
    needle = contains.lower()
    hits = [(c, l) for c, l in codes.items()
            if needle in c.lower() or needle in l.lower()]
    if not hits:
        return f"Aucun code ne contient '{contains}' dans {dimension}."
    shown = hits[:60]
    out = "\n".join(f"{c} : {l}" for c, l in shown)
    if len(hits) > 60:
        out += f"\n… et {len(hits) - 60} autres, affinez 'contains'."
    return out


@mcp.tool()
async def query_data(
    dataset: str,
    filters: dict[str, str] | None = None,
    time_from: str = "",
    time_to: str = "",
) -> str:
    """Interroge un dataset. filters = {dimension: "CODE1+CODE2"}.

    Les codes sont validés avant l'appel. Exemple :
    query_data("nama_10_gdp", {"geo": "FR+BE", "na_item": "B1GQ",
    "unit": "CP_MEUR"}, time_from="2020").
    Filtrer suffisamment : la réponse est plafonnée à 400 cellules.
    """
    filters = filters or {}
    try:
        structure = await _structure(dataset)
    except api.EurostatError as e:
        return str(e)

    # -- validation contre le DSD
    params: dict[str, str | list[str]] = {}
    for dim, raw in filters.items():
        if dim not in structure:
            return (f"Dimension '{dim}' inconnue pour {dataset}."
                    + _suggest(dim, list(structure)))
        valid = structure[dim]["codes"]
        codes = [c.strip() for c in raw.split("+") if c.strip()]
        for code in codes:
            if code not in valid:
                return (f"Code '{code}' inconnu pour la dimension '{dim}'."
                        + _suggest(code, list(valid))
                        + " Utilisez list_codes pour explorer.")
        params[dim] = codes
    # -- mode offline : miroir Parquet local en priorité
    info = mirror.mirror_info(dataset)
    if info is not None:
        return _query_mirror(info, params_filters=
                             {d: [c.strip() for c in v.split("+")] for d, v in filters.items()},
                             time_from=time_from, time_to=time_to,
                             last_update=info["last_update"])

    if OFFLINE_ONLY:
        return (f"Dataset '{dataset}' non mirroré et mode offline actif. "
                f"Lancer : python -m territorial_mcp.mirror --datasets {dataset}")

    if time_from:
        params["sinceTimePeriod"] = time_from
    if time_to:
        params["untilTimePeriod"] = time_to
    if not filters and not time_from:
        params["lastTimePeriod"] = "3"  # garde-fou anti-déluge

    try:
        js = await api.fetch_jsonstat(dataset, params)
    except api.EurostatError as e:
        return str(e)

    header, rows = _rows_from_jsonstat(js)
    truncated = len(rows) > MAX_CELLS
    rows = rows[:MAX_CELLS]
    out = [" | ".join(header)] + [" | ".join(r) for r in rows]
    if truncated:
        out.append(f"[Tronqué à {MAX_CELLS} lignes — ajoutez des filtres "
                   "ou réduisez la plage temporelle.]")
    return "\n".join(out)


def main() -> None:
    if os.environ.get("MCP_TRANSPORT") == "http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
