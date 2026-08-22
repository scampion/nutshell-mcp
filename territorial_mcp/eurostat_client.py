"""Client HTTP pour les APIs de dissémination Eurostat.

Deux endpoints utilisés :
- Catalogue (table of contents) : liste plate de tous les datasets.
- API "Statistics" (JSON-stat 2.0) : données + métadonnées de dimensions.

Le parsing SDMX 2.1 XML est volontairement évité : l'astuce
`lastTimePeriod=1` sur l'endpoint Statistics renvoie les codelists
complètes avec un volume de données minimal.
"""

from __future__ import annotations

import httpx

BASE = "https://ec.europa.eu/eurostat/api/dissemination"
TOC_URL = f"{BASE}/catalogue/toc/txt?lang=en"
DATA_URL = f"{BASE}/statistics/1.0/data/{{dataset}}"

_client = httpx.AsyncClient(timeout=60, follow_redirects=True)


async def fetch_toc() -> list[dict]:
    """Télécharge le catalogue (TSV) et le réduit aux datasets."""
    r = await _client.get(TOC_URL)
    r.raise_for_status()
    lines = r.text.splitlines()
    header = lines[0].split("\t")
    idx = {name.strip('"'): i for i, name in enumerate(header)}
    out, seen = [], set()
    for line in lines[1:]:
        cols = [c.strip('"') for c in line.split("\t")]
        if len(cols) < len(header):
            continue
        if cols[idx["type"]] not in ("dataset", "table"):
            continue
        code = cols[idx["code"]]
        if code in seen:
            continue
        seen.add(code)
        out.append(
            {
                "code": code,
                "title": cols[idx["title"]].strip(),
                "last_update": cols[idx.get("last update of data", 3)],
                "data_start": cols[idx.get("data start", 5)],
                "data_end": cols[idx.get("data end", 6)],
            }
        )
    return out


async def fetch_jsonstat(dataset: str, params: dict[str, str | list[str]]) -> dict:
    """Appelle l'API Statistics et renvoie le JSON-stat brut."""
    base = {"format": "JSON", "lang": "EN"}
    r = await _client.get(DATA_URL.format(dataset=dataset), params={**base, **params})
    if r.status_code == 400:
        # Eurostat renvoie un message d'erreur structuré
        try:
            msg = r.json().get("error", {}).get("label", r.text[:300])
        except Exception:
            msg = r.text[:300]
        raise EurostatError(f"Requête rejetée par Eurostat : {msg}")
    if r.status_code == 404:
        raise EurostatError(f"Dataset '{dataset}' introuvable.")
    r.raise_for_status()
    return r.json()


async def fetch_structure(dataset: str) -> dict:
    """Renvoie {dimension: {"label": str, "codes": {code: label}}}.

    Utilise lastTimePeriod=1 pour minimiser les données tout en
    récupérant les codelists complètes du dataset.
    """
    js = await fetch_jsonstat(dataset, {"lastTimePeriod": "1"})
    dims = {}
    for dim_id in js["id"]:
        d = js["dimension"][dim_id]
        codes = d["category"].get("label", {})
        if not codes:  # parfois seulement un index
            codes = {c: c for c in d["category"]["index"]}
        dims[dim_id] = {"label": d.get("label", dim_id), "codes": codes}
    return dims


class EurostatError(Exception):
    """Erreur métier à remonter telle quelle au modèle."""
