"""Serveur MCP territorial — 7 tools pensés pour un modèle local (Qwen3.8-27B).

Deux familles de tools :

- **couche unifiée** (§8.1-8.3) : ``search_indicators`` → ``list_zones`` →
  ``get_indicators``. Grain zone × indicateur × période, toutes sources
  confondues, servi exclusivement depuis le disque ;
- **grain natif Eurostat** (§8.4) : ``search_datasets`` → ``get_structure`` →
  ``list_codes`` → ``query_data``, pour les 10 301 datasets dans leur
  intégralité.

Principes : le modèle ne construit jamais de requête source (P1) ; toute erreur
est actionnable, avec les 3 candidats les plus proches (difflib) ; toute sortie
est plafonnée et se termine par sa ligne de provenance (P5).

Lancement :
    python -m nutshell_mcp.server            # stdio (client local)
    MCP_TRANSPORT=http python -m nutshell_mcp.server   # streamable HTTP
"""

from __future__ import annotations

import contextlib
import difflib
import os

try:  # SDK >= 2.0
    from mcp.server import MCPServer as FastMCP
except ImportError:  # SDK 1.x
    from mcp.server.fastmcp import FastMCP

import duckdb

from . import config, geo, mirror, registry, store
from . import eurostat_client as api
from . import indicators as canonical

mcp = FastMCP("territorial")

MAX_CODES_SHOWN = 25   # codes affichés par dimension dans get_structure
MAX_CELLS = 400        # cellules max renvoyées par query_data
MAX_ROWS = 400         # lignes max renvoyées par get_indicators / list_zones
MAX_INDICATORS = 5     # garde-fou §8.3
MAX_ZONES = 100        # garde-fou §8.3
LAST_N_PERIODS = 3     # sans filtre temporel


def _offline() -> bool:
    """Mode offline total : aucun appel réseau (NUTSHELL_OFFLINE / EUROSTAT_OFFLINE)."""
    return config.offline()




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
    cached = store.get_structure(dataset, ignore_ttl=_offline())
    if cached is not None:
        return cached
    if _offline():
        raise api.EurostatError(
            f"Structure de '{dataset}' absente du cache et mode offline actif. "
            f"Lancer : python -m nutshell_mcp.mirror --datasets {dataset}")
    try:
        structure = await api.fetch_structure(dataset)
    except api.EurostatError:
        raise
    except Exception:
        stale = store.get_structure(dataset, ignore_ttl=True)
        if stale is not None:
            return stale  # serve-stale-on-error
        raise api.EurostatError(
            f"Eurostat injoignable et '{dataset}' absent du cache local.") from None
    store.put_structure(dataset, structure)
    return structure


def _suggest(value: str, candidates: list[str]) -> str:
    close = difflib.get_close_matches(value.upper(), [c.upper() for c in candidates], n=3)
    return f" Vouliez-vous : {', '.join(close)} ?" if close else ""


def _rows_from_jsonstat(js: dict) -> tuple[list[str], list[list[str]]]:
    """Aplatis un JSON-stat 2.0 en (en-têtes, lignes)."""
    dim_ids: list[str] = js["id"]
    sizes: list[int] = js["size"]
    # index -> code, trié par position
    order = {
        d: sorted(js["dimension"][d]["category"]["index"].items(), key=lambda kv: kv[1])
        for d in dim_ids
    }
    values = js["value"]  # dict {index_lineaire: valeur} ou liste
    if isinstance(values, list):
        values = dict(enumerate(values))

    rows = []
    for flat_idx, val in values.items():
        flat_idx = int(flat_idx)
        coords, rem = [], flat_idx
        for size in reversed(sizes):
            coords.append(rem % size)
            rem //= size
        coords.reverse()
        row = [order[d][c][0] for d, c in zip(dim_ids, coords, strict=False)]
        row.append(str(val))
        rows.append(row)
    return [*dim_ids, "value"], rows


# -------------------------------------------------- helpers couche unifiée

def _suggest_list(value: str, candidates: list[str], n: int = 3) -> list[str]:
    """Les n candidats les plus proches, insensible à la casse."""
    upper = {c.upper(): c for c in candidates}
    return [upper[m] for m in difflib.get_close_matches(value.upper(), list(upper), n=n)]


def _sync_command(source: str, indicator_id: str) -> str:
    return (
        f"python -m nutshell_mcp.sync --source {source} "
        f"--indicators {indicator_id}"
    )


def _provenance(provenance: dict[str, dict]) -> str:
    """Ligne de provenance multi-source : ``[Source : eurostat (21.08.2026), …]``."""
    seen: dict[str, str] = {}
    for meta in provenance.values():
        source = meta.get("source") or "?"
        date = meta.get("source_date") or "date inconnue"
        if source not in seen or date > seen[source]:
            seen[source] = date
    if not seen:
        return "[Source : aucune donnée locale]"
    parts = [f"{source} ({date})" for source, date in sorted(seen.items())]
    return "[Source : " + ", ".join(parts) + "]"


def _table(columns: list[str], rows: list[list[str]]) -> list[str]:
    return [" | ".join(columns)] + [" | ".join(r) for r in rows]


