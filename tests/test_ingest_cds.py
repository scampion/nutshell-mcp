"""Pipeline Copernicus : fournisseurs, recalage, statistiques zonales, partition.

Aucun test n'a besoin du réseau ni d'une clé CDS : le raster est synthétique
(gradient connu), les géométries sont écrites dans `tmp_path`, et le
fournisseur `cds` est simulé. Le seul test réseau (ARCO réel, deux pas de
temps) est marqué `network`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from nutshell_mcp import config, indicators, registry, store
from nutshell_mcp import ingest_cds as cds

# Grille 4×4 de 1° couvrant lon 0→4, lat 0→4 (coordonnées = centres de maille).
LATS = np.array([3.5, 2.5, 1.5, 0.5])
LONS = np.array([0.5, 1.5, 2.5, 3.5])
VALUES = np.array(
    [
        [10.0, 20.0, 30.0, 40.0],
        [11.0, 21.0, 31.0, 41.0],
        [12.0, 22.0, 32.0, 42.0],
        [13.0, 23.0, 33.0, 43.0],
    ]
)

LST_YAML = {
    "id": "lst_summer_mean",
    "label": "Température de surface moyenne, juin-août",
    "unit": "DEG_C",
    "source": "copernicus",
    "frequency": "A",
    "geo_levels": ["NUTS2"],
    "extraction": {
        "product": "reanalysis-era5-land",
        "variable": "skin_temperature",
        "temporal_agg": {"months": [6, 7, 8], "stat": "mean"},
        "zonal_stat": "mean",
    },
}

IMPERV_YAML = {
    "id": "imperviousness_share",
    "label": "Part des sols imperméabilisés",
    "unit": "PC",
    "source": "copernicus",
    "frequency": "A",
    "geo_levels": ["NUTS2"],
    "extraction": {
        "product": "imperviousness-density",
        "variable": "imperviousness_density",
        "temporal_agg": {"months": [], "stat": "mean"},
        "zonal_stat": "mean",
    },
}


def _square(west, south, east, north):
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


#: ZZ11 est entièrement dans le raster (4 mailles), ZZ12 déborde à l'est (2 sur 4).
FEATURES = [
    {
        "type": "Feature",
        "properties": {"NUTS_ID": "ZZ11", "CNTR_CODE": "ZZ"},
        "geometry": _square(0.0, 2.0, 2.0, 4.0),
    },
    {
        "type": "Feature",
        "properties": {"NUTS_ID": "ZZ12", "CNTR_CODE": "ZZ"},
        "geometry": _square(3.0, 0.0, 5.0, 2.0),
    },
    {
        "type": "Feature",
        "properties": {"NUTS_ID": "YY11", "CNTR_CODE": "YY"},
        "geometry": _square(0.0, 0.0, 1.0, 1.0),
    },
]


@pytest.fixture
def spec_lst():
    return registry.parse(LST_YAML)


@pytest.fixture
def spec_imperv():
    return registry.parse(IMPERV_YAML)


@pytest.fixture
def geometries(data_dir: Path) -> Path:
    """Écrit les géométries NUTS2 synthétiques là où `geo.geometry_path` les cherche."""
    from nutshell_mcp import geo

    path = geo.geometry_path("NUTS2")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": FEATURES}), encoding="utf-8"
    )
    return path


def _raster(tmp_path: Path, values=VALUES, name="synthetic.tif") -> Path:
    return cds.write_geotiff(tmp_path / name, LATS, LONS, values)


# ------------------------------------------------------------------- géométrie

def test_aire_geojson_avec_trou():
    carre = _square(0, 0, 2, 2)
    assert cds.geometry_area(carre) == pytest.approx(4.0)
    troue = {
        "type": "Polygon",
        "coordinates": [
            carre["coordinates"][0],
            _square(0.5, 0.5, 1.5, 1.5)["coordinates"][0],
        ],
    }
    assert cds.geometry_area(troue) == pytest.approx(3.0)


def test_selection_par_pays(geometries):
    assert [f["properties"]["NUTS_ID"] for f in cds.select_features("NUTS2", ["ZZ"])] == [
        "ZZ11",
        "ZZ12",
    ]
    assert len(cds.select_features("NUTS2", [])) == 3


def test_emprise_du_perimetre(geometries):
    assert cds.features_bbox(cds.select_features("NUTS2", ["ZZ"])) == (0.0, 0.0, 5.0, 4.0)


def test_geometries_absentes_message_actionnable(data_dir):
    with pytest.raises(cds.CdsError, match="sync --source geo"):
        cds.select_features("NUTS2", [])


# --------------------------------------------------------------------- raster

def test_recalage_des_longitudes_0_360():
    lons = np.array([0.0, 90.0, 180.0, 270.0])
    array = np.array([[1.0, 2.0, 3.0, 4.0]])
    recalees, recale = cds.normalize_longitudes(lons, array)
    assert list(recalees) == [-90.0, 0.0, 90.0, 180.0]
    # la colonne 270° (= -90°) passe en tête, les valeurs suivent
    assert list(recale[0]) == [4.0, 1.0, 2.0, 3.0]


def test_geotiff_decale_d_un_demi_pixel(tmp_path):
    import rasterio

    path = _raster(tmp_path)
    with rasterio.open(path) as src:
        assert src.crs.to_epsg() == 4326
        assert src.transform.c == pytest.approx(0.0)  # bord ouest, pas centre
        assert src.transform.f == pytest.approx(4.0)  # bord nord
        assert src.read(1)[0, 0] == pytest.approx(10.0)


def test_geotiff_reordonne_les_latitudes_croissantes(tmp_path):
    import rasterio

    path = cds.write_geotiff(tmp_path / "flip.tif", LATS[::-1], LONS, VALUES[::-1], )
    with rasterio.open(path) as src:
        assert src.read(1)[0, 0] == pytest.approx(10.0)


# --------------------------------------------------------- statistiques zonales

def test_moyenne_zonale_attendue(tmp_path, geometries):
    rows = cds.zonal_rows(_raster(tmp_path), FEATURES, "NUTS_ID", "mean", time_label="2023")
    by_code = {r["geo_code"]: r for r in rows}
    # ZZ11 couvre les 4 mailles du coin nord-ouest : (10+20+11+21)/4
    assert by_code["ZZ11"]["value"] == pytest.approx(15.5)
    assert by_code["ZZ11"]["quality"] == ""
    assert by_code["ZZ11"]["time"] == "2023"


def test_couverture_partielle_signalee(tmp_path):
    rows = cds.zonal_rows(_raster(tmp_path), FEATURES, "NUTS_ID", "mean")
    by_code = {r["geo_code"]: r for r in rows}
    # ZZ12 déborde du raster à l'est : 2 mailles couvertes sur 4 attendues
    assert by_code["ZZ12"]["value"] == pytest.approx(42.5)
    assert by_code["ZZ12"]["quality"] == "partial_coverage"


def test_zone_hors_emprise_ignoree(tmp_path):
    lointaine = {
        "type": "Feature",
        "properties": {"NUTS_ID": "XX11"},
        "geometry": _square(50.0, 50.0, 51.0, 51.0),
    }
    rows = cds.zonal_rows(_raster(tmp_path), [lointaine], "NUTS_ID", "mean")
    assert rows == []


def test_qualite_de_base_propagee(tmp_path):
    rows = cds.zonal_rows(
        _raster(tmp_path), FEATURES[:1], "NUTS_ID", "mean", base_quality="sampled"
    )
    assert rows[0]["quality"] == "sampled"


def test_conversion_kelvin_celsius(tmp_path, spec_lst):
    assert cds.kelvin_offset(spec_lst, "K", None) == pytest.approx(-273.15)
    assert cds.kelvin_offset(spec_lst, "", 293.0) == pytest.approx(-273.15)
    assert cds.kelvin_offset(spec_lst, "degC", 20.0) == 0.0
    assert cds.kelvin_offset(spec_lst, "", 20.0) == 0.0

    path = _raster(tmp_path, VALUES + 273.15, name="kelvin.tif")
    rows = cds.zonal_rows(
        path, FEATURES[:1], "NUTS_ID", "mean",
        offset=cds.kelvin_offset(spec_lst, "K", None),
    )
    assert rows[0]["value"] == pytest.approx(15.5)


def test_conversion_ignoree_hors_temperature(spec_imperv):
    assert cds.kelvin_offset(spec_imperv, "K", 300.0) == 0.0


# ------------------------------------------------------------- configuration

def test_annees_cibles(monkeypatch):
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    assert cds.target_years() == [2023]
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2020-2022,2024")
    assert cds.target_years() == [2020, 2021, 2022, 2024]
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "hier")
    with pytest.raises(cds.CdsError, match="NUTSHELL_CDS_YEARS"):
        cds.target_years()
    monkeypatch.delenv("NUTSHELL_CDS_YEARS")
    from datetime import UTC, datetime

    assert cds.target_years() == [datetime.now(UTC).year - 1]


def test_fournisseur_par_defaut(monkeypatch, tmp_path):
    monkeypatch.delenv("NUTSHELL_CDS_PROVIDER", raising=False)
    monkeypatch.delenv("CDSAPI_KEY", raising=False)
    monkeypatch.setenv("CDSAPI_RC", str(tmp_path / "absent.cdsapirc"))
    assert cds.default_provider() == "arco"
    (tmp_path / "present.cdsapirc").write_text("url: x\nkey: y\n")
    monkeypatch.setenv("CDSAPI_RC", str(tmp_path / "present.cdsapirc"))
    assert cds.default_provider() == "cds"


def test_routage_du_fournisseur_par_produit(monkeypatch, tmp_path, spec_lst, spec_imperv):
    """Sans consigne explicite, un produit non-ERA5 ne peut venir que d'un raster local."""
    monkeypatch.delenv("NUTSHELL_CDS_PROVIDER", raising=False)
    monkeypatch.delenv("CDSAPI_KEY", raising=False)
    monkeypatch.setenv("CDSAPI_RC", str(tmp_path / "absent.cdsapirc"))
    assert cds.provider_name_for(spec_lst) == "arco"
    assert cds.provider_name_for(spec_imperv) == "local"
    # une consigne explicite l'emporte sur la déduction
    monkeypatch.setenv("NUTSHELL_CDS_PROVIDER", "local")
    assert cds.provider_name_for(spec_lst) == "local"


