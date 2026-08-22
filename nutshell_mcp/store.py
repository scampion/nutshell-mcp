"""Métadonnées SQLite (§6.3) : catalogue FTS5, structures DSD, états de sync.

Un seul fichier, ``eurostat.db`` (chemin résolu par :mod:`nutshell_mcp.config`).
Quatre familles de tables y cohabitent :

- ``catalog`` (FTS5) : le TOC Eurostat, pour ``search_datasets`` hors ligne ;
- ``structures`` : les DSD sérialisées, pour la validation et ``list_codes`` ;
- ``registry`` / ``registry_fts`` : le registre matérialisé (voir
  :mod:`nutshell_mcp.registry`) ;
- ``sync_state`` : l'état de synchronisation générique par source.

Interface pour les pipelines d'ingestion (lots 2 et 3)
------------------------------------------------------
Chaque pipeline enregistre son signal de fraîcheur avec deux helpers génériques,
sans créer de table dédiée :

.. code-block:: python

    from nutshell_mcp import store

    previous = store.get_sync_state("osm", "europe-latest.osm.pbf")
    if previous != remote_timestamp:
        ...  # ingestion
        store.set_sync_state("osm", "europe-latest.osm.pbf", remote_timestamp)

La clé est libre (nom de fichier distant, id d'indicateur, produit CDS…), la
valeur est une chaîne (ETag, timestamp, version, dernière période matérialisée).
"""

from __future__ import annotations

import json
import sqlite3
import time

from . import config

CATALOG_TTL = 24 * 3600
STRUCTURE_TTL = 24 * 3600

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS catalog
    USING fts5(code, title, data_start, data_end, last_update);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS structures (
    dataset TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    fetched_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_state (
    source TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    updated_at REAL NOT NULL,
    PRIMARY KEY (source, key)
);
"""


def connect() -> sqlite3.Connection:
    """Ouvre la base et garantit le schéma de base (idempotent)."""
    config.data_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.db_path())
    conn.executescript(_SCHEMA)
    return conn


# Alias interne historique.
_conn = connect


# ------------------------------------------------------------------ catalogue

def catalog_is_stale() -> bool:
    with connect() as c:
        row = c.execute("SELECT value FROM meta WHERE key='catalog_at'").fetchone()
    return row is None or time.time() - float(row[0]) > CATALOG_TTL


def replace_catalog(rows: list[dict]) -> None:
    with connect() as c:
        c.execute("DELETE FROM catalog")
        c.executemany(
            "INSERT INTO catalog VALUES (:code, :title, :data_start, :data_end, :last_update)",
            rows,
        )
        c.execute("INSERT OR REPLACE INTO meta VALUES ('catalog_at', ?)", (str(time.time()),))


def search_catalog(query: str, limit: int) -> list[dict]:
    # Requête FTS5 : chaque terme est cité (guillemets doublés) pour neutraliser
    # la syntaxe spéciale ; une requête malformée renvoie simplement vide.
    terms = " ".join('"' + t.replace('"', '""') + '"' for t in query.split())
    if not terms:
        return []
    with connect() as c:
        try:
            rows = c.execute(
                """
                SELECT code, title, data_start, data_end
                FROM catalog WHERE catalog MATCH ? ORDER BY rank LIMIT ?
                """,
                (terms, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [{"code": r[0], "title": r[1], "period": f"{r[2]}–{r[3]}"} for r in rows]


def catalog_last_update(dataset: str) -> str | None:
    """Date de dernière mise à jour d'un dataset selon le TOC local."""
    with connect() as c:
        row = c.execute(
            "SELECT last_update FROM catalog WHERE code = ?", (dataset,)
        ).fetchone()
    return row[0] if row else None


# ----------------------------------------------------------------- structures

def get_structure(dataset: str, ignore_ttl: bool = False) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT payload, fetched_at FROM structures WHERE dataset=?", (dataset,)
        ).fetchone()
    if row and (ignore_ttl or time.time() - row[1] < STRUCTURE_TTL):
        return json.loads(row[0])
    return None


def put_structure(dataset: str, structure: dict) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO structures VALUES (?, ?, ?)",
            (dataset, json.dumps(structure), time.time()),
        )


# --------------------------------------------------------------- états de sync

def get_sync_state(source: str, key: str) -> str | None:
    """Signal de fraîcheur local pour ``(source, key)``, ou ``None`` si inconnu."""
    with connect() as c:
        row = c.execute(
            "SELECT value FROM sync_state WHERE source=? AND key=?", (source, key)
        ).fetchone()
    return row[0] if row else None


def set_sync_state(source: str, key: str, value: str | None) -> None:
    """Enregistre le signal de fraîcheur local pour ``(source, key)``."""
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO sync_state VALUES (?,?,?,?)",
            (source, key, value, time.time()),
        )


def list_sync_state(source: str) -> dict[str, str | None]:
    """Tous les états enregistrés pour une source."""
    with connect() as c:
        rows = c.execute(
            "SELECT key, value FROM sync_state WHERE source=?", (source,)
        ).fetchall()
    return dict(rows)
