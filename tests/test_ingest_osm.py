"""Pipeline OSM (§7.3) : jointure/comptage, écriture de partition, config, signal de
fraîcheur.

Aucun de ces tests ne requiert le réseau. Ceux qui appellent réellement
`osmium` (aucun ici : la jointure/comptage travaille directement sur du
GeoParquet synthétique) sont marqués skipif en l'absence du binaire ; le seul
test réseau (extrait Luxembourg réel) est marqué `@pytest.mark.network`.
"""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

import duckdb
import pytest

from nutshell_mcp import config, geo, indicators, registry
from nutshell_mcp import ingest_osm as osm

HAS_OSMIUM = shutil.which("osmium") is not None


# --------------------------------------------------------------- fixtures géo

def _write_nuts3_geometries(path: Path) -> None:
    """Trois zones NUTS3 synthétiques, non superposées : LU000, BE100, BE200, FR101."""
    features = [
        {
            "type": "Feature",
            "properties": {"NUTS_ID": "LU000", "CNTR_CODE": "LU", "NAME_LATN": "Luxembourg"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[6.0, 49.5], [6.5, 49.5], [6.5, 50.0], [6.0, 50.0], [6.0, 49.5]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"NUTS_ID": "BE100", "CNTR_CODE": "BE", "NAME_LATN": "Bruxelles"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4.0, 50.5], [4.5, 50.5], [4.5, 51.0], [4.0, 51.0], [4.0, 50.5]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"NUTS_ID": "BE200", "CNTR_CODE": "BE", "NAME_LATN": "Anvers"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4.6, 50.2], [4.9, 50.2], [4.9, 50.4], [4.6, 50.4], [4.6, 50.2]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"NUTS_ID": "FR101", "CNTR_CODE": "FR", "NAME_LATN": "Paris"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[2.0, 48.5], [2.5, 48.5], [2.5, 49.0], [2.0, 49.0], [2.0, 48.5]]],
            },
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def zones_nuts3(data_dir: Path) -> Path:
    """Géométries + table `geo` NUTS3 synthétiques : LU000, BE100, BE200, FR101."""
    _write_nuts3_geometries(geo.geometry_path("NUTS3"))
    rows = [
        ("LU000", "NUTS3", "Luxembourg", "LU0", 2024, "LU"),
        ("BE100", "NUTS3", "Bruxelles", "BE1", 2024, "BE"),
        ("BE200", "NUTS3", "Anvers", "BE2", 2024, "BE"),
        ("FR101", "NUTS3", "Paris", "FR10", 2024, "FR"),
    ]
    with geo._conn() as conn:
        conn.execute("DELETE FROM geo WHERE level = 'NUTS3'")
        conn.executemany("INSERT INTO geo VALUES (?,?,?,?,?,?)", rows)
    return data_dir


@pytest.fixture
def hospitals_spec(data_dir: Path):
    """Spec `hospitals_count` restreinte à NUTS3 (seul niveau doté de géométries de test)."""
    payload = {
        "id": "hospitals_count",
        "label": "Hôpitaux (comptage OSM)",
        "unit": "COUNT",
        "source": "osm",
        "frequency": "SNAPSHOT",
        "geo_levels": ["NUTS3"],
        "extraction": {
            "tags": [{"key": "amenity", "value": "hospital"}],
            "geometry": ["node", "way", "relation"],
            "aggregation": "count",
        },
    }
    return registry.parse(payload)