def test_sync_route_imperviousness_vers_local(geometries, spec_lst, spec_imperv,
                                              stub_provider, monkeypatch, tmp_path):
    """lst_summer_mean passe par le fournisseur ERA5, imperviousness_share par local."""
    monkeypatch.setattr(
        cds, "make_provider",
        lambda name="", bbox=None: stub_provider if name != "local" else cds.LocalProvider(bbox),
    )
    monkeypatch.delenv("NUTSHELL_CDS_PROVIDER", raising=False)
    monkeypatch.delenv("CDSAPI_KEY", raising=False)
    monkeypatch.setenv("CDSAPI_RC", str(tmp_path / "absent.cdsapirc"))
    monkeypatch.setenv("NUTSHELL_RASTER_DIR", str(tmp_path / "rasters"))
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")

    report = cds.sync([spec_lst, spec_imperv], full=False)
    assert stub_provider.calls == [("lst_summer_mean", 2023)]
    assert report.updated_items and "lst_summer_mean" in report.updated_items[0]
    # le raster CLMS n'est pas déposé : erreur actionnable, sans bloquer le lot
    failed_id, reason = report.failed_items[0]
    assert failed_id == "imperviousness_share"
    assert "land.copernicus.eu" in reason


def test_fournisseur_inconnu():
    with pytest.raises(cds.CdsError, match="NUTSHELL_CDS_PROVIDER"):
        cds.make_provider("météo-france")