#: Profondeur de chaque niveau, et longueur du code NUTS correspondant.
_LEVEL_DEPTH = {"NUTS0": 0, "NUTS1": 1, "NUTS2": 2, "NUTS3": 3, "CITY": 4}
_CODE_LENGTH = {"NUTS0": 2, "NUTS1": 3, "NUTS2": 4, "NUTS3": 5}


def _level_hint(zone: dict, levels: list[str]) -> str:
    """Action corrective quand une zone n'est pas au bon niveau pour un indicateur.

    Si l'indicateur existe à un niveau plus fin, on propose de descendre sous la
    zone ; sinon on propose le code ancêtre au niveau le plus fin disponible.
    """
    depth = _LEVEL_DEPTH.get(zone["level"], 0)
    finer = [lvl for lvl in levels if _LEVEL_DEPTH.get(lvl, 0) > depth]
    if finer:
        target = min(finer, key=lambda lvl: _LEVEL_DEPTH[lvl])
        return f'utilisez list_zones("{target}", parent="{zone["geo_code"]}")'
    coarser = max(levels, key=lambda lvl: _LEVEL_DEPTH.get(lvl, 0))
    length = _CODE_LENGTH.get(coarser)
    code = zone["geo_code"]
    if length and len(code) > length and zone["level"] != "CITY":
        return f"demandez la zone englobante '{code[:length]}' (niveau {coarser})"
    return f'utilisez list_zones("{coarser}")'


# ------------------------------------------------------------------- tools

@mcp.tool()
async def search_indicators(query: str, source: str = "", limit: int = 10) -> str:
    """Cherche un indicateur (socio-économique, environnemental, infrastructure).

    Point d'entrée de toute analyse territoriale croisée. source filtre sur
    eurostat, copernicus ou osm. Utiliser ensuite list_zones puis get_indicators.
    """
    registry.ensure_materialized()
    if source and source not in registry.SOURCES:
        return (
            f"Source '{source}' inconnue. Sources : {', '.join(registry.SOURCES)}."
        )
    hits = registry.search(query, source, limit)
    if not hits:
        known = registry.all_ids()
        close = _suggest_list(query, known)
        extra = f" Proches : {', '.join(close)}." if close else ""
        return (
            f"Aucun indicateur ne correspond à '{query}'.{extra} "
            f"Registre complet ({len(known)}) : {', '.join(known)}."
        )
    lines = ["id | label | unité | freq | niveaux geo | source"]
    for hit in hits:
        materialized = canonical.materialized_info(hit["id"]) is not None
        flag = "" if materialized else " (non matérialisé)"
        lines.append(
            f"{hit['id']} | {hit['label']} | {hit['unit']} | {hit['frequency']} | "
            f"{','.join(hit['geo_levels'])} | {hit['source']}{flag}"
        )
    return "\n".join(lines)


@mcp.tool()
async def list_zones(level: str, parent: str = "", contains: str = "") -> str:
    """Liste les zones d'un niveau NUTS0-3 ou CITY, sous un parent ou par nom.

    Exemple : list_zones("NUTS2", parent="FR"). Les codes obtenus alimentent
    get_indicators.
    """
    level = level.upper().strip()
    available = geo.levels_available()
    if not available:
        return (
            "Référentiel géographique absent. "
            "Lancer : python -m nutshell_mcp.sync --source geo"
        )
    if level not in available:
        return (
            f"Niveau '{level}' inconnu. Niveaux disponibles : {', '.join(available)}."
        )
    if parent and geo.zone(parent) is None:
        close = geo.suggest(parent)
        extra = f" Vouliez-vous : {', '.join(close)} ?" if close else ""
        return f"Zone parente '{parent}' inconnue.{extra}"
    rows = geo.zones(level, parent or None, contains or None)
    if not rows:
        target = f" sous '{parent}'" if parent else ""
        needle = f" contenant '{contains}'" if contains else ""
        return f"Aucune zone de niveau {level}{target}{needle}."
    truncated = len(rows) > MAX_ROWS
    shown = rows[:MAX_ROWS]
    out = _table(
        ["geo_code", "name", "level", "parent"],
        [[r["geo_code"], r["name"] or "", r["level"], r["parent"] or ""] for r in shown],
    )
    if truncated:
        out.append(
            f"[Tronqué à {MAX_ROWS} lignes sur {len(rows)} — préciser 'parent' "
            f"(ex. parent=\"{shown[0]['geo_code'][:2]}\") ou 'contains'.]"
        )
    return "\n".join(out)


