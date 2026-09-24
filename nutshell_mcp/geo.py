"""Référentiel géographique (§4) : table `geo`, correspondances de millésimes,
géométries GISCO.

Le code de zone est la clé de jointure de tout le système. Le référentiel est
construit depuis GISCO, ce qui garantit la cohérence avec les codes `geo` des
datasets Eurostat.

Sources retenues
----------------
- NUTS (niveaux 0 à 3), millésimes 2024 et 2021, GeoJSON EPSG:4326 :
  ``https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/
  NUTS_RG_{resolution}_{millesime}_4326_LEVL_{niveau}.geojson``
  Résolutions retenues : ``01M`` (statistiques zonales, jointures spatiales) et
  ``10M`` (affichage / attributs).
- Villes Urban Audit 2024 (niveau ``CITY``) :
  ``…/urau/geojson/URAU_RG_100K_2024_4326_CITIES.geojson``
- Correspondance NUTS 2021 → NUTS 2024 : classeur officiel Eurostat
  ``https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx``
  (feuille « NUTS2021- NUTS2024 »), lu avec la stdlib — pas de dépendance Excel.

Modèle de données
-----------------
``geo(geo_code PK, level, name, parent_code, valid_from, country)``
    Référentiel **courant** : NUTS 2024 niveaux 0-3 + villes Urban Audit 2024.
``nuts_changes(old_code, new_code, vintage_from, vintage_to, bijective, change)``
    Historique 2021 → 2024. ``bijective = 1`` quand la valeur d'une zone 2021
    peut être reportée telle quelle sur une zone 2024 (code inchangé, changement
    de code ou de nom) ; ``0`` sinon (fusion, scission, transfert de limites,
    région créée ou supprimée).

Interface pour les pipelines d'ingestion (lots 2 et 3)
------------------------------------------------------
.. code-block:: python

    from nutshell_mcp import geo

    # Fichier de géométries à passer à exactextract / DuckDB spatial
    path = geo.geometry_path("NUTS3")          # 01M, millésime 2024
    prop = geo.geometry_code_property("NUTS3")  # "NUTS_ID" (ou "URAU_CODE")

    # Liste des zones d'un niveau (codes attendus en sortie de pipeline)
    codes = [z["geo_code"] for z in geo.zones("NUTS3")]

Les GeoJSON sont conservés bruts (EPSG:4326, une FeatureCollection par niveau) :
GDAL/OGR, `exactextract` et l'extension spatiale de DuckDB les lisent tous
directement, sans conversion préalable.
"""

from __future__ import annotations

import json
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable
from pathlib import Path

import httpx

from . import config, store

GISCO_BASE = "https://gisco-services.ec.europa.eu/distribution/v2"
NUTS_URL = GISCO_BASE + "/nuts/geojson/NUTS_RG_{resolution}_{vintage}_4326_LEVL_{level}.geojson"
URAU_URL = GISCO_BASE + "/urau/geojson/URAU_RG_100K_{vintage}_4326_CITIES.geojson"
CORRESPONDENCE_URL = (
    "https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx"
)

NUTS_LEVELS = ("NUTS0", "NUTS1", "NUTS2", "NUTS3")
ALL_LEVELS = (*NUTS_LEVELS, "CITY")
RESOLUTIONS = (config.INGEST_RESOLUTION, config.DISPLAY_RESOLUTION)

#: Propriété portant le code de zone dans les GeoJSON GISCO, par famille.
NUTS_CODE_PROPERTY = "NUTS_ID"
URAU_CODE_PROPERTY = "URAU_CODE"