def _write_poi_parquet(path: Path, points: list[tuple], polygons: list[tuple]) -> None:
    """Écrit un GeoParquet POI de test (mêmes conventions que `_refilter_to_geoparquet`).

    ``points`` : liste de ``(lon, lat, amenity)``. ``polygons`` : liste de
    ``(wkt, amenity)`` — simule un way/relation dont le centroïde sera utilisé
    à l'agrégation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("CREATE TABLE poi (id BIGINT, amenity VARCHAR, geom GEOMETRY)")
    for i, (lon, lat, amenity) in enumerate(points):
        con.execute(
            "INSERT INTO poi VALUES (?, ?, ST_Point(?, ?))", [i, amenity, lon, lat]
        )
    for i, (wkt, amenity) in enumerate(polygons, start=1000):
        con.execute(
            "INSERT INTO poi VALUES (?, ?, ST_GeomFromText(?))", [i, amenity, wkt]
        )
    con.execute(f"COPY poi TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


# --------------------------------------------------------- jointure / comptage

def test_aggregate_compte_point_dans_zone_avec_zero_explicite(
    zones_nuts3, hospitals_spec
):
    """Un POI dans sa zone compte ; une zone du périmètre sans POI reçoit un zéro explicite."""
    lu_parquet = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    be_parquet = config.mirror_dir() / "osm" / "poi_belgium.parquet"
    _write_poi_parquet(lu_parquet, points=[(6.2, 49.7, "hospital")], polygons=[])
    _write_poi_parquet(be_parquet, points=[(4.2, 50.7, "hospital")], polygons=[])

    extract_info = {
        "luxembourg": {"country": "LU", "poi_path": lu_parquet},
        "belgium": {"country": "BE", "poi_path": be_parquet},
    }
    rows = osm._aggregate(hospitals_spec, extract_info, "2026-08")
    by_zone = {r["geo_code"]: r["value"] for r in rows}

    assert by_zone["LU000"] == 1.0
    assert by_zone["BE100"] == 1.0
    # BE200 est dans le périmètre (pays BE couvert par l'extrait belgium) mais
    # ne contient aucun POI : zéro EXPLICITE, pas d'absence de ligne.
    assert by_zone["BE200"] == 0.0
    # FR101 n'est couvert par aucun extrait configuré : hors périmètre, absent.
    assert "FR101" not in by_zone
    assert all(r["quality"] == "osm_completeness_unknown" for r in rows)
    assert all(r["time"] == "2026-08" for r in rows)


def test_aggregate_way_compte_via_centroide(zones_nuts3, hospitals_spec):
    """Un way/relation (polygone) est rattaché à sa zone via son centroïde."""
    lu_parquet = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    # Petit carré (empreinte de bâtiment) dont le centroïde tombe dans LU000.
    building = "POLYGON((6.29 49.69, 6.31 49.69, 6.31 49.71, 6.29 49.71, 6.29 49.69))"
    _write_poi_parquet(lu_parquet, points=[], polygons=[(building, "hospital")])

    extract_info = {"luxembourg": {"country": "LU", "poi_path": lu_parquet}}
    rows = osm._aggregate(hospitals_spec, extract_info, "2026-08")
    by_zone = {r["geo_code"]: r["value"] for r in rows}
    assert by_zone["LU000"] == 1.0


def test_aggregate_poi_hors_zone_ignore(zones_nuts3, hospitals_spec):
    """Un POI qui ne tombe dans aucune zone du référentiel n'est simplement pas compté."""
    lu_parquet = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    _write_poi_parquet(lu_parquet, points=[(10.0, 10.0, "hospital")], polygons=[])

    extract_info = {"luxembourg": {"country": "LU", "poi_path": lu_parquet}}
    rows = osm._aggregate(hospitals_spec, extract_info, "2026-08")
    by_zone = {r["geo_code"]: r["value"] for r in rows}
    assert by_zone["LU000"] == 0.0  # zéro explicite : zone du périmètre, aucun match


def test_aggregate_clip_transfrontalier(zones_nuts3, hospitals_spec):
    """Un POI de l'extrait LU qui déborde géométriquement en Belgique n'est compté nulle part.

    Reproduit le piège n°3 du spike : sans clip, ce POI serait attribué à
    BE100 (géométriquement correct) alors qu'il vient de l'extrait
    Luxembourg — double comptage potentiel si l'extrait belge couvre
    également ce secteur. Le clip (pays de l'extrait == pays de la zone)
    l'exclut, et l'extrait belge (qui n'a pas ce POI) ne le compte pas non
    plus : le POI est perdu, ce qui est le comportement attendu et documenté.
    """
    lu_parquet = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    be_parquet = config.mirror_dir() / "osm" / "poi_belgium.parquet"
    # Point géométriquement dans BE100, mais présent dans le fichier de l'extrait LU.
    _write_poi_parquet(lu_parquet, points=[(4.2, 50.7, "hospital")], polygons=[])
    _write_poi_parquet(be_parquet, points=[], polygons=[])

    extract_info = {
        "luxembourg": {"country": "LU", "poi_path": lu_parquet},
        "belgium": {"country": "BE", "poi_path": be_parquet},
    }
    rows = osm._aggregate(hospitals_spec, extract_info, "2026-08")
    by_zone = {r["geo_code"]: r["value"] for r in rows}
    assert by_zone["LU000"] == 0.0
    assert by_zone["BE100"] == 0.0  # pas compté malgré la géométrie : clip pays