@mcp.tool()
async def get_indicators(
    indicators: list[str],
    zones: list[str],
    time_from: str = "",
    time_to: str = "",
) -> str:
    """Valeurs d'indicateurs pour des zones, une colonne par indicateur.

    Croise plusieurs sources en un seul tableau. Maximum 5 indicateurs et
    100 zones ; sans time_from/time_to, les 3 dernières périodes. Les ids
    viennent de search_indicators, les codes de zone de list_zones.
    """
    registry.ensure_materialized()
    requested = [i.strip() for i in indicators if i.strip()]
    zone_codes = [z.strip().upper() for z in zones if z.strip()]
    if not requested:
        return "Aucun indicateur demandé. Utilisez search_indicators pour en choisir."
    if not zone_codes:
        return "Aucune zone demandée. Utilisez list_zones pour en choisir."
    if len(requested) > MAX_INDICATORS:
        return (
            f"{len(requested)} indicateurs demandés, maximum {MAX_INDICATORS}. "
            f"Séparez la requête en plusieurs appels."
        )
    if len(zone_codes) > MAX_ZONES:
        return (
            f"{len(zone_codes)} zones demandées, maximum {MAX_ZONES}. "
            f"Restreignez avec list_zones(parent=…)."
        )

    # -- validation des indicateurs
    known_ids = registry.all_ids()
    specs = []
    for indicator_id in requested:
        spec = registry.get(indicator_id)
        if spec is None:
            close = _suggest_list(indicator_id, known_ids)
            extra = f" Vouliez-vous : {', '.join(close)} ?" if close else ""
            return (
                f"Indicateur '{indicator_id}' inconnu.{extra}\n"
                f"Utilisez search_indicators pour explorer."
            )
        specs.append(spec)

    # -- validation des zones
    resolved = []
    for code in zone_codes:
        zone_info = geo.zone(code)
        if zone_info is None:
            if not geo.levels_available():
                return (
                    "Référentiel géographique absent. "
                    "Lancer : python -m nutshell_mcp.sync --source geo"
                )
            close = geo.suggest(code)
            extra = f" Vouliez-vous : {', '.join(close)} ?" if close else ""
            return (
                f"Zone '{code}' inconnue.{extra}\n"
                f"Utilisez list_zones pour explorer le référentiel."
            )
        resolved.append(zone_info)

    # -- compatibilité niveau × geo_levels (§8.3)
    for spec in specs:
        levels = set(spec.geo_levels)
        incompatible = [z for z in resolved if z["level"] not in levels]
        if incompatible:
            bad = incompatible[0]
            return (
                f"'{spec.id}' n'existe pas au niveau {bad['level']} "
                f"(zone '{bad['geo_code']}') ; niveaux disponibles : "
                f"{', '.join(spec.geo_levels)}.\n"
                f"Séparez la requête ou {_level_hint(bad, spec.geo_levels)}."
            )

    # -- matérialisation
    for spec in specs:
        if canonical.materialized_info(spec.id) is None:
            offline_note = " et mode offline actif" if _offline() else ""
            return (
                f"Indicateur '{spec.id}' non matérialisé{offline_note}.\n"
                f"Lancer : {_sync_command(spec.source, spec.id)}"
            )

    columns, rows, provenance = canonical.query(
        [s.id for s in specs], [z["geo_code"] for z in resolved],
        time_from, time_to, LAST_N_PERIODS,
    )
    if not rows:
        window = (
            f" entre {time_from or '…'} et {time_to or '…'}"
            if (time_from or time_to) else ""
        )
        return (
            f"Aucune valeur pour ces zones{window}. "
            f"Élargissez la plage temporelle ou vérifiez les codes avec list_zones."
        )
    truncated = len(rows) > MAX_ROWS
    shown = rows[:MAX_ROWS]
    out = _table(columns, shown)
    if truncated:
        out.append(
            f"[Tronqué à {MAX_ROWS} lignes sur {len(rows)} — réduisez le nombre "
            f"de zones ou resserrez time_from/time_to.]"
        )
    out.append(_provenance(provenance))
    return "\n".join(out)


@mcp.tool()
async def search_datasets(query: str, limit: int = 10) -> str:
    """Recherche full-text dans le catalogue Eurostat (~7000 datasets).

    Renvoie code, titre et période couverte. Utiliser ensuite
    get_structure(code) avant toute requête de données.
    """
    if store.catalog_is_stale() and not _offline():
        # serve-stale : le catalogue local reste utilisable si Eurostat est muet
        with contextlib.suppress(Exception):
            store.replace_catalog(await api.fetch_toc())
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
        body = ", ".join(f"{code} ({label})" for code, label in shown)
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
    hits = [(code, label) for code, label in codes.items()
            if needle in code.lower() or needle in label.lower()]
    if not hits:
        return f"Aucun code ne contient '{contains}' dans {dimension}."
    shown = hits[:60]
    out = "\n".join(f"{code} : {label}" for code, label in shown)
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
    """Interroge un dataset Eurostat au grain complet. filters = {dim: "A+B"}.

    Exemple : query_data("nama_10_gdp", {"geo": "FR+BE", "na_item": "B1GQ",
    "unit": "CP_MEUR"}, time_from="2020"). Réponse plafonnée à 400 cellules.
    Pour croiser avec des indicateurs environnementaux ou d'infrastructure,
    préférer get_indicators.
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

    if _offline():
        return (f"Dataset '{dataset}' non mirroré et mode offline actif. "
                f"Lancer : python -m nutshell_mcp.mirror --datasets {dataset}")

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
