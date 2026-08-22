"""Pipeline Copernicus (§7.2) : rasters → statistiques zonales → grain canonique.

Séquence, identique quelle que soit la provenance du raster :

1. **acquisition** d'un raster par indicateur et par année, déléguée à un
   *fournisseur* (§ « Fournisseurs » ci-dessous) qui applique déjà l'agrégation
   temporelle déclarée par ``extraction.temporal_agg`` ;
2. **recalage** : longitudes ERA5 0-360 ramenées en -180/180, GeoTIFF EPSG:4326
   temporaire écrit dans ``work/`` (patron rasterio, origine décalée d'un
   demi-pixel — les coordonnées ERA5 désignent le *centre* des mailles) ;
3. **statistiques zonales** ``exactextract`` contre les géométries GISCO de
   chaque niveau de ``spec.geo_levels``, pondérées par la fraction de maille
   réellement couverte ;
4. **écriture** de la partition par ``indicators.write_partition``, puis purge
   du raster brut (§7.2 : le poste le plus lourd est supprimable).

Fournisseurs de rasters
-----------------------
Un fournisseur expose ``fetch(spec, year) -> Raster``. ``NUTSHELL_CDS_PROVIDER``
impose le même pour tout le lot ; sans consigne, le fournisseur est déduit du
produit déclaré au registre : une réanalyse ERA5 (``reanalysis-*``) va vers
``cds`` si ``~/.cdsapirc`` existe et ``arco`` sinon, tout autre produit — les
couches CLMS notamment — vers ``local``, seule voie possible pour eux.

``cds``
    Voie officielle : ``cdsapi`` sur ``reanalysis-era5-land-monthly-means``
    (``product_type=monthly_averaged_reanalysis``). Les files d'attente CDS
    durant des heures, **toutes les requêtes du lot sont soumises d'abord**
    (``prepare``), les identifiants de requête sont persistés dans ``sync_state``
    et la collecte reprend là où elle s'était arrêtée après une interruption.
``arco``
    Repli **sans clé** : lecture anonyme du zarr public ARCO-ERA5 sur GCS
    (``gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3``).
    Le store est chunké ``(1, 721, 1440)`` : un chunk = une grille globale pour
    **un** pas de temps horaire, donc un sous-ensemble spatial ne réduit pas le
    nombre de requêtes réseau (3 à 9 s par pas de temps). Une moyenne JJA
    horaire exacte (2208 pas) prendrait des heures : le fournisseur
    **échantillonne** ``NUTSHELL_ARCO_SAMPLES_PER_MONTH`` pas de temps par mois
    (défaut 4, aux heures synoptiques 00/06/12/18 sur des jours répartis) et
    marque le résultat ``quality = "sampled"`` — c'est une estimation, pas la
    moyenne climatologique exacte.
``local``
    Raster déposé à la main sous ``NUTSHELL_RASTER_DIR/{indicateur}/{année}.tif``
    (GeoTIFF EPSG:4326). C'est la voie prévue pour ``imperviousness_share`` :
    le Copernicus Land Monitoring Service exige une authentification que le
    pipeline ne peut pas porter ; l'utilisateur télécharge le raster, le
    pipeline fait le reste.

Variables d'environnement
-------------------------
``NUTSHELL_CDS_PROVIDER``          ``cds`` | ``arco`` | ``local``
``NUTSHELL_CDS_YEARS``             ``2023`` | ``2020,2023`` | ``2020-2023``
                                   (défaut : dernière année complète)
``NUTSHELL_CDS_COUNTRIES``         ``LU,BE,FR`` — restreint le périmètre spatial
                                   (défaut : tout le référentiel, coûteux)
``NUTSHELL_ARCO_SAMPLES_PER_MONTH`` pas de temps échantillonnés par mois (4)
``NUTSHELL_ARCO_STORE``            URL zarr alternative
``NUTSHELL_RASTER_DIR``            racine des rasters du fournisseur ``local``
``NUTSHELL_CDS_KEEP_RASTERS=1``    ne purge pas les rasters intermédiaires
``NUTSHELL_CDS_TIMEOUT``           attente maximale d'une requête CDS (s, 3600)
``NUTSHELL_CDS_POLL``              intervalle de scrutation CDS (s, 30)

Signal de fraîcheur (P3)
------------------------
``sync_state("copernicus", "{id}:last_year")`` porte la dernière année
matérialisée : une année déjà présente n'est pas recalculée (sauf ``--full``).
Les années déjà écrites sont relues et fusionnées avec les nouvelles, la
partition d'un indicateur restant réécrite d'un bloc.
"""

from __future__ import annotations

import calendar
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import config, geo, indicators, store
from .sync import SyncReport