def test_aggregate_plusieurs_tags_combines_en_ou(zones_nuts3):
    """Deux tags du même indicateur sont combinés en OU (registry.py, OsmExtraction)."""
    payload = {
        "id": "health_facilities_count",
        "label": "Établissements de santé",
        "unit": "COUNT",
        "source": "osm",
        "frequency": "SNAPSHOT",
        "geo_levels": ["NUTS3"],
        "extraction": {
            "tags": [
                {"key": "amenity", "value": "hospital"},
                {"key": "amenity", "value": "clinic"},
            ],
            "geometry": ["node"],
            "aggregation": "count",
        },
    }
    spec = registry.parse(payload)
    lu_parquet = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    _write_poi_parquet(
        lu_parquet,
        points=[(6.1, 49.6, "hospital"), (6.2, 49.7, "clinic"), (6.3, 49.8, "pharmacy")],
        polygons=[],
    )
    extract_info = {"luxembourg": {"country": "LU", "poi_path": lu_parquet}}
    rows = osm._aggregate(spec, extract_info, "2026-08")
    by_zone = {r["geo_code"]: r["value"] for r in rows}
    assert by_zone["LU000"] == 2.0  # hospital + clinic, pas pharmacy


# ------------------------------------------------------------- écriture partition

def test_ecriture_partition_depuis_agregation(zones_nuts3, hospitals_spec):
    lu_parquet = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    _write_poi_parquet(lu_parquet, points=[(6.2, 49.7, "hospital")], polygons=[])
    extract_info = {"luxembourg": {"country": "LU", "poi_path": lu_parquet}}
    rows = osm._aggregate(hospitals_spec, extract_info, "2026-08")

    n = indicators.write_partition(hospitals_spec, rows, source_date="extrait 2026-08")
    assert n == len(rows)

    info = indicators.materialized_info("hospitals_count")
    assert info is not None
    assert info["source"] == "osm"
    assert info["source_date"] == "extrait 2026-08"

    columns, out, provenance = indicators.query(["hospitals_count"], ["LU000"])
    assert columns == ["geo_code", "time", "hospitals_count"]
    # Le flag qualité (systématique pour OSM, §7.3) est reporté dans la cellule pivotée.
    assert out == [["LU000", "2026-08", "1 [osm_completeness_unknown]"]]
    assert provenance["hospitals_count"]["source"] == "osm"


# --------------------------------------------------------------------- config