#: Types de changement 2021 → 2024 qui préservent l'identité de la zone.
_BIJECTIVE_CHANGES = {"", "Code change", "Name change"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS geo (
    geo_code TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    name TEXT,
    parent_code TEXT,
    valid_from INTEGER NOT NULL,
    country TEXT
);
CREATE INDEX IF NOT EXISTS geo_level_idx ON geo(level);
CREATE INDEX IF NOT EXISTS geo_parent_idx ON geo(parent_code);
CREATE TABLE IF NOT EXISTS nuts_changes (
    old_code TEXT,
    new_code TEXT,
    vintage_from INTEGER NOT NULL,
    vintage_to INTEGER NOT NULL,
    bijective INTEGER NOT NULL,
    change TEXT
);
CREATE INDEX IF NOT EXISTS nuts_changes_old_idx ON nuts_changes(old_code);
"""


def _conn() -> sqlite3.Connection:
    conn = store.connect()
    conn.executescript(_SCHEMA)
    return conn


# ------------------------------------------------------------------- chemins

def geometry_path(
    level: str,
    vintage: int = config.DEFAULT_NUTS_VINTAGE,
    resolution: str = config.INGEST_RESOLUTION,
) -> Path:
    """Chemin local du GeoJSON d'un niveau (existant ou non).

    ``level`` ∈ ``NUTS0…NUTS3``, ``CITY``. ``resolution`` ∈ ``01M`` (ingestion),
    ``10M`` (affichage) ; ignorée pour ``CITY``, publié en 100K uniquement.
    """
    level = level.upper()
    if level == "CITY":
        return config.geo_dir() / f"URAU_RG_100K_{vintage}_4326_CITIES.geojson"
    if level not in NUTS_LEVELS:
        raise ValueError(f"Niveau '{level}' inconnu (attendu : {', '.join(ALL_LEVELS)}).")
    return (
        config.geo_dir()
        / f"NUTS_RG_{resolution}_{vintage}_4326_LEVL_{level[-1]}.geojson"
    )


def geometry_code_property(level: str) -> str:
    """Nom de la propriété GeoJSON portant le code de zone, pour un niveau."""
    return URAU_CODE_PROPERTY if level.upper() == "CITY" else NUTS_CODE_PROPERTY


def _remote_url(level: str, vintage: int, resolution: str) -> str:
    if level.upper() == "CITY":
        return URAU_URL.format(vintage=vintage)
    return NUTS_URL.format(resolution=resolution, vintage=vintage, level=level[-1])


# ------------------------------------------------------------- téléchargement

def _download(url: str, dest: Path, client: httpx.Client) -> tuple[bool, str | None]:
    """Télécharge ``url`` vers ``dest`` si le signal de fraîcheur a changé.

    Renvoie ``(mis_a_jour, signal)``. Le signal est l'ETag GISCO à défaut le
    ``Last-Modified`` (P3 : invalidation événementielle, pas de TTL).
    """
    known = store.get_sync_state("geo", dest.name)
    headers = {}
    if known and dest.exists():
        headers["If-None-Match"] = known
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with client.stream("GET", url, headers=headers) as r:
        if r.status_code == 304:
            return False, known
        r.raise_for_status()
        signal = r.headers.get("etag") or r.headers.get("last-modified")
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    tmp.replace(dest)  # écriture atomique
    store.set_sync_state("geo", dest.name, signal)
    return True, signal


# ------------------------------------------------------------- table `geo`

def _properties(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    for feature in payload.get("features", []):
        yield feature.get("properties") or {}


def _nuts_rows(path: Path, level: str, vintage: int) -> list[tuple]:
    rows = []
    for props in _properties(path):
        code = props.get(NUTS_CODE_PROPERTY)
        if not code:
            continue
        name = props.get("NAME_LATN") or props.get("NUTS_NAME") or code
        parent = code[:-1] if len(code) > 2 else None
        rows.append((code, level, name, parent, vintage, props.get("CNTR_CODE")))
    return rows


def _city_rows(path: Path, vintage: int) -> list[tuple]:
    rows = []
    key = f"NUTS3_{vintage}"
    for props in _properties(path):
        code = props.get(URAU_CODE_PROPERTY)
        if not code:
            continue
        parent = props.get(key) or props.get("NUTS3_2024") or props.get("NUTS3_2021")
        rows.append(
            (code, "CITY", props.get("URAU_NAME") or code, parent, vintage,
             props.get("CNTR_CODE"))
        )
    return rows


def rebuild_table(vintage: int = config.DEFAULT_NUTS_VINTAGE) -> int:
    """Reconstruit la table `geo` depuis les GeoJSON présents sur disque.

    Les attributs sont lus dans la résolution d'affichage (10M, légère) ; les
    codes y sont identiques à ceux de la résolution 01M.
    """
    rows: list[tuple] = []
    for level in NUTS_LEVELS:
        path = geometry_path(level, vintage, config.DISPLAY_RESOLUTION)
        if not path.exists():
            path = geometry_path(level, vintage, config.INGEST_RESOLUTION)
        if path.exists():
            rows += _nuts_rows(path, level, vintage)
    city = geometry_path("CITY", vintage)
    if city.exists():
        rows += _city_rows(city, vintage)
    if not rows:
        return 0
    with _conn() as c:
        c.execute("DELETE FROM geo")
        c.executemany("INSERT OR REPLACE INTO geo VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


# ------------------------------------------------- correspondance de millésimes

def _xlsx_sheet_rows(path: Path, sheet_name: str) -> list[dict[str, str]]:
    """Lit une feuille XLSX avec la stdlib (zipfile + ElementTree)."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rels_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(path) as z:
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheet_target = None
        for sheet in workbook.iter(ns + "sheet"):
            if sheet.attrib.get("name") == sheet_name:
                sheet_target = target[sheet.attrib[rels_ns + "id"]]
                break
        if sheet_target is None:
            raise ValueError(f"Feuille '{sheet_name}' absente de {path.name}.")
        shared = [
            "".join(t.text or "" for t in si.iter(ns + "t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml"))
        ]
        name = sheet_target if sheet_target.startswith("xl/") else "xl/" + sheet_target
        sheet = ET.fromstring(z.read(name))

    out = []
    for row in sheet.iter(ns + "row"):
        cells: dict[str, str] = {}
        for cell in row.iter(ns + "c"):
            column = "".join(ch for ch in cell.get("r", "") if ch.isalpha())
            value_node = cell.find(ns + "v")
            value = "" if value_node is None else (value_node.text or "")
            if cell.get("t") == "s" and value:
                value = shared[int(value)]
            cells[column] = value.strip()
        out.append(cells)
    return out


def rebuild_changes(path: Path) -> int:
    """Charge la correspondance NUTS 2021 → 2024 depuis le classeur Eurostat.

    Colonnes utilisées : C (code 2021), D (code 2024), H (nature du changement).
    Une ligne dont une des deux colonnes de code est vide décrit une région
    créée ou supprimée : elle est conservée, avec ``bijective = 0``.
    """
    rows = _xlsx_sheet_rows(path, "NUTS2021- NUTS2024")
    out = []
    for cells in rows[1:]:
        old = cells.get("C", "")
        new = cells.get("D", "")
        change = cells.get("H", "")
        if not old and not new:
            continue
        bijective = int(bool(old) and bool(new) and change in _BIJECTIVE_CHANGES)
        out.append((old or None, new or None, 2021, 2024, bijective, change or None))
    with _conn() as c:
        c.execute("DELETE FROM nuts_changes WHERE vintage_from=2021 AND vintage_to=2024")
        c.executemany("INSERT INTO nuts_changes VALUES (?,?,?,?,?,?)", out)
    return len(out)


def recode(code: str, vintage_from: int, vintage_to: int = config.DEFAULT_NUTS_VINTAGE
           ) -> tuple[str | None, bool]:
    """Convertit un code d'un millésime vers un autre.

    Renvoie ``(code_cible, bijectif)``. ``(None, False)`` si la zone a disparu.
    Un code absent de la table de correspondance est renvoyé inchangé et
    considéré comme bijectif (cas des pays et des zones jamais modifiées).
    """
    if vintage_from == vintage_to:
        return code, True
    with _conn() as c:
        row = c.execute(
            """SELECT new_code, bijective FROM nuts_changes
               WHERE old_code = ? AND vintage_from = ? AND vintage_to = ?""",
            (code, vintage_from, vintage_to),
        ).fetchone()
    if row is None:
        return code, True
    return row[0], bool(row[1])


def recoding_map(vintage_from: int, vintage_to: int = config.DEFAULT_NUTS_VINTAGE
                 ) -> dict[str, str]:
    """Table {code source → code cible} restreinte aux correspondances bijectives."""
    if vintage_from == vintage_to:
        return {}
    with _conn() as c:
        rows = c.execute(
            """SELECT old_code, new_code FROM nuts_changes
               WHERE vintage_from = ? AND vintage_to = ? AND bijective = 1
                 AND old_code IS NOT NULL AND new_code IS NOT NULL AND old_code <> new_code""",
            (vintage_from, vintage_to),
        ).fetchall()
    return dict(rows)


# ------------------------------------------------------------------- lecture

def is_available() -> bool:
    """Vrai si le référentiel a été construit au moins une fois."""
    with _conn() as c:
        return c.execute("SELECT 1 FROM geo LIMIT 1").fetchone() is not None


def zones(level: str, parent: str | None = None, contains: str | None = None) -> list[dict]:
    """Zones d'un niveau, optionnellement sous un parent ou filtrées par nom.

    ``parent`` accepte un code d'un niveau quelconque au-dessus (``FR`` pour des
    NUTS2 comme ``FRK``) : le filtre est un préfixe pour les codes NUTS, une
    égalité sur ``parent_code`` pour les villes.
    """
    sql = "SELECT geo_code, name, level, parent_code FROM geo WHERE level = ?"
    args: list[str] = [level.upper()]
    if parent:
        parent = parent.upper()
        if level.upper() == "CITY":
            sql += " AND (parent_code = ? OR parent_code LIKE ?)"
            args += [parent, f"{parent}%"]
        else:
            sql += " AND geo_code LIKE ? AND geo_code <> ?"
            args += [f"{parent}%", parent]
    sql += " ORDER BY geo_code"
    with _conn() as c:
        rows = c.execute(sql, args).fetchall()
    if contains:
        # Filtre en Python : lower() SQLite ne replie pas les accents.
        needle = store.fold(contains)
        rows = [r for r in rows if needle in store.fold(r[1] or "") or needle in store.fold(r[0])]
    return [
        {"geo_code": r[0], "name": r[1], "level": r[2], "parent": r[3]} for r in rows
    ]


def zone(code: str) -> dict | None:
    """Une zone du référentiel, ou ``None``."""
    with _conn() as c:
        row = c.execute(
            "SELECT geo_code, name, level, parent_code, valid_from, country "
            "FROM geo WHERE geo_code = ?",
            (code.upper(),),
        ).fetchone()
    if row is None:
        return None
    return {
        "geo_code": row[0], "name": row[1], "level": row[2],
        "parent": row[3], "valid_from": row[4], "country": row[5],
    }


def suggest(code: str, n: int = 3) -> list[str]:
    """Les ``n`` codes du référentiel les plus proches (difflib)."""
    import difflib

    with _conn() as c:
        codes = [r[0] for r in c.execute("SELECT geo_code FROM geo")]
    return difflib.get_close_matches(code.upper(), codes, n=n, cutoff=0.5)


def levels_available() -> list[str]:
    """Niveaux effectivement présents dans le référentiel."""
    with _conn() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT level FROM geo ORDER BY level")]


# ------------------------------------------------------------------ ingestion

def ingest(
    vintages: tuple[int, ...] = (config.DEFAULT_NUTS_VINTAGE, config.PREVIOUS_NUTS_VINTAGE),
    resolutions: tuple[str, ...] = RESOLUTIONS,
    include_cities: bool = True,
    force: bool = False,
) -> dict:
    """Télécharge les géométries GISCO puis reconstruit `geo` et `nuts_changes`.

    Idempotent : un fichier dont l'ETag GISCO n'a pas bougé n'est pas
    retéléchargé (sauf ``force``). Renvoie un compte-rendu.
    """
    config.ensure_dirs()
    updated: list[str] = []
    unchanged: list[str] = []
    failed: list[tuple[str, str]] = []

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        for vintage in vintages:
            for resolution in resolutions:
                for level in NUTS_LEVELS:
                    dest = geometry_path(level, vintage, resolution)
                    if force and dest.exists():
                        store.set_sync_state("geo", dest.name, None)
                    try:
                        changed, _ = _download(
                            _remote_url(level, vintage, resolution), dest, client
                        )
                    except Exception as exc:  # un fichier manquant n'arrête pas le lot
                        failed.append((dest.name, str(exc)))
                        continue
                    (updated if changed else unchanged).append(dest.name)
        if include_cities:
            for vintage in vintages:
                dest = geometry_path("CITY", vintage)
                if force and dest.exists():
                    store.set_sync_state("geo", dest.name, None)
                try:
                    changed, _ = _download(_remote_url("CITY", vintage, ""), dest, client)
                except Exception as exc:
                    failed.append((dest.name, str(exc)))
                    continue
                (updated if changed else unchanged).append(dest.name)

        # Correspondance de millésimes (classeur Eurostat, hors service GISCO).
        corr = config.work_dir() / "NUTS2021-NUTS2024.xlsx"
        corr.parent.mkdir(parents=True, exist_ok=True)
        changes = 0
        try:
            _download(CORRESPONDENCE_URL, corr, client)
            changes = rebuild_changes(corr)
        except Exception as exc:
            failed.append(("NUTS2021-NUTS2024.xlsx", str(exc)))

    count = rebuild_table(config.DEFAULT_NUTS_VINTAGE)
    return {
        "zones": count,
        "changes": changes,
        "updated": updated,
        "unchanged": unchanged,
        "failed": failed,
    }