def test_message_sans_cle_cds(monkeypatch, tmp_path):
    monkeypatch.delenv("CDSAPI_KEY", raising=False)
    monkeypatch.setenv("CDSAPI_RC", str(tmp_path / "absent.cdsapirc"))
    with pytest.raises(cds.CdsError, match="how-to-api"):
        cds.CdsProvider().client()


# ------------------------------------------------------------ fournisseur local

def test_local_lit_le_raster_depose(tmp_path, monkeypatch, spec_imperv):
    root = tmp_path / "rasters"
    monkeypatch.setenv("NUTSHELL_RASTER_DIR", str(root))
    (root / "imperviousness_share").mkdir(parents=True)
    cds.write_geotiff(root / "imperviousness_share" / "2018.tif", LATS, LONS, VALUES)

    raster = cds.LocalProvider().fetch(spec_imperv, 2018)
    assert raster.path.name == "2018.tif"
    assert raster.ephemeral is False  # jamais purgé : c'est le fichier de l'utilisateur
    assert raster.source_date.startswith("raster local ")
    assert raster.sample_max == pytest.approx(43.0)


def test_local_erreur_actionnable(tmp_path, monkeypatch, spec_imperv):
    monkeypatch.setenv("NUTSHELL_RASTER_DIR", str(tmp_path / "rasters"))
    with pytest.raises(cds.CdsError) as err:
        cds.LocalProvider().fetch(spec_imperv, 2018)
    message = str(err.value)
    assert "imperviousness_share/2018.tif" in message.replace("\\", "/")
    assert "land.copernicus.eu" in message
    assert "NUTSHELL_RASTER_DIR" in message