def test_configured_extracts_defaut(data_dir, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NUTSHELL_OSM_EXTRACTS", raising=False)
    assert osm.configured_extracts() == ["europe/luxembourg"]


def test_configured_extracts_env(data_dir, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NUTSHELL_OSM_EXTRACTS", " europe/luxembourg, europe/belgium ,")
    assert osm.configured_extracts() == ["europe/luxembourg", "europe/belgium"]


def test_extract_name_et_pays():
    assert osm._extract_name("europe/luxembourg") == "luxembourg"
    assert osm._extract_country("luxembourg") == "LU"
    assert osm._extract_country("belgium") == "BE"
    with pytest.raises(RuntimeError, match="pays inconnu"):
        osm._extract_country("narnia")


def test_tag_expressions_et_paires(hospitals_spec):
    exprs = osm._tag_filter_expressions([hospitals_spec])
    assert exprs == ["n/amenity=hospital", "r/amenity=hospital", "w/amenity=hospital"]
    assert osm._tag_pairs([hospitals_spec]) == [("amenity", "hospital")]


# ------------------------------------------------------------ signal de fraîcheur

def test_parse_timestamp_sortie_figee():
    # Sortie réelle observée dans le spike (osmium fileinfo -g header.option.timestamp).
    assert osm._parse_timestamp("2026-08-21T20:21:11Z\n") == "2026-08-21T20:21:11Z"


@pytest.mark.parametrize("bad", ["", "not-a-timestamp", "2026-08-21", "  \n"])
def test_parse_timestamp_rejette_sortie_invalide(bad):
    with pytest.raises(RuntimeError, match="timestamp"):
        osm._parse_timestamp(bad)


# --------------------------------------------------------- mode hors ligne / erreurs

def test_sync_sans_osmium_echoue_proprement(
    data_dir, registry_dir, hospitals_spec, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(osm.shutil, "which", lambda _name: None)
    report = osm.sync([hospitals_spec], full=False)
    assert not report.ok
    assert any("osmium-tool" in reason for _item, reason in report.failed_items)


def test_sync_extract_hors_ligne_sans_cache_leve(data_dir, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NUTSHELL_OFFLINE", "1")
    with pytest.raises(RuntimeError, match="hors ligne"):
        osm._sync_extract(
            "europe/luxembourg", full=False, tag_exprs=[], tag_pairs=[],
            report=__import__("nutshell_mcp.sync", fromlist=["SyncReport"]).SyncReport("osm"),
        )


def test_sync_extract_hors_ligne_avec_cache_reutilise(
    data_dir, monkeypatch: pytest.MonkeyPatch
):
    from nutshell_mcp import store
    from nutshell_mcp.sync import SyncReport

    poi_path = config.mirror_dir() / "osm" / "poi_luxembourg.parquet"
    poi_path.parent.mkdir(parents=True, exist_ok=True)
    poi_path.write_bytes(b"")  # présence suffit : le contenu n'est pas relu ici
    store.set_sync_state("osm", "extract:luxembourg:md5", "deadbeef")
    store.set_sync_state("osm", "extract:luxembourg:timestamp", "2026-08-21T20:21:11Z")

    monkeypatch.setenv("NUTSHELL_OFFLINE", "1")
    report = SyncReport("osm")
    info = osm._sync_extract(
        "europe/luxembourg", full=False, tag_exprs=[], tag_pairs=[], report=report
    )
    assert info["country"] == "LU"
    assert info["month"] == "2026-08"
    assert info["changed"] is False
    assert report.unchanged_items == ["extract:luxembourg"]


# -------------------------------------------------------------------- réseau réel

@pytest.mark.network
@pytest.mark.skipif(not HAS_OSMIUM, reason="osmium-tool absent du PATH")
def test_sync_luxembourg_reel(data_dir, monkeypatch: pytest.MonkeyPatch):
    """Bout en bout sur le vrai extrait Luxembourg (~47 Mo, téléchargé une fois)."""
    monkeypatch.setenv("NUTSHELL_OSM_EXTRACTS", "europe/luxembourg")
    directory = config.data_dir() / "registry"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "hospitals_count.yaml").write_text(
        textwrap.dedent("""
            id: hospitals_count
            label: "Hôpitaux (comptage OSM)"
            unit: COUNT
            source: osm
            frequency: SNAPSHOT
            geo_levels: [NUTS3]
            extraction:
              tags: [{key: amenity, value: hospital}]
              geometry: [node, way, relation]
              aggregation: count
        """),
        encoding="utf-8",
    )
    monkeypatch.setenv("NUTSHELL_REGISTRY_DIR", str(directory))
    geo.ingest()  # référentiel geo réel (réseau, mais léger : NUTS3 Europe)
    specs = registry.load_all(source="osm")

    report = osm.sync(specs, full=True)
    assert report.ok, report.render()

    columns, rows, provenance = indicators.query(["hospitals_count"], ["LU000"])
    assert rows, "aucune ligne pour LU000 : la jointure spatiale a échoué"
    cell = rows[0][columns.index("hospitals_count")]
    assert cell.endswith("[osm_completeness_unknown]"), cell
    value = int(cell.split(" ", 1)[0])
    assert 5 <= value <= 30, f"nombre d'hôpitaux LU implausible : {value}"
    assert provenance["hospitals_count"]["source"] == "osm"
    assert provenance["hospitals_count"]["source_date"].startswith("extrait ")

    # Rejeu : rien n'a changé côté Geofabrik, tout doit être 'unchanged'.
    report2 = osm.sync(specs, full=False)
    assert report2.ok
    assert not report2.updated_items
    assert "extract:luxembourg" in report2.unchanged_items
