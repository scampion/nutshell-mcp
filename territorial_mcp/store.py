"""Cache local SQLite : catalogue indexé en FTS5 + structures avec TTL.

Un seul fichier eurostat.db. Le catalogue est rafraîchi si plus vieux
que CATALOG_TTL, les structures (codelists) si plus vieilles que
STRUCTURE_TTL. Remplaçable par DuckDB si on veut des agrégations
côté serveur plus tard.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "eurostat.db"
CATALOG_TTL = 24 * 3600
STRUCTURE_TTL = 24 * 3600


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS catalog
            USING fts5(code, title, data_start, data_end, last_update);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS structures (
            dataset TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            fetched_at REAL NOT NULL
        );
        """
    )
    return conn


def catalog_is_stale() -> bool:
    with _conn() as c:
        row = c.execute("SELECT value FROM meta WHERE key='catalog_at'").fetchone()
    return row is None or time.time() - float(row[0]) > CATALOG_TTL


def replace_catalog(rows: list[dict]) -> None:
    with _conn() as c:
        c.execute("DELETE FROM catalog")
        c.executemany(
            "INSERT INTO catalog VALUES (:code, :title, :data_start, :data_end, :last_update)",
            rows,
        )
        c.execute(
            "INSERT OR REPLACE INTO meta VALUES ('catalog_at', ?)", (str(time.time()),)
        )


def search_catalog(query: str, limit: int) -> list[dict]:
    # Requête FTS5 : on échappe chaque terme pour éviter la syntaxe spéciale
    terms = " ".join(f'"{t}"' for t in query.split())
    with _conn() as c:
        rows = c.execute(
            """
            SELECT code, title, data_start, data_end
            FROM catalog WHERE catalog MATCH ? ORDER BY rank LIMIT ?
            """,
            (terms, limit),
        ).fetchall()
    return [
        {"code": r[0], "title": r[1], "period": f"{r[2]}–{r[3]}"} for r in rows
    ]


def get_structure(dataset: str, ignore_ttl: bool = False) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT payload, fetched_at FROM structures WHERE dataset=?", (dataset,)
        ).fetchone()
    if row and (ignore_ttl or time.time() - row[1] < STRUCTURE_TTL):
        return json.loads(row[0])
    return None


def put_structure(dataset: str, structure: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO structures VALUES (?, ?, ?)",
            (dataset, json.dumps(structure), time.time()),
        )