def test_local_refuse_un_crs_non_4326(tmp_path, monkeypatch, spec_imperv):
    import rasterio
    from rasterio.transform import from_origin

    root = tmp_path / "rasters" / "imperviousness_share"
    root.mkdir(parents=True)
    monkeypatch.setenv("NUTSHELL_RASTER_DIR", str(tmp_path / "rasters"))
    with rasterio.open(
        root / "2018.tif", "w", driver="GTiff", height=4, width=4, count=1,
        dtype="float32", crs="EPSG:3035", transform=from_origin(0, 4, 1, 1),
    ) as dst:
        dst.write(VALUES.astype("float32"), 1)
    with pytest.raises(cds.CdsError, match="gdalwarp"):
        cds.LocalProvider().fetch(spec_imperv, 2018)


# -------------------------------------------------------------- fournisseur cds

class _FakeReply(dict):
    pass


class _FakeResult:
    """Résultat CDS simulé : suit l'état, écrit un NetCDF minimal au download."""

    created: ClassVar[list] = []

    def __init__(self, client, reply):
        self.client = client
        self.reply = _FakeReply(reply)
        self.reply.setdefault("state", "completed")
        self.downloads: list[str] = []
        _FakeResult.created.append(self)

    def update(self):
        self.reply["state"] = "completed"

    def download(self, target):
        self.downloads.append(target)
        _write_netcdf(Path(target))


def _write_netcdf(path: Path) -> None:
    import pandas as pd
    import xarray as xr

    times = pd.to_datetime(["2023-06-01", "2023-07-01", "2023-08-01"])
    data = np.stack([VALUES + 273.15 + i for i in range(3)])
    dataset = xr.Dataset(
        {"skt": (("time", "latitude", "longitude"), data.astype("float32"))},
        coords={"time": times, "latitude": LATS, "longitude": LONS},
    )
    dataset["skt"].attrs["units"] = "K"
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_netcdf(path)


class _FakeClient:
    def __init__(self):
        self.requests: list[tuple[str, dict]] = []
        self.counter = 0

    def retrieve(self, name, request, target=None):
        self.counter += 1
        self.requests.append((name, request))
        return _FakeResult(self, {"request_id": f"req-{self.counter}", "state": "accepted"})


@pytest.fixture
def fake_cds(monkeypatch):
    import cdsapi.api

    _FakeResult.created = []
    monkeypatch.setattr(cdsapi.api, "Result", _FakeResult)
    client = _FakeClient()
    return client


