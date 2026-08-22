"""Miroir local Eurostat pour le mode offline total.

Pipeline : bulk TSV.gz (endpoint SDMX 2.1) → Parquet long format
(une ligne = dims + time + value + flag), un fichier par dataset dans
mirror/{code}.parquet. La synchronisation est pilotée par le TOC :
un dataset n'est re-téléchargé que si son "last update of data" a
changé. Les structures (DSD) sont rafraîchies au passage pour que
la validation et list_codes fonctionnent hors ligne.

Usage :
    python -m territorial_mcp.mirror --datasets nama_10_gdp,demo_pjan
    python -m territorial_mcp.mirror --all            # ~24 Go compressés !
    python -m territorial_mcp.mirror --resync         # datasets déjà mirrorés
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import io
import sqlite3
import sys
import time
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from . import eurostat_client as api
from . import store

MIRROR_DIR = Path(__file__).parent.parent / "mirror"
BULK_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "{code}?format=TSV&compressed=true"
)
BATCH = 200_000  # lignes par RecordBatch parquet


# ------------------------------------------------------------------ state

def _init_state() -> None:
    with sqlite3.connect(store.DB_PATH) as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS mirror_state (
                   dataset TEXT PRIMARY KEY,
                   toc_last_update TEXT,
                   synced_at REAL,
                   rows INTEGER,
                   dims TEXT
               )"""
        )


def mirror_info(dataset: str) -> dict | None:
    _init_state()
    with sqlite3.connect(store.DB_PATH) as c:
        row = c.execute(
            "SELECT toc_last_update, dims FROM mirror_state WHERE dataset=?",
            (dataset,),
        ).fetchone()
    path = MIRROR_DIR / f"{dataset}.parquet"
    if row and path.exists():
        return {"path": str(path), "last_update": row[0], "dims": row[1].split(",")}
    return None


def mirrored_datasets() -> list[str]:
    _init_state()
    with sqlite3.connect(store.DB_PATH) as c:
        return [r[0] for r in c.execute("SELECT dataset FROM mirror_state")]


# -------------------------------------------------------------- ingestion

def _parse_tsv(stream: io.TextIOBase):
    """Génère (dims, [(codes..., time, value, flag), ...]) depuis un bulk TSV.

    En-tête type : "freq,unit,na_item,geo\\TIME_PERIOD\t2020\t2021..."
    Cellules : "123.4", "123.4 p" (flag), ":" (absent), ": c" (confidentiel).
    """
    reader = csv.reader(stream, delimiter="\t")
    header = next(reader)
    dims = header[0].split("\\")[0].split(",")
    times = [t.strip() for t in header[1:]]
    for row in reader:
        codes = [c.strip() for c in row[0].split(",")]
        for t, cell in zip(times, row[1:]):
            cell = cell.strip()
            if not cell:
                continue
            val, _, flag = cell.partition(" ")
            if val == ":":
                continue  # pas de valeur (le flag seul n'est pas mirroré)
            try:
                yield dims, codes, t, float(val), flag.strip()
            except ValueError:
                continue


async def sync_dataset(code: str, toc_update: str) -> int:
    MIRROR_DIR.mkdir(exist_ok=True)
    tmp = MIRROR_DIR / f"{code}.parquet.tmp"
    dims_ref: list[str] = []
    writer = None
    nrows = 0
    cols: dict[str, list] = {}

    def flush():
        nonlocal writer, nrows
        if not cols.get("value"):
            return
        table = pa.table({k: pa.array(v, type=pa.string() if k != "value" else pa.float64())
                          for k, v in cols.items()})
        if writer is None:
            writer = pq.ParquetWriter(tmp, table.schema, compression="zstd")
        writer.write_table(table)
        nrows += len(table)
        for v in cols.values():
            v.clear()

    async with api._client.stream("GET", BULK_URL.format(code=code)) as r:
        r.raise_for_status()
        raw = io.BytesIO()
        async for chunk in r.aiter_bytes():
            raw.write(chunk)
    raw.seek(0)
    text = io.TextIOWrapper(gzip.GzipFile(fileobj=raw), encoding="utf-8")

    for dims, codes, t, val, flag in _parse_tsv(text):
        if not dims_ref:
            dims_ref = dims
            for d in dims:
                cols[d] = []
            cols["time"], cols["value"], cols["flag"] = [], [], []
        for d, c in zip(dims, codes):
            cols[d].append(c)
        cols["time"].append(t)
        cols["value"].append(val)
        cols["flag"].append(flag)
        if len(cols["value"]) >= BATCH:
            flush()
    flush()
    if writer:
        writer.close()
        tmp.replace(MIRROR_DIR / f"{code}.parquet")

    # structure (DSD) pour la validation offline
    try:
        store.put_structure(code, await api.fetch_structure(code))
    except Exception as e:
        print(f"  ! structure {code} non récupérée : {e}", file=sys.stderr)

    _init_state()
    with sqlite3.connect(store.DB_PATH) as c:
        c.execute(
            "INSERT OR REPLACE INTO mirror_state VALUES (?,?,?,?,?)",
            (code, toc_update, time.time(), nrows, ",".join(dims_ref)),
        )
    return nrows


# ------------------------------------------------------------------- sync

async def sync(targets: list[str] | None, resync: bool, rate: float) -> None:
    """targets=None → tout le catalogue. Piloté par le TOC : skip si inchangé."""
    toc = await api.fetch_toc()
    toc_by_code = {}
    for row in toc:
        toc_by_code.setdefault(row["code"], row)
    store.replace_catalog(toc)  # le catalogue local sert la recherche offline

    if resync:
        targets = mirrored_datasets()
    if targets is None:
        total_cells = 8.48e9
        print(f"ATTENTION : miroir complet ≈ 24 Go compressés "
              f"({len(toc_by_code)} datasets). Ctrl-C pour annuler (5 s)…")
        await asyncio.sleep(5)
        targets = list(toc_by_code)

    done = skipped = failed = 0
    for code in targets:
        row = toc_by_code.get(code)
        if row is None:
            print(f"  ? {code} absent du TOC, ignoré")
            continue
        info = mirror_info(code)
        if info and info["last_update"] == row["last_update"]:
            skipped += 1
            continue
        t0 = time.time()
        try:
            n = await sync_dataset(code, row["last_update"])
            done += 1
            print(f"  ✓ {code}: {n:,} lignes en {time.time()-t0:.1f}s")
        except Exception as e:
            failed += 1
            print(f"  ✗ {code}: {e}", file=sys.stderr)
        await asyncio.sleep(max(0.0, 1.0 / rate - (time.time() - t0)))
    print(f"Sync terminé : {done} mis à jour, {skipped} inchangés, {failed} échecs.")


def main() -> None:
    p = argparse.ArgumentParser(description="Miroir local Eurostat")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--datasets", help="codes séparés par des virgules")
    g.add_argument("--all", action="store_true", help="tout le catalogue (~24 Go)")
    g.add_argument("--resync", action="store_true",
                   help="re-vérifie les datasets déjà mirrorés (TOC-driven)")
    p.add_argument("--rate", type=float, default=2.0, help="requêtes/s (défaut 2)")
    a = p.parse_args()
    targets = a.datasets.split(",") if a.datasets else None
    asyncio.run(sync(targets, a.resync, a.rate))


if __name__ == "__main__":
    main()