#: Store ARCO-ERA5 public par défaut (accès anonyme, couverture 1940 → présent).
ARCO_STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
#: Dataset CDS retenu : nettement plus léger que la variante horaire (§B1 du spike).
CDS_DATASET = "reanalysis-era5-land-monthly-means"
CDS_HOWTO = "https://cds.climate.copernicus.eu/how-to-api"
CLMS_URL = "https://land.copernicus.eu/en/products/high-resolution-layer-imperviousness"

#: Heures synoptiques utilisées par l'échantillonnage ARCO (cycle diurne équilibré).
SYNOPTIC_HOURS = (0, 6, 12, 18)
#: Statistiques zonales invariantes par transformation affine (K → °C applicable après coup).
AFFINE_STATS = frozenset({"mean", "min", "max", "median"})
#: En deçà de cette fraction de zone couverte, la valeur est marquée `partial_coverage`.
COVERAGE_TOLERANCE = 0.999


class CdsError(Exception):
    """Erreur actionnable du pipeline Copernicus (message destiné à l'utilisateur)."""


# ------------------------------------------------------------------- imports

def _require(module: str, package: str = "copernicus"):
    """Import paresseux d'une dépendance d'extra, avec message actionnable."""
    try:
        return __import__(module, fromlist=["_"])
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        raise CdsError(
            f"Dépendance '{module}' absente ({exc}). "
            f'Installer l\'extra : pip install -e ".[{package}]"'
        ) from exc


# ---------------------------------------------------------- configuration env

def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def target_years() -> list[int]:
    """Années à matérialiser (``NUTSHELL_CDS_YEARS``, défaut : dernière complète)."""
    raw = _env("NUTSHELL_CDS_YEARS")
    if not raw:
        return [datetime.now(UTC).year - 1]
    years: set[int] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            try:
                years.update(range(int(start), int(end) + 1))
            except ValueError as exc:
                raise CdsError(
                    f"NUTSHELL_CDS_YEARS='{raw}' illisible : '{chunk}' n'est pas "
                    f"une plage d'années (format attendu : 2020-2023)."
                ) from exc
        else:
            try:
                years.add(int(chunk))
            except ValueError as exc:
                raise CdsError(
                    f"NUTSHELL_CDS_YEARS='{raw}' illisible : '{chunk}' n'est pas "
                    f"une année (format attendu : 2023 ou 2020-2023)."
                ) from exc
    return sorted(years)


def target_countries() -> list[str]:
    """Codes pays du périmètre (``NUTSHELL_CDS_COUNTRIES``), vide = tout le référentiel."""
    return [c.strip().upper() for c in _env("NUTSHELL_CDS_COUNTRIES").split(",") if c.strip()]


def raster_dir() -> Path:
    """Racine des rasters déposés manuellement (fournisseur ``local``)."""
    raw = _env("NUTSHELL_RASTER_DIR")
    return Path(raw).expanduser().resolve() if raw else config.data_dir() / "rasters"


def cdsapirc_path() -> Path:
    return Path(os.environ.get("CDSAPI_RC") or (Path.home() / ".cdsapirc"))


def default_provider() -> str:
    """``cds`` si une clé est configurée, ``arco`` sinon."""
    if cdsapirc_path().exists() or os.environ.get("CDSAPI_KEY"):
        return "cds"
    return "arco"


# ------------------------------------------------------------------ géométrie