def test_requete_cds_construite(spec_lst):
    provider = cds.CdsProvider(bbox=(5.6, 49.3, 6.7, 50.3))
    request = provider.build_request(spec_lst, 2023)
    assert provider.dataset_name == "reanalysis-era5-land-monthly-means"
    assert request["product_type"] == ["monthly_averaged_reanalysis"]
    assert request["variable"] == ["skin_temperature"]
    assert request["year"] == ["2023"]
    assert request["month"] == ["06", "07", "08"]
    # CDS attend [Nord, Ouest, Sud, Est], élargi d'un dixième de degré
    assert request["area"] == [50.4, 5.5, 49.2, 6.8]


def test_soumission_du_lot_et_persistance_des_request_ids(data_dir, spec_lst, fake_cds):
    provider = cds.CdsProvider()
    provider._client = fake_cds
    provider.prepare([(spec_lst, 2022), (spec_lst, 2023)])
    assert len(fake_cds.requests) == 2
    assert store.get_sync_state("copernicus", "lst_summer_mean:2022:request_id") == "req-1"
    assert store.get_sync_state("copernicus", "lst_summer_mean:2023:request_id") == "req-2"

    # reprise : rien n'est re-soumis pour une requête déjà en file
    provider.prepare([(spec_lst, 2022), (spec_lst, 2023)])
    assert len(fake_cds.requests) == 2


def test_collecte_reprend_sur_le_request_id(data_dir, spec_lst, fake_cds):
    store.set_sync_state("copernicus", "lst_summer_mean:2023:request_id", "req-abc")
    provider = cds.CdsProvider()
    provider._client = fake_cds
    raster = provider.fetch(spec_lst, 2023)

    assert fake_cds.requests == []  # aucune re-soumission
    assert _FakeResult.created[-1].reply["request_id"] == "req-abc"
    assert raster.units == "K"
    assert raster.source_date.startswith("reanalysis-era5-land-monthly-means ")
    # l'état est purgé une fois le fichier récupéré
    assert store.get_sync_state("copernicus", "lst_summer_mean:2023:request_id") is None

    rows = cds.zonal_rows(
        raster.path, FEATURES[:1], "NUTS_ID", "mean",
        offset=cds.kelvin_offset(spec_lst, raster.units, raster.sample_max),
    )
    # moyenne des trois mois (offsets 0/1/2) sur les 4 mailles du coin : 15.5 + 1
    assert rows[0]["value"] == pytest.approx(16.5)


def test_requete_cds_en_echec(data_dir, spec_lst, fake_cds, monkeypatch):
    provider = cds.CdsProvider()
    provider._client = fake_cds
    result = _FakeResult(fake_cds, {"request_id": "x", "state": "failed"})
    monkeypatch.setattr(result, "update", lambda: None)
    with pytest.raises(cds.CdsError, match="échec"):
        provider._wait(result)


# ------------------------------------------------------------ échantillonnage

def test_pas_de_temps_echantillonnes(monkeypatch):
    monkeypatch.setenv("NUTSHELL_ARCO_SAMPLES_PER_MONTH", "4")
    stamps = cds.ArcoProvider().timestamps(2023, [6, 7, 8])
    assert len(stamps) == 12
    assert stamps[0] == "2023-06-04T00:00:00"
    # les quatre heures synoptiques sont représentées : pas de biais diurne
    assert {s[11:13] for s in stamps} == {"00", "06", "12", "18"}
    monkeypatch.setenv("NUTSHELL_ARCO_SAMPLES_PER_MONTH", "1")
    assert len(cds.ArcoProvider().timestamps(2023, [6, 7, 8])) == 3


# ---------------------------------------------------------------------- sync

class _StubProvider(cds.RasterProvider):
    """Fournisseur de test : renvoie le raster synthétique, compte ses appels."""

    name = "stub"

    def __init__(self, tmp_path: Path, bbox=None):
        super().__init__(bbox)
        self.tmp_path = tmp_path
        self.calls: list[tuple[str, int]] = []

    def fetch(self, spec, year):
        self.calls.append((spec.id, year))
        path = cds.write_geotiff(
            self.tmp_path / f"{spec.id}_{year}.tif", LATS, LONS, VALUES + 273.15
        )
        return cds.Raster(path=path, source_date=f"stub {year}", units="K", quality="sampled")


