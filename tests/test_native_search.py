"""Grain natif : recherche du catalogue, période de get_structure, tri de list_codes, accents."""

from __future__ import annotations

import pytest

from nutshell_mcp import geo, server, store

CATALOG = [
    {"code": "nama_10r_3gdp", "data_start": "2000", "data_end": "2024", "last_update": "",
     "title": "Gross domestic product (GDP) at current market prices by NUTS 3 region"},
    {"code": "tour_occ_nin2m", "data_start": "2020", "data_end": "2025", "last_update": "",
     "title": "Nights spent at tourist accommodation establishments by month and NUTS 2 region"},
]


@pytest.fixture
def catalog(data_dir, monkeypatch):
    monkeypatch.setenv("NUTSHELL_OFFLINE", "1")
    store.replace_catalog(CATALOG)
    store.put_structure("tour_occ_nin2m", {
        "geo": {"label": "Geo", "codes": {
            "BE10": "Région de Bruxelles-Capitale", "DE7": "Hessen", "EE": "Estonia",
            "ES": "Spain", "ES511": "Barcelona", "ES51": "Cataluña", "ES70": "Canarias",
            "ES7": "Canarias", "PT20": "Região Autónoma dos Açores (PT)",
        }},
        "time": {"label": "Time", "codes": {"2025": "2025"}},
    })
    return data_dir


def test_search_catalog_pluriel_trouve_le_singulier(catalog):
    hits = store.search_catalog("gross domestic product regions", 10)
    assert [h["code"] for h in hits] == ["nama_10r_3gdp"]
    assert hits[0]["partial"] is False


def test_search_catalog_repli_sur_un_terme(catalog):
    hits = store.search_catalog("GDP per inhabitant", 10)
    assert [h["code"] for h in hits] == ["nama_10r_3gdp"]
    assert hits[0]["partial"] is True


async def test_search_datasets_signale_le_repli(catalog):
    out = await server.search_datasets("GDP per inhabitant")
    assert out.startswith("Aucun dataset ne contient tous les termes")
    assert "nama_10r_3gdp" in out


async def test_get_structure_affiche_la_periode_du_catalogue(catalog):
    out = await server.get_structure("tour_occ_nin2m")
    assert "- time [Time] : 2020 → 2025" in out


async def test_list_codes_codes_prefixes_avant_libelles(catalog):
    out = await server.list_codes("tour_occ_nin2m", "geo", contains="ES")
    codes = [line.split(" : ")[0] for line in out.splitlines()]
    # Codes ES par niveau, puis libellés contenant « es » (Bruxelles, Hessen, Açores…).
    assert codes[:5] == ["ES", "ES7", "ES51", "ES70", "ES511"]
    assert set(codes[5:]) == {"BE10", "DE7", "EE", "PT20"}


async def test_list_codes_ignore_les_accents(catalog):
    out = await server.list_codes("tour_occ_nin2m", "geo", contains="acores")
    assert out == "PT20 : Região Autónoma dos Açores (PT)"


def test_zones_ignore_les_accents(geo_table):
    assert [z["geo_code"] for z in geo.zones("NUTS2", contains="Île-de-France")] == ["FR10"]
    assert [z["geo_code"] for z in geo.zones("NUTS2", contains="rhone")] == ["FRK2"]