def _open_features(level: str) -> list[dict]:
    path = geo.geometry_path(level)
    if not path.exists():
        raise CdsError(
            f"Géométries du niveau {level} absentes ({path}).\n"
            f"Lancer : python -m nutshell_mcp.sync --source geo"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("features") or []


def select_features(level: str, countries: list[str]) -> list[dict]:
    """Features GeoJSON d'un niveau, restreintes au périmètre pays.

    Le filtre porte sur ``CNTR_CODE`` quand la propriété existe, sinon sur le
    préfixe du code de zone (``LU000`` → ``LU``).
    """
    code_property = geo.geometry_code_property(level)
    out = []
    for feature in _open_features(level):
        props = feature.get("properties") or {}
        code = props.get(code_property)
        if not code or not feature.get("geometry"):
            continue
        if countries:
            country = props.get("CNTR_CODE") or code[:2]
            if country.upper() not in countries:
                continue
        out.append(feature)
    return out


def _ring_area(ring: list) -> float:
    """Aire planaire (degrés²) d'un anneau GeoJSON, formule des lacets."""
    if len(ring) < 3:
        return 0.0
    pts = list(ring)
    if pts[0][:2] != pts[-1][:2]:
        pts.append(pts[0])
    total = 0.0
    for (x1, y1), (x2, y2) in zip(
        [(p[0], p[1]) for p in pts[:-1]], [(p[0], p[1]) for p in pts[1:]], strict=True
    ):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def geometry_area(geometry: dict) -> float:
    """Aire d'une géométrie GeoJSON en degrés², trous déduits.

    Sert de dénominateur au contrôle de couverture : ``exactextract`` renvoie la
    somme des fractions de mailles *valides* couvertes, à comparer au nombre de
    mailles qu'occuperait la zone entière.
    """
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        polygons = [coords]
    elif kind == "MultiPolygon":
        polygons = coords
    else:
        return 0.0
    total = 0.0
    for polygon in polygons:
        if not polygon:
            continue
        total += _ring_area(polygon[0])
        for hole in polygon[1:]:
            total -= _ring_area(hole)
    return max(total, 0.0)


def features_bbox(features: list[dict]) -> tuple[float, float, float, float]:
    """Emprise (ouest, sud, est, nord) d'une liste de features, en degrés."""
    west = south = float("inf")
    east = north = float("-inf")

    def walk(node):
        nonlocal west, south, east, north
        if isinstance(node, (list, tuple)):
            if node and isinstance(node[0], (int, float)):
                lon, lat = float(node[0]), float(node[1])
                west, east = min(west, lon), max(east, lon)
                south, north = min(south, lat), max(north, lat)
            else:
                for child in node:
                    walk(child)

    for feature in features:
        walk((feature.get("geometry") or {}).get("coordinates"))
    if west == float("inf"):
        raise CdsError("Périmètre vide : aucune géométrie sélectionnée.")
    return west, south, east, north


# --------------------------------------------------------------------- raster

@dataclass
class Raster:
    """Raster agrégé prêt pour la statistique zonale."""

    path: Path
    #: Date / version du produit à la source, écrite telle quelle en `source_date`.
    source_date: str
    #: Unité déclarée par la source (``K`` pour ERA5), vide si inconnue.
    units: str = ""
    #: Qualité de base propagée aux lignes (``sampled`` pour ARCO).
    quality: str = ""
    #: Valeur maximale observée, utilisée pour deviner une échelle en kelvins.
    sample_max: float | None = None
    #: Faux pour un fichier fourni par l'utilisateur : ne jamais le purger.
    ephemeral: bool = True
    notes: list[str] = field(default_factory=list)


def normalize_longitudes(lons, array):
    """Ramène des longitudes 0-360 en -180/180 et réordonne le raster.

    ERA5 publie ses grilles en 0-360 : sans ce recalage, l'Europe de l'Ouest
    (longitudes négatives) tombe à l'autre bout du raster.
    """
    numpy = _require("numpy")
    lons = numpy.asarray(lons, dtype="float64")
    shifted = numpy.where(lons > 180.0, lons - 360.0, lons)
    order = numpy.argsort(shifted, kind="stable")
    return shifted[order], numpy.asarray(array)[..., order]


def _crop(lats, lons, array, bbox, margin: float):
    """Restreint le raster à l'emprise demandée, avec une marge d'un pixel."""
    numpy = _require("numpy")
    west, south, east, north = bbox
    lon_mask = (lons >= west - margin) & (lons <= east + margin)
    lat_mask = (lats >= south - margin) & (lats <= north + margin)
    if not lon_mask.any() or not lat_mask.any():
        return lats, lons, array
    return (
        lats[lat_mask],
        lons[lon_mask],
        numpy.asarray(array)[numpy.ix_(lat_mask, lon_mask)],
    )


def write_geotiff(path: Path, lats, lons, array) -> Path:
    """Écrit un GeoTIFF EPSG:4326 depuis une grille régulière centrée sur les mailles.

    Les coordonnées ERA5 désignent le centre des mailles ; l'origine du GeoTIFF
    est donc décalée d'un demi-pixel vers le nord-ouest.
    """
    numpy = _require("numpy")
    rasterio = _require("rasterio")
    from rasterio.transform import from_origin

    lats = numpy.asarray(lats, dtype="float64")
    lons = numpy.asarray(lons, dtype="float64")
    data = numpy.asarray(array, dtype="float32")
    if lats.size < 2 or lons.size < 2:
        raise CdsError(
            "Raster trop petit pour une statistique zonale "
            f"({lats.size}×{lons.size} mailles) : élargir le périmètre."
        )
    res_lat = abs(float(lats[1] - lats[0]))
    res_lon = abs(float(lons[1] - lons[0]))
    if lats[0] < lats[-1]:  # GeoTIFF nord-up : latitudes décroissantes
        lats = lats[::-1]
        data = data[::-1, :]
    transform = from_origin(
        float(lons.min()) - res_lon / 2, float(lats.max()) + res_lat / 2, res_lon, res_lat
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
        count=1, dtype="float32", crs="EPSG:4326", transform=transform,
        nodata=float("nan"), compress="deflate",
    ) as dst:
        dst.write(data, 1)
    return path


# ------------------------------------------------------------- fournisseurs

class RasterProvider:
    """Interface commune des fournisseurs de rasters.

    ``fetch(spec, year)`` renvoie un :class:`Raster` déjà agrégé temporellement
    selon ``spec.extraction.temporal_agg``. ``prepare`` permet à un fournisseur
    asynchrone (CDS) de soumettre tout le lot avant la première collecte.
    """

    name = "abstract"

    def __init__(self, bbox: tuple[float, float, float, float] | None = None) -> None:
        self.bbox = bbox

    def prepare(self, jobs: list[tuple[Any, int]]) -> None:
        """Soumet à l'avance les travaux du lot (par défaut : rien à faire)."""

    def fetch(self, spec: Any, year: int) -> Raster:
        raise NotImplementedError

    def close(self) -> None:
        """Libère les ressources ouvertes (connexions, stores)."""


def _aggregate(dataset_array, months: list[int], stat: str):
    """Applique l'agrégation temporelle déclarée par le registre."""
    if "time" not in dataset_array.dims and "valid_time" not in dataset_array.dims:
        return dataset_array
    dim = "time" if "time" in dataset_array.dims else "valid_time"
    if months:
        selector = dataset_array[dim].dt.month.isin(months)
        if bool(selector.any()):
            dataset_array = dataset_array.isel({dim: selector})
    if stat not in ("mean", "min", "max", "sum"):
        raise CdsError(f"Statistique temporelle '{stat}' non supportée.")
    return getattr(dataset_array, stat)(dim=dim, skipna=True)


class ArcoProvider(RasterProvider):
    """ARCO-ERA5 sur Google Cloud Storage, accès anonyme, échantillonné.

    Le store est chunké par pas de temps global : chaque pas de temps demandé
    coûte une requête HTTP d'une grille mondiale entière, quel que soit le
    sous-ensemble spatial. On échantillonne donc quelques pas de temps par mois
    plutôt que de lire les 2208 heures d'un été — le résultat est marqué
    ``sampled``.
    """

    name = "arco"

    def __init__(self, bbox=None) -> None:
        super().__init__(bbox)
        self._dataset = None
        self.samples_per_month = max(1, int(_env("NUTSHELL_ARCO_SAMPLES_PER_MONTH", "4")))
        self.store = _env("NUTSHELL_ARCO_STORE", ARCO_STORE)

    def _open(self):
        if self._dataset is None:
            if config.offline():
                raise CdsError(
                    "Mode offline actif : le fournisseur 'arco' a besoin du réseau. "
                    "Désactiver NUTSHELL_OFFLINE pour synchroniser."
                )
            xarray = _require("xarray")
            _require("gcsfs")
            self._dataset = xarray.open_zarr(
                self.store, chunks=None, storage_options={"token": "anon"}
            )
        return self._dataset

    def timestamps(self, year: int, months: list[int]) -> list[str]:
        """Pas de temps échantillonnés : jours répartis, heures synoptiques tournantes."""
        months = months or list(range(1, 13))
        out = []
        for month in months:
            days_in_month = calendar.monthrange(year, month)[1]
            for i in range(self.samples_per_month):
                day = round((i + 0.5) * days_in_month / self.samples_per_month)
                day = min(max(day, 1), days_in_month)
                hour = SYNOPTIC_HOURS[i % len(SYNOPTIC_HOURS)]
                out.append(f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00")
        return sorted(set(out))

    def fetch(self, spec: Any, year: int) -> Raster:
        dataset = self._open()
        variable = spec.extraction.variable
        if variable not in dataset.data_vars:
            available = ", ".join(sorted(dataset.data_vars)[:12])
            raise CdsError(
                f"Variable '{variable}' absente du store ARCO. Disponibles (extrait) : "
                f"{available}…"
            )
        stamps = self.timestamps(year, spec.extraction.temporal_agg.months)
        stop = str(dataset.attrs.get("valid_time_stop") or "")
        if stop and stamps and stamps[-1][:10] > stop:
            raise CdsError(
                f"Année {year} au-delà de la couverture du store ARCO "
                f"(données valides jusqu'au {stop})."
            )
        sub = dataset[variable].sel(time=stamps)
        aggregated = _aggregate(sub, [], spec.extraction.temporal_agg.stat).load()

        lats = aggregated["latitude"].values
        lons, values = normalize_longitudes(aggregated["longitude"].values, aggregated.values)
        if self.bbox:
            resolution = abs(float(lons[1] - lons[0])) if lons.size > 1 else 0.25
            lats, lons, values = _crop(lats, lons, values, self.bbox, resolution)
        target = config.work_dir() / "copernicus" / f"{spec.id}_{year}_arco.tif"
        write_geotiff(target, lats, lons, values)
        numpy = _require("numpy")
        source_date = str(
            dataset.attrs.get("last_updated") or dataset.attrs.get("valid_time_stop") or year
        )[:10]
        return Raster(
            path=target,
            source_date=f"ARCO-ERA5 {source_date}",
            units=str(dataset[variable].attrs.get("units") or ""),
            quality="sampled",
            sample_max=float(numpy.nanmax(values)) if values.size else None,
            notes=[f"{len(stamps)} pas de temps échantillonnés"],
        )

    def close(self) -> None:
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None


class CdsProvider(RasterProvider):
    """Voie officielle ``cdsapi`` sur ``reanalysis-era5-land-monthly-means``.

    Les requêtes du lot sont soumises d'un bloc (``prepare``), leurs identifiants
    persistés dans ``sync_state`` — une interruption entre la soumission et la
    collecte n'oblige pas à re-soumettre (§7.2).
    """

    name = "cds"
    dataset_name = CDS_DATASET

    def __init__(self, bbox=None) -> None:
        super().__init__(bbox)
        self._client = None
        self.timeout = float(_env("NUTSHELL_CDS_TIMEOUT", "3600"))
        self.poll = float(_env("NUTSHELL_CDS_POLL", "30"))

    # -- clé et client

    def client(self):
        if self._client is None:
            if not cdsapirc_path().exists() and not os.environ.get("CDSAPI_KEY"):
                raise CdsError(
                    f"Aucune clé CDS : {cdsapirc_path()} est absent.\n"
                    f"Créer un compte puis déposer le jeton personnel en suivant "
                    f"{CDS_HOWTO}\n"
                    f"Sans clé, utiliser le repli anonyme : "
                    f"NUTSHELL_CDS_PROVIDER=arco"
                )
            cdsapi = _require("cdsapi")
            self._client = cdsapi.Client(wait_until_complete=False)
        return self._client

    # -- requête

    def build_request(self, spec: Any, year: int) -> dict:
        """Requête CDS d'un indicateur pour une année (moyennes mensuelles).

        ``temporal_agg.stat`` s'applique aux **moyennes mensuelles**, pas aux pas
        horaires : c'est bien la définition d'une « moyenne estivale » pour
        ``stat: mean``, mais le maximum de trois moyennes mensuelles n'est pas le
        maximum horaire de l'été. Un indicateur en ``stat: max`` doit donc viser
        le produit horaire, pas ce dataset.
        """
        aggregation = spec.extraction.temporal_agg
        months = aggregation.months or list(range(1, 13))
        request = {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": [spec.extraction.variable],
            "year": [str(year)],
            "month": [f"{m:02d}" for m in months],
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
        }
        if self.bbox:
            west, south, east, north = self.bbox
            # CDS attend [Nord, Ouest, Sud, Est], arrondi au dixième vers l'extérieur.
            request["area"] = [
                round(north + 0.1, 1), round(west - 0.1, 1),
                round(south - 0.1, 1), round(east + 0.1, 1),
            ]
        return request

    def _state_key(self, spec: Any, year: int) -> str:
        return f"{spec.id}:{year}:request_id"

    def prepare(self, jobs: list[tuple[Any, int]]) -> None:
        """Soumet toutes les requêtes du lot, en réutilisant celles déjà en file."""
        for spec, year in jobs:
            key = self._state_key(spec, year)
            if store.get_sync_state("copernicus", key):
                continue
            result = self.client().retrieve(self.dataset_name, self.build_request(spec, year))
            request_id = (getattr(result, "reply", None) or {}).get("request_id")
            if request_id:
                store.set_sync_state("copernicus", key, str(request_id))

    def _result(self, spec: Any, year: int):
        """Résultat CDS en cours, repris depuis l'identifiant persisté si possible."""
        key = self._state_key(spec, year)
        request_id = store.get_sync_state("copernicus", key)
        if request_id:
            from cdsapi.api import Result

            result = Result(self.client(), {"request_id": request_id})
            result.update()
            return result
        result = self.client().retrieve(self.dataset_name, self.build_request(spec, year))
        new_id = (getattr(result, "reply", None) or {}).get("request_id")
        if new_id:
            store.set_sync_state("copernicus", key, str(new_id))
        return result

    def _wait(self, result) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            state = (getattr(result, "reply", None) or {}).get("state")
            if state in ("completed", "successful"):
                return
            if state in ("failed", "deleted"):
                message = (getattr(result, "reply", None) or {}).get("error") or state
                raise CdsError(f"Requête CDS en échec ({message}).")
            if time.monotonic() > deadline:
                raise CdsError(
                    f"Requête CDS toujours en file après {self.timeout:.0f} s. "
                    f"Relancer la synchronisation plus tard : l'identifiant de "
                    f"requête est conservé, rien ne sera re-soumis."
                )
            time.sleep(self.poll)
            result.update()

    def fetch(self, spec: Any, year: int) -> Raster:
        xarray = _require("xarray")
        result = self._result(spec, year)
        self._wait(result)
        work = config.work_dir() / "copernicus"
        work.mkdir(parents=True, exist_ok=True)
        netcdf = work / f"{spec.id}_{year}_cds.nc"
        result.download(str(netcdf))
        store.set_sync_state("copernicus", self._state_key(spec, year), None)

        dataset = xarray.open_dataset(netcdf)
        try:
            variable = _pick_variable(dataset, spec.extraction.variable)
            aggregated = _aggregate(
                dataset[variable],
                spec.extraction.temporal_agg.months,
                spec.extraction.temporal_agg.stat,
            ).load()
            lat_name = "latitude" if "latitude" in aggregated.coords else "lat"
            lon_name = "longitude" if "longitude" in aggregated.coords else "lon"
            lats = aggregated[lat_name].values
            lons, values = normalize_longitudes(aggregated[lon_name].values, aggregated.values)
            target = work / f"{spec.id}_{year}_cds.tif"
            write_geotiff(target, lats, lons, values)
            numpy = _require("numpy")
            units = str(dataset[variable].attrs.get("units") or "")
            sample_max = float(numpy.nanmax(values)) if values.size else None
        finally:
            dataset.close()
        if not _env("NUTSHELL_CDS_KEEP_RASTERS"):
            netcdf.unlink(missing_ok=True)
        today = datetime.now(UTC).date().isoformat()
        return Raster(
            path=target,
            source_date=f"{self.dataset_name} {today}",
            units=units,
            quality="",
            sample_max=sample_max,
        )


def _pick_variable(dataset, wanted: str) -> str:
    """Nom réel de la variable dans le NetCDF CDS (``skin_temperature`` → ``skt``)."""
    if wanted in dataset.data_vars:
        return wanted
    short_names = {"skin_temperature": "skt", "2m_temperature": "t2m"}
    candidate = short_names.get(wanted)
    if candidate and candidate in dataset.data_vars:
        return candidate
    if len(dataset.data_vars) == 1:
        return next(iter(dataset.data_vars))
    raise CdsError(
        f"Variable '{wanted}' introuvable dans le fichier CDS "
        f"(présentes : {', '.join(sorted(dataset.data_vars))})."
    )


class LocalProvider(RasterProvider):
    """Raster déposé manuellement — seule voie possible pour les produits CLMS.

    Attend ``NUTSHELL_RASTER_DIR/{indicateur}/{année}.tif`` en EPSG:4326.
    ``temporal_agg.months == []`` : aucune agrégation temporelle, le millésime du
    raster fait la période.
    """

    name = "local"

    def path_for(self, spec: Any, year: int) -> Path:
        return raster_dir() / spec.id / f"{year}.tif"

    def fetch(self, spec: Any, year: int) -> Raster:
        rasterio = _require("rasterio")
        candidates = [self.path_for(spec, year)]
        candidates.append(candidates[0].with_suffix(".tiff"))
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            hint = ""
            if "impervious" in spec.id:
                hint = f"\nTéléchargement (compte gratuit requis) : {CLMS_URL}"
            raise CdsError(
                f"Raster absent pour '{spec.id}' ({year}).\n"
                f"Déposer le GeoTIFF EPSG:4326 sous : {candidates[0]}"
                f"{hint}\n"
                f"La racine se règle par NUTSHELL_RASTER_DIR."
            )
        with rasterio.open(path) as src:
            crs = src.crs
            if crs is None or crs.to_epsg() != 4326:
                raise CdsError(
                    f"Le raster {path} est en {crs or 'CRS inconnu'} ; EPSG:4326 est "
                    f"attendu.\nReprojeter : gdalwarp -t_srs EPSG:4326 "
                    f"{path} {path.with_name(path.stem + '_4326.tif')}"
                )
            scale = max(1, max(src.height, src.width) // 512)
            preview = src.read(
                1, out_shape=(1, max(1, src.height // scale), max(1, src.width // scale)),
            )
            units = str((src.tags() or {}).get("units", ""))
        numpy = _require("numpy")
        finite = preview[numpy.isfinite(preview)]
        mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC).date().isoformat()
        return Raster(
            path=path,
            source_date=f"raster local {mtime}",
            units=units,
            quality="",
            sample_max=float(finite.max()) if finite.size else None,
            ephemeral=False,
        )


PROVIDERS = {"cds": CdsProvider, "arco": ArcoProvider, "local": LocalProvider}


def make_provider(name: str = "", bbox=None) -> RasterProvider:
    """Instancie le fournisseur demandé (ou celui déduit de l'environnement)."""
    name = (name or _env("NUTSHELL_CDS_PROVIDER") or default_provider()).lower()
    if name not in PROVIDERS:
        raise CdsError(
            f"Fournisseur de rasters '{name}' inconnu. "
            f"Valeurs possibles pour NUTSHELL_CDS_PROVIDER : {', '.join(PROVIDERS)}."
        )
    return PROVIDERS[name](bbox)


def provider_name_for(spec: Any) -> str:
    """Fournisseur adapté à un indicateur, quand l'environnement ne l'impose pas.

    ``cds`` comme ``arco`` ne servent que des réanalyses ERA5 : tout autre produit
    (couches CLMS notamment) ne peut venir que d'un raster déposé à la main.
    """
    explicit = _env("NUTSHELL_CDS_PROVIDER")
    if explicit:
        return explicit.lower()
    product = getattr(spec.extraction, "product", "") or ""
    return default_provider() if product.startswith("reanalysis-") else "local"


# ------------------------------------------------------ statistiques zonales

def kelvin_offset(spec: Any, units: str, sample_max: float | None) -> float:
    """Décalage à appliquer pour satisfaire l'unité du registre (K → °C).

    L'unité de la source prime ; à défaut, une valeur maximale supérieure à
    100 trahit une échelle absolue en kelvins.
    """
    if spec.unit != "DEG_C":
        return 0.0
    normalized = (units or "").strip().upper()
    if normalized in ("K", "KELVIN"):
        return -273.15
    if normalized:
        return 0.0
    if sample_max is not None and sample_max > 100.0:
        return -273.15
    return 0.0


def _pixel_area(path: Path) -> float:
    rasterio = _require("rasterio")
    with rasterio.open(path) as src:
        transform = src.transform
    return abs(transform.a * transform.e)


def zonal_rows(
    raster_path: Path,
    features: list[dict],
    code_property: str,
    stat: str,
    offset: float = 0.0,
    base_quality: str = "",
    time_label: str = "",
) -> list[dict]:
    """Statistiques zonales d'un raster contre des features GeoJSON.

    ``exactextract`` reçoit directement la liste de dicts Feature : passer un
    chemin de fichier exigerait GDAL/ogr, fiona ou geopandas côté Python, qu'on
    ne veut pas ajouter aux dépendances (cf. spike B3).

    La couverture est contrôlée en comparant la somme des fractions de mailles
    valides renvoyées par ``count`` au nombre de mailles qu'occuperait la zone
    entière : en deçà, la valeur est marquée ``partial_coverage``.
    """
    if not features:
        return []
    exactextract = _require("exactextract")
    ops = [stat] if stat == "count" else [stat, "count"]
    results = exactextract.exact_extract(
        str(raster_path), features, ops, include_cols=[code_property]
    )
    cell_area = _pixel_area(raster_path)
    by_code = {
        (f.get("properties") or {}).get(code_property): f.get("geometry") or {}
        for f in features
    }
    rows = []
    for result in results:
        props = result.get("properties") or {}
        code = props.get(code_property)
        value = props.get(stat)
        if code is None or value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if value != value:  # NaN : zone hors emprise du raster
            continue
        covered = float(props.get("count", 0.0) or 0.0)
        expected = geometry_area(by_code.get(code) or {}) / cell_area if cell_area else 0.0
        fraction = covered / expected if expected > 0 else 1.0
        quality = "partial_coverage" if fraction < COVERAGE_TOLERANCE else base_quality
        rows.append(
            {
                "geo_code": code,
                "time": time_label,
                "value": value + offset if stat in AFFINE_STATS else value,
                "quality": quality,
            }
        )
    return rows


# ------------------------------------------------------------------ partition

def _existing_rows(spec: Any, drop_years: set[str]) -> list[dict]:
    """Lignes déjà matérialisées pour les périodes qu'on ne recalcule pas."""
    path = indicators.partition_path(spec.id)
    if not path.exists():
        return []
    import duckdb

    rows = duckdb.execute(
        "SELECT geo_code, time, value, quality FROM read_parquet(?)", [str(path)]
    ).fetchall()
    return [
        {"geo_code": r[0], "time": r[1], "value": r[2], "quality": r[3] or ""}
        for r in rows
        if r[1] not in drop_years
    ]


def _last_year(spec: Any) -> int | None:
    raw = store.get_sync_state("copernicus", f"{spec.id}:last_year")
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


# ---------------------------------------------------------------------- sync

def sync(specs: list, full: bool = False) -> SyncReport:
    """Matérialise les indicateurs Copernicus du registre (contrat de `sync.py`)."""
    report = SyncReport("copernicus")
    config.ensure_dirs()
    try:
        years = target_years()
        countries = target_countries()
    except CdsError as exc:
        report.failed("copernicus", str(exc))
        return report
    if not years:
        report.note("aucune année cible (NUTSHELL_CDS_YEARS vide)")
        return report

    # -- périmètre spatial : features de tous les niveaux demandés, une seule fois
    levels = sorted({level for spec in specs for level in spec.geo_levels})
    features: dict[str, list[dict]] = {}
    for level in levels:
        try:
            features[level] = select_features(level, countries)
        except CdsError as exc:
            report.failed(level, str(exc))
    if not any(features.values()):
        report.failed(
            "périmètre",
            "aucune zone sélectionnée — vérifier NUTSHELL_CDS_COUNTRIES "
            f"({', '.join(countries) if countries else 'non défini'}) et le référentiel geo.",
        )
        return report
    everything = [f for group in features.values() for f in group]
    bbox = features_bbox(everything)
    scope = ", ".join(countries) if countries else "référentiel complet"
    report.note(
        f"périmètre {scope} : {len(everything)} zones sur {len(features)} niveau(x), "
        f"emprise {bbox[0]:.1f}/{bbox[1]:.1f} → {bbox[2]:.1f}/{bbox[3]:.1f}"
    )

    # -- années à produire par indicateur
    plan: dict[str, list[int]] = {}
    for spec in specs:
        last = None if full else _last_year(spec)
        todo = [y for y in years if last is None or y > last]
        if not todo:
            report.unchanged(spec.id)
            continue
        plan[spec.id] = todo
    if not plan:
        return report

    # -- un fournisseur par famille de produit, instancié à la demande
    pool: dict[str, RasterProvider] = {}
    assigned: dict[str, RasterProvider] = {}
    by_id = {spec.id: spec for spec in specs}
    for indicator_id in list(plan):
        try:
            name = provider_name_for(by_id[indicator_id])
            if name not in pool:
                pool[name] = make_provider(name, bbox=bbox)
                report.note(
                    f"fournisseur '{name}'"
                    + ("" if _env("NUTSHELL_CDS_PROVIDER") else " (déduit)")
                )
            assigned[indicator_id] = pool[name]
        except CdsError as exc:
            report.failed(indicator_id, str(exc))
            plan.pop(indicator_id, None)

    # Les requêtes d'un même fournisseur sont soumises d'un bloc avant collecte
    # (files d'attente CDS de plusieurs heures, §7.2).
    for provider in pool.values():
        jobs = [
            (by_id[i], year)
            for i, todo in plan.items()
            for year in todo
            if assigned.get(i) is provider
        ]
        try:
            provider.prepare(jobs)
        except Exception as exc:
            for spec, _ in jobs:
                report.failed(spec.id, f"soumission impossible : {exc}")
                plan.pop(spec.id, None)

    for indicator_id, todo in plan.items():
        try:
            written = _materialize(
                by_id[indicator_id], todo, assigned[indicator_id], features, report
            )
        except Exception as exc:
            report.failed(indicator_id, str(exc))
            continue
        report.updated(
            indicator_id,
            f"{written:,} lignes, années {', '.join(str(y) for y in todo)}",
        )
    for provider in pool.values():
        provider.close()
    return report


def _materialize(spec, years: list[int], provider, features, report) -> int:
    """Calcule et écrit la partition d'un indicateur pour les années demandées."""
    rows = _existing_rows(spec, {str(y) for y in years})
    source_date = ""
    for year in years:
        raster = provider.fetch(spec, year)
        source_date = raster.source_date
        offset = kelvin_offset(spec, raster.units, raster.sample_max)
        produced = 0
        for level in spec.geo_levels:
            level_features = features.get(level) or []
            new_rows = zonal_rows(
                raster.path,
                level_features,
                geo.geometry_code_property(level),
                spec.extraction.zonal_stat,
                offset=offset,
                base_quality=raster.quality,
                time_label=str(year),
            )
            produced += len(new_rows)
            rows += new_rows
        for note in raster.notes:
            report.note(f"{spec.id} {year} : {note}")
        # §7.2 : les rasters bruts sont le poste le plus lourd, purgés aussitôt.
        if raster.ephemeral and not _env("NUTSHELL_CDS_KEEP_RASTERS"):
            Path(raster.path).unlink(missing_ok=True)
        if not produced:
            raise CdsError(
                f"Aucune zone couverte par le raster {spec.id} {year} : "
                f"vérifier le périmètre (NUTSHELL_CDS_COUNTRIES) et l'emprise du produit."
            )
    written = indicators.write_partition(spec, rows, source_date=source_date)
    store.set_sync_state("copernicus", f"{spec.id}:last_year", str(max(years)))
    return written