@pytest.fixture
def stub_provider(tmp_path, monkeypatch):
    provider = _StubProvider(tmp_path / "stub")
    monkeypatch.setattr(cds, "make_provider", lambda name="", bbox=None: provider)
    return provider


def test_sync_ecrit_la_partition(geometries, spec_lst, stub_provider, monkeypatch):
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")
    report = cds.sync([spec_lst], full=False)

    assert report.ok, report.render()
    assert stub_provider.calls == [("lst_summer_mean", 2023)]
    info = indicators.materialized_info("lst_summer_mean")
    assert info["rows"] == 2
    assert info["source"] == "copernicus"
    assert info["source_date"] == "stub 2023"

    columns, rows, provenance = indicators.query(["lst_summer_mean"], ["ZZ11", "ZZ12"])
    assert columns == ["geo_code", "time", "lst_summer_mean"]
    assert rows == [
        ["ZZ11", "2023", "15.5 [sampled]"],
        ["ZZ12", "2023", "42.5 [partial_coverage]"],
    ]
    assert provenance["lst_summer_mean"]["source"] == "copernicus"
    assert store.get_sync_state("copernicus", "lst_summer_mean:last_year") == "2023"


def test_sync_saute_une_annee_deja_materialisee(geometries, spec_lst, stub_provider,
                                                monkeypatch):
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")
    cds.sync([spec_lst], full=False)
    stub_provider.calls.clear()

    report = cds.sync([spec_lst], full=False)
    assert stub_provider.calls == []
    assert report.unchanged_items == ["lst_summer_mean"]

    # --full ignore le signal de fraîcheur local
    report = cds.sync([spec_lst], full=True)
    assert stub_provider.calls == [("lst_summer_mean", 2023)]
    assert report.updated_items


def test_sync_ajoute_une_annee_sans_perdre_la_precedente(geometries, spec_lst,
                                                         stub_provider, monkeypatch):
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2022")
    cds.sync([spec_lst], full=False)
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2022,2023")
    cds.sync([spec_lst], full=False)

    assert stub_provider.calls == [("lst_summer_mean", 2022), ("lst_summer_mean", 2023)]
    info = indicators.materialized_info("lst_summer_mean")
    assert (info["time_min"], info["time_max"]) == ("2022", "2023")
    assert info["rows"] == 4


def test_sync_purge_le_raster_intermediaire(geometries, spec_lst, stub_provider,
                                            monkeypatch):
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")
    cds.sync([spec_lst], full=False)
    assert not (stub_provider.tmp_path / "lst_summer_mean_2023.tif").exists()


def test_sync_perimetre_vide(geometries, spec_lst, stub_provider, monkeypatch):
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "XX")
    report = cds.sync([spec_lst], full=False)
    assert not report.ok
    assert "NUTSHELL_CDS_COUNTRIES" in report.failed_items[0][1]


def test_sync_echec_par_indicateur_non_bloquant(geometries, spec_lst, spec_imperv,
                                                monkeypatch, tmp_path):
    class _Flaky(_StubProvider):
        def fetch(self, spec, year):
            if spec.id == "imperviousness_share":
                raise cds.CdsError("raster absent")
            return super().fetch(spec, year)

    provider = _Flaky(tmp_path / "flaky")
    monkeypatch.setattr(cds, "make_provider", lambda name="", bbox=None: provider)
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")

    report = cds.sync([spec_lst, spec_imperv], full=False)
    assert not report.ok
    assert report.updated_items and "lst_summer_mean" in report.updated_items[0]
    assert report.failed_items == [("imperviousness_share", "raster absent")]


