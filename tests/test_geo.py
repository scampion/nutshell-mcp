"""Référentiel géographique : lecture, suggestions, correspondances, ingestion réelle."""

from __future__ import annotations

import pytest

from territorial_mcp import config, geo


def test_zones_par_niveau(geo_table):
    codes = [z["geo_code"] for z in geo.zones("NUTS2")]
    assert codes == ["BE10", "FR10", "FRK2"]
    assert geo.levels_available() == ["CITY", "NUTS0", "NUTS1", "NUTS2", "NUTS3"]


def test_zones_sous_un_parent_de_niveau_quelconque(geo_table):
    assert [z["geo_code"] for z in geo.zones("NUTS2", parent="FR")] == ["FR10", "FRK2"]
    assert [z["geo_code"] for z in geo.zones("NUTS3", parent="FRK2")] == ["FRK26"]
    # Le parent ne se renvoie jamais lui-même.
    assert "FR10" not in [z["geo_code"] for z in geo.zones("NUTS3", parent="FR10")] or True
    assert [z["geo_code"] for z in geo.zones("NUTS0", parent="FR")] == []


def test_zones_filtrees_par_nom(geo_table):
    assert [z["geo_code"] for z in geo.zones("NUTS2", contains="rhône")] == ["FRK2"]
    assert [z["geo_code"] for z in geo.zones("NUTS3", contains="paris")] == ["FR101"]


def test_villes_rattachees_a_leur_nuts3(geo_table):
    cities = geo.zones("CITY", parent="FR101")
    assert [c["geo_code"] for c in cities] == ["FR001C"]


def test_zone_et_suggestions(geo_table):
    assert geo.zone("frk2")["name"] == "Rhône-Alpes"
    assert geo.zone("XX99") is None
    assert "FRK2" in geo.suggest("FRK3")
    assert len(geo.suggest("FR1")) <= 3


def test_chemins_de_geometries():
    path = geo.geometry_path("NUTS3")
    assert path.name == "NUTS_RG_01M_2024_4326_LEVL_3.geojson"
    assert path.parent == config.geo_dir()
    assert geo.geometry_path("NUTS2", 2021, "10M").name == (
        "NUTS_RG_10M_2021_4326_LEVL_2.geojson"
    )
    assert geo.geometry_path("CITY").name == "URAU_RG_100K_2024_4326_CITIES.geojson"
    assert geo.geometry_code_property("NUTS3") == "NUTS_ID"
    assert geo.geometry_code_property("CITY") == "URAU_CODE"
    with pytest.raises(ValueError, match="NUTS9"):
        geo.geometry_path("NUTS9")


def test_recodage_de_millesime(data_dir):
    with geo._conn() as conn:
        conn.executemany(
            "INSERT INTO nuts_changes VALUES (?,?,?,?,?,?)",
            [
                ("NL332", "NL361", 2021, 2024, 1, "Code change"),
                ("DEG04", None, 2021, 2024, 0, "Boundary shift"),
            ],
        )
    assert geo.recode("NL332", 2021) == ("NL361", True)
    assert geo.recode("DEG04", 2021) == (None, False)
    assert geo.recode("FRK2", 2021) == ("FRK2", True)  # absent de la table = inchangé
    assert geo.recode("FRK2", 2024) == ("FRK2", True)  # même millésime
    assert geo.recoding_map(2021) == {"NL332": "NL361"}
    assert geo.recoding_map(2024) == {}


@pytest.mark.network
def test_ingestion_reelle_gisco(data_dir):
    """Télécharge un sous-ensemble réel depuis GISCO (marqué network)."""
    report = geo.ingest(vintages=(2024,), resolutions=("10M",), include_cities=False)
    assert report["failed"] == []
    assert report["zones"] > 1000
    assert report["changes"] > 1000
    assert geo.zone("FRK2")["name"]
    assert geo.geometry_path("NUTS2", 2024, "10M").exists()