def test_sync_via_le_fournisseur_local(geometries, spec_imperv, monkeypatch, tmp_path):
    root = tmp_path / "rasters" / "imperviousness_share"
    root.mkdir(parents=True)
    cds.write_geotiff(root / "2018.tif", LATS, LONS, VALUES)
    monkeypatch.setenv("NUTSHELL_RASTER_DIR", str(tmp_path / "rasters"))
    monkeypatch.setenv("NUTSHELL_CDS_PROVIDER", "local")
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2018")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")

    report = cds.sync([spec_imperv], full=False)
    assert report.ok, report.render()
    _, rows, _ = indicators.query(["imperviousness_share"], ["ZZ11"])
    assert rows == [["ZZ11", "2018", "15.5"]]
    # le raster de l'utilisateur n'est jamais supprimé
    assert (root / "2018.tif").exists()


def test_sync_offline_refuse_arco(geometries, spec_lst, monkeypatch):
    monkeypatch.setenv("NUTSHELL_OFFLINE", "1")
    monkeypatch.setenv("NUTSHELL_CDS_PROVIDER", "arco")
    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")
    report = cds.sync([spec_lst], full=False)
    assert not report.ok
    assert "offline" in report.failed_items[0][1]


def test_pipeline_branche_sur_sync_py(geometries, spec_lst, stub_provider, monkeypatch):
    """`sync.sync_pipeline` doit trouver le module et lui déléguer le lot."""
    from nutshell_mcp import sync as sync_module

    monkeypatch.setenv("NUTSHELL_CDS_YEARS", "2023")
    monkeypatch.setenv("NUTSHELL_CDS_COUNTRIES", "ZZ")
    report = sync_module.sync_pipeline("copernicus", [spec_lst], full=False)
    assert report.source == "copernicus"
    assert report.ok, report.render()


# ------------------------------------------------------------- test réseau réel

@pytest.mark.network
def test_arco_reel_deux_pas_de_temps(data_dir, geometries, spec_lst, monkeypatch):
    """Deux pas de temps réels sur le store public ARCO (aucune clé requise)."""
    monkeypatch.setenv("NUTSHELL_ARCO_SAMPLES_PER_MONTH", "1")
    provider = cds.ArcoProvider(bbox=(5.6, 49.3, 6.7, 50.3))
    spec = registry.parse({**LST_YAML, "extraction": {
        **LST_YAML["extraction"],
        "temporal_agg": {"months": [7, 8], "stat": "mean"},
    }})
    raster = provider.fetch(spec, 2023)
    try:
        assert raster.quality == "sampled"
        assert raster.units == "K"
        assert raster.source_date.startswith("ARCO-ERA5 ")
        assert 250.0 < (raster.sample_max or 0) < 340.0
        assert raster.path.exists()
    finally:
        provider.close()
        raster.path.unlink(missing_ok=True)
    assert config.work_dir().exists()


def test_target_bbox(monkeypatch):
    from nutshell_mcp import ingest_cds as cds

    monkeypatch.delenv("NUTSHELL_CDS_BBOX", raising=False)
    assert cds.target_bbox() is None
    monkeypatch.setenv("NUTSHELL_CDS_BBOX", "-12,34,35,72")
    assert cds.target_bbox() == (-12.0, 34.0, 35.0, 72.0)
    monkeypatch.setenv("NUTSHELL_CDS_BBOX", "35,34,-12,72")
    with pytest.raises(cds.CdsError, match="NUTSHELL_CDS_BBOX invalide"):
        cds.target_bbox()


def test_intersects_exclut_les_regions_ultraperipheriques():
    from nutshell_mcp import ingest_cds as cds

    europe = (-12.0, 34.0, 35.0, 72.0)
    guadeloupe = cds.features_bbox([{"type": "Feature", "geometry": {
        "type": "Polygon", "coordinates": [[[-61.8, 15.9], [-61.0, 15.9], [-61.0, 16.5],
                                           [-61.8, 16.5], [-61.8, 15.9]]]}}])
    paris = cds.features_bbox([{"type": "Feature", "geometry": {
        "type": "Polygon", "coordinates": [[[2.2, 48.8], [2.5, 48.8], [2.5, 48.9],
                                           [2.2, 48.9], [2.2, 48.8]]]}}])
    assert not cds._intersects(guadeloupe, europe)
    assert cds._intersects(paris, europe)
