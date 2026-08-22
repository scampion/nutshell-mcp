# Décisions d'implémentation (ADR courts)

Écarts et choix non tranchés par `architecture-spec-mcp-territorial.md`.
Format : contexte → décision → conséquence.

---

## ADR-L1-1. URLs GISCO retenues

**Contexte.** La spec (§4) dit « construire le référentiel depuis GISCO » sans
nommer de fichier. Le service de distribution publie 7 millésimes NUTS, 5
résolutions, 3 projections et 6 formats.

**Décision.** Vérifiées par requête réelle avant codage, les URLs retenues sont :

| usage | URL |
|---|---|
| NUTS, niveaux 0-3 | `https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_{01M\|10M}_{2024\|2021}_4326_LEVL_{0..3}.geojson` |
| Villes Urban Audit | `…/v2/urau/geojson/URAU_RG_100K_{2024\|2021}_4326_CITIES.geojson` |
| Correspondance de millésimes | `https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx` |

- `RG` (region) et non `BN` (boundaries) : ce sont les polygones qui servent aux
  statistiques zonales et aux jointures spatiales.
- EPSG **4326** partout, pour que `exactextract`, GDAL et DuckDB spatial lisent
  les fichiers sans reprojection préalable et que les rasters ERA5-Land
  (également en 4326) se recouvrent directement.
- `01M` pour l'ingestion (§4 : « 1:1M pour les statistiques zonales »), `10M`
  pour l'affichage. Les attributs (codes, noms, parents) sont identiques dans
  les deux : la table `geo` est construite depuis le 10M, dix fois plus léger.
- Urban Audit n'existe qu'en `100K` : la résolution est ignorée pour `CITY`.

**Conséquence.** 18 fichiers, 173 Mo sur disque — sous le budget de 500 Mo
annoncé au §10.

---

## ADR-L1-2. Géométries conservées en GeoJSON brut

**Contexte.** La spec autorise « GeoJSON/GeoParquet » (§4).

**Décision.** Les fichiers GISCO sont stockés tels quels, sans conversion.

**Conséquence.** `exactextract` (lot 3) les lit via GDAL, l'extension spatiale de
DuckDB via `ST_Read` (lot 2), `ogr2ogr` sans option. Une conversion en
GeoParquet aurait ajouté une dépendance spatiale au socle, que le serveur doit
pouvoir démarrer sans (CLAUDE.md). Le nom de la propriété portant le code de
zone est exposé par `geo.geometry_code_property(level)` : `NUTS_ID` pour les
NUTS, `URAU_CODE` pour les villes.

---

## ADR-L1-3. La table `geo` ne porte que le millésime courant

**Contexte.** La spec impose `geo(geo_code PK, …)` **et** la gestion de deux
millésimes (§4). Les deux sont incompatibles : `FRK2` existe en 2021 et en 2024.

**Décision.** `geo` contient le seul millésime courant (NUTS 2024 + villes 2024),
`geo_code` reste clé primaire. L'historique vit dans `nuts_changes`, qui contient
**tous** les codes 2021 (la colonne `old_code` couvre l'intégralité du millésime
précédent, y compris les codes inchangés).

**Conséquence.** `list_zones` ne montre jamais de région retirée. La projection
d'un indicateur déclaré `nuts_vintage: 2021` interroge `nuts_changes`, pas `geo`.
Les géométries 2021 restent téléchargées et accessibles par
`geo.geometry_path(level, vintage=2021)` pour les pipelines qui en auraient
besoin.

---

## ADR-L1-4. Bijectivité dérivée de la colonne « Change » du classeur Eurostat

**Contexte.** La spec parle d'une « table de correspondance GISCO entre
millésimes ». Le service de distribution GISCO n'en publie pas ; le classeur
officiel `NUTS2021-NUTS2024.xlsx` (feuille « NUTS2021- NUTS2024 ») en tient lieu.

**Décision.** Le classeur est lu avec la stdlib (`zipfile` + `ElementTree`) — un
XLSX est un zip de XML, aucune dépendance Excel n'est ajoutée. Colonnes
utilisées : C (code 2021), D (code 2024), H (nature du changement).
`bijective = 1` si les deux codes sont renseignés **et** que le changement est
vide, `Code change` ou `Name change`. Tout le reste (`Boundary shift`, `Merged`,
`Split`, `art. 5(2a)`, `New region`) donne `bijective = 0`.

**Conséquence.** 1 647 correspondances chargées, dont 83 non bijectives. La
projection ne recode que les 16 vrais changements de code (les identités n'ont
pas besoin d'être recodées) et marque `quality = 'recoded'`. Les zones 2021
supprimées disparaissent de la table canonique — elles n'ont pas d'équivalent
2024 et une valeur reportée serait fausse.

---

## ADR-L1-5. Villes Urban Audit incluses dès le lot 1

**Contexte.** Le lead autorisait un TODO si les villes posaient friction.

**Décision.** Elles sont ingérées : le fichier existe, pèse 13 Mo, et porte déjà
`NUTS3_2024`, ce qui donne `parent_code` sans jointure spatiale.

**Conséquence.** 739 villes de niveau `CITY` dans `geo`, immédiatement utilisables
par les indicateurs OSM et Copernicus qui déclarent ce niveau. `list_zones("CITY",
parent="FR")` fonctionne (le filtre parent accepte un préfixe de code NUTS).

---

## ADR-L1-6. `geometry_path` prend le niveau en premier argument

**Contexte.** L'interface demandée était `geometry_path(vintage, resolution)`.

**Décision.** La signature est `geometry_path(level, vintage=2024,
resolution="01M")`. GISCO publie un fichier **par niveau** : sans le niveau, la
fonction ne peut pas désigner un fichier.

**Conséquence.** Les pipelines appellent `geo.geometry_path("NUTS3")` pour le cas
courant.

---

## ADR-L1-7. `ingested_at` en timestamp UTC naïf

**Contexte.** Le schéma §6.1 dit « timestamp ».

**Décision.** `pa.timestamp("us")` sans fuseau, valeur en UTC.

**Conséquence.** DuckDB exige le module `pytz` pour convertir un `TIMESTAMP WITH
TIME ZONE` vers Python ; `pytz` n'est pas dans les dépendances et n'a pas à y
entrer pour une colonne d'horodatage interne. La convention UTC est documentée
dans le module.

---

## ADR-L1-8. Le registre est du code, pas de la donnée

**Contexte.** `NUTSHELL_DATA_DIR` déplace tout l'état sur disque.

**Décision.** `registry/*.yaml` ne suit pas `NUTSHELL_DATA_DIR` : il est
versionné dans le dépôt, comme le code. Une variable dédiée,
`NUTSHELL_REGISTRY_DIR`, permet de le déplacer (utilisée par les tests).

**Conséquence.** `rsync` du répertoire `mirror/` + `eurostat.db` réplique bien
l'état vivant (§9), et un déploiement met à jour le registre par un `git pull`.

---

## ADR-L1-9. Le registre se re-matérialise tout seul au service

**Contexte.** La spec ne dit pas quand `registry` est écrit dans SQLite.

**Décision.** `registry.ensure_materialized()` compare une empreinte
(nom + mtime + taille de chaque YAML) à celle enregistrée et re-matérialise si
elle a changé. Elle est appelée par `search_indicators` et `get_indicators`.

**Conséquence.** Ajouter un indicateur = déposer un YAML ; il est visible au tool
suivant, sans relancer de sync. Un registre devenu invalide ne casse pas le
serveur : la matérialisation échoue silencieusement et l'ancienne version
continue d'être servie (la validation bruyante, c'est `registry validate` en CI).

---

## ADR-L1-10. Jeu de règles `ruff` figé dans `pyproject.toml`

**Contexte.** `ruff check .` doit passer (CLAUDE.md), mais le jeu de règles par
défaut varie d'une version de ruff à l'autre.

**Décision.** `select = ["E", "F", "W", "I", "UP", "B", "C4", "SIM", "RUF"]`.
`BLE` (blind except) est délibérément exclu : §7 impose qu'un échec d'indicateur
n'interrompe pas le lot, ce qui se traduit par des `except Exception` assumés
dans chaque pipeline. `RUF001-003` sont exclus (apostrophes typographiques des
messages français), `B008` aussi (idiome `Field(...)` de pydantic).

---

## ADR-L1-11. Sans filtre temporel, les 3 dernières périodes sont globales

**Contexte.** §8.3 : « sans filtre temporel, seules les 3 dernières périodes sont
renvoyées ». Ambigu : 3 par zone, par indicateur, ou en tout ?

**Décision.** Les 3 périodes les plus récentes **de l'ensemble du résultat**.

**Conséquence.** Le tableau reste rectangulaire et comparable entre zones — ce
qui est le point du pivot. Une zone dont la dernière valeur est plus ancienne
apparaît avec des cellules vides, ce qui est une information utile, plutôt
qu'avec des périodes décalées qui rendraient la lecture trompeuse.

---

## ADR-L1-12. La ligne de provenance agrège par source, pas par indicateur

**Contexte.** §8.3 montre `[Source : eurostat (21.08.2026), copernicus (v2023),
osm (extrait 2026-08)]` sans dire quoi faire de deux indicateurs Eurostat de
dates différentes.

**Décision.** Une entrée par source, portant la `source_date` la plus récente des
indicateurs de cette source présents dans la réponse.

**Conséquence.** La ligne reste courte quel que soit le nombre d'indicateurs — ce
qui est l'objectif (P5, sorties bornées pour un 27B). Le détail par indicateur
reste disponible dans la table canonique.

---

## ADR-L1-13. `quality` non vide s'affiche entre crochets dans la cellule

**Contexte.** La table canonique porte `quality` (flag Eurostat, `recoded`,
`osm_completeness_unknown`…), mais la sortie pivotée n'a pas de colonne pour lui.

**Décision.** La valeur est suffixée : `66800 [p]`, `41 [osm_completeness_unknown]`.

**Conséquence.** Le modèle voit la réserve au moment où il lit le chiffre, sans
colonne supplémentaire ni ligne de note à corréler. Une cellule sans crochets est
une valeur sans réserve.

---

## ADR-L1-14. `--project-only` vit dans `mirror.py`, pas dans `sync.py`

**Contexte.** Le lead demandait « une commande pour projeter sans re-télécharger ».

**Décision.** `python -m nutshell_mcp.mirror --project-only [--datasets a,b]`.

**Conséquence.** `sync.py` garde une interface unique et orthogonale
(`--source`), tandis que `mirror.py` reste l'outil bas niveau du miroir natif,
conformément à sa conservation demandée « comme aujourd'hui ».

---

## Lot 3 — Copernicus

### ADR-L3-1. Trois fournisseurs de rasters derrière une interface unique

**Contexte.** La spec (§7.2) ne connaît qu'un chemin d'acquisition : `cdsapi`.
Or la machine de développement n'a pas de clé CDS, et le Copernicus Land
Monitoring Service (produit `imperviousness_share`) exige une authentification
qu'aucune API publique ne contourne — le spike a vérifié que le catalogue STAC
du Copernicus Data Space est navigable sans jeton mais que **le téléchargement
des assets ne l'est pas**, et qu'aucune collection « imperviousness » n'y
figure.

**Décision.** L'acquisition passe par un fournisseur, `fetch(spec, year) ->
Raster`, sélectionné par `NUTSHELL_CDS_PROVIDER` (défaut : `cds` si
`~/.cdsapirc` existe, sinon `arco`, avec la mention du choix dans le rapport de
sync). Tout l'aval — recalage, statistiques zonales, conversion d'unité,
écriture, purge — est commun.

**Conséquence.** Le pipeline est complet et testable sans clé ni réseau, et la
voie officielle CDS n'est pas un TODO : elle est implémentée, testée par mock
(construction de la requête, reprise sur `request_id`, échec de requête) et
prête à servir dès qu'une clé est configurée. `Raster` porte, en plus du chemin,
la `source_date`, l'unité de la source, la qualité de base et la valeur maximale
observée — la signature de la spec (« → chemin ») aurait obligé chaque
fournisseur à écrire ces métadonnées ailleurs.

### ADR-L3-2. ARCO-ERA5 échantillonné, marqué `sampled`

**Contexte.** `gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3`
est lisible **anonymement** et couvre 1940 → aujourd'hui. Mais il est chunké
`(1, 721, 1440)` : un chunk = une grille mondiale pour **un** pas de temps
horaire. Un sous-ensemble spatial ne réduit donc pas le nombre de requêtes
réseau (3 à 9 s chacune) ; une moyenne JJA horaire exacte (2208 pas) demande
1 à 2 h par indicateur et par année.

Les stores 6-horaires du même bucket ont été inspectés pour voir s'ils faisaient
mieux : `1959-2022-6h-1440x721.zarr` s'arrête au **31 décembre 2021**, ne
contient pas `skin_temperature`, et est chunké exactement pareil — un chunk par
pas de temps. Aucun gain, et une couverture temporelle qui exclut les années
récentes.

**Décision.** Le store horaire complet est conservé, et le fournisseur
**échantillonne** `NUTSHELL_ARCO_SAMPLES_PER_MONTH` pas de temps par mois
(défaut 4), aux heures synoptiques 00/06/12/18 réparties sur des jours espacés.
Les quatre heures sont systématiquement représentées : un échantillonnage à midi
seul surestimerait la moyenne de plusieurs degrés. Chaque valeur produite porte
`quality = "sampled"`.

**Conséquence.** Un été coûte ~1 min au lieu de 1-2 h. Les valeurs sont des
estimations : LU00 ressort à 18,98 °C pour JJA 2023 (le spike, en ne lisant que
des pas de temps de midi, trouvait 20,41 °C — l'écart est exactement le biais
diurne évité). Le flag remonte jusqu'à l'utilisateur du tool, entre crochets,
comme prévu par l'ADR-L1-13 : le modèle voit la réserve au moment où il lit le
chiffre. Le jour où une clé CDS est configurée, le fournisseur `cds` produit la
même partition sans ce flag.

### ADR-L3-3. `reanalysis-era5-land-monthly-means` plutôt que le produit horaire

**Contexte.** Le registre déclare `product: reanalysis-era5-land`. Le produit
horaire demanderait ~2208 pas de temps par été et par zone d'emprise.

**Décision.** Le fournisseur `cds` interroge
`reanalysis-era5-land-monthly-means` avec
`product_type = monthly_averaged_reanalysis` : 3 valeurs mensuelles au lieu de
2208 valeurs horaires pour un `temporal_agg` JJA. Le champ `product` du registre
reste la **famille** de produit, pas le nom exact du dataset CDS.

**Conséquence.** Requête légère, file d'attente plus courte, et `temporal_agg.stat`
s'applique aux moyennes mensuelles — ce qui est la définition attendue d'une
« moyenne estivale » et non une moyenne pondérée par le nombre d'heures. Pour un
`stat` autre que `mean`, la nuance compte (le maximum de trois moyennes
mensuelles n'est pas le maximum horaire de l'été) : c'est documenté dans le
module.

### ADR-L3-4. `imperviousness_share` passe par le fournisseur `local`

**Contexte.** Aucune voie automatisable sans authentification n'a été trouvée
pour les couches haute résolution CLMS.

**Décision.** Le produit est ingéré depuis un GeoTIFF EPSG:4326 déposé sous
`NUTSHELL_RASTER_DIR/{indicateur}/{année}.tif`. En son absence, l'erreur nomme
le chemin exact attendu, l'URL de téléchargement CLMS et la variable qui déplace
la racine ; un CRS autre que 4326 produit la ligne `gdalwarp` à exécuter.
`temporal_agg.months: []` signifie « pas d'agrégation temporelle », et `time`
vaut le millésime du raster.

**Conséquence.** L'indicateur n'est pas matérialisable en CI, mais il l'est en
une commande dès que l'utilisateur a téléchargé le fichier — sans code
supplémentaire. Aucune reprojection n'est faite par le pipeline : reprojeter une
couche CLMS à 10 m sur toute l'Europe est un travail de plusieurs dizaines de Go
qui n'a pas sa place dans un `sync` (§10 : l'espace de travail est budgété pour
des rasters ERA5, pas pour du 10 m continental).

### ADR-L3-5. Couverture partielle mesurée par l'aire de la géométrie

**Contexte.** §6.1 prévoit `quality = 'partial_coverage'`. `exactextract`
renvoie bien la somme des fractions de mailles couvertes (`count`), mais
seulement pour les mailles **valides et dans l'emprise du raster** : ce nombre
seul ne dit pas si la zone débordait.

**Décision.** Le dénominateur est calculé côté pipeline : aire planaire de la
géométrie GeoJSON (formule des lacets, trous déduits, ~20 lignes de stdlib)
divisée par l'aire d'une maille. En deçà de 99,9 % du ratio, la valeur est
marquée `partial_coverage`. Une zone entièrement hors emprise (valeur nulle ou
NaN) est simplement omise de la partition.

**Conséquence.** Le contrôle couvre les deux causes réelles — maille sans donnée
(ERA5-Land sur la mer, CLMS hors couverture) et zone débordant l'emprise — sans
ajouter shapely ni geopandas aux dépendances. `partial_coverage` **remplace**
la qualité de base plutôt que de s'y ajouter : une cellule ne porte qu'un flag,
conformément à l'ADR-L1-13, et la réserve la plus forte gagne.

### ADR-L3-6. `exactextract` reçoit des Features GeoJSON, pas un chemin

**Contexte.** Le spike (B3) a montré que `exact_extract(raster, chemin_vecteur,
ops)` exige GDAL/`ogr`, `fiona` ou `geopandas` côté Python.

**Décision.** Le pipeline lit lui-même le GeoJSON GISCO (stdlib `json`) et passe
la **liste de dicts Feature** à `exact_extract`. L'extra `copernicus` perd
`geopandas` et gagne `gcsfs` + `zarr` (fournisseur `arco`).

**Conséquence.** L'extra reste raisonnable, et le filtrage du périmètre
(`NUTSHELL_CDS_COUNTRIES` sur `CNTR_CODE`, à défaut le préfixe du code de zone)
se fait sur les mêmes objets, sans seconde lecture.

### ADR-L3-7. Une partition Copernicus porte une seule `source_date`

**Contexte.** `indicators.write_partition` réécrit la partition d'un bloc avec
une `source_date` unique, alors que le pipeline accumule les années.

**Décision.** Les années déjà matérialisées sont relues et fusionnées avec les
nouvelles, et la partition prend la `source_date` du dernier raster acquis.

**Conséquence.** Une valeur de 2021 réécrite en même temps qu'une valeur de 2024
affiche la version du produit la plus récente. C'est cohérent avec l'ADR-L1-12
(la provenance agrège par source, pas par ligne) et sans effet sur le contrat de
§6.1, qui ne demande pas une date par ligne. Une `source_date` par période
exigerait de changer la signature de `write_partition` — hors périmètre du lot.

### ADR-L3-8. `python -m nutshell_mcp.sync` délègue au module canonique

**Contexte (bug réel, découvert à la première validation).** Lancé par
`python -m nutshell_mcp.sync`, le fichier est chargé sous le nom `__main__` ;
`ingest_cds` faisant `from .sync import SyncReport`, Python importait le module
une **seconde** fois sous son vrai nom, avec une classe `SyncReport` distincte.
Le `isinstance(result, SyncReport)` de `sync_pipeline` échouait, et le rapport
du pipeline était silencieusement remplacé par un rapport vide — les données
étaient pourtant bien écrites.

**Décision.** Le bloc `if __name__ == "__main__"` de `sync.py` réimporte
`nutshell_mcp.sync` et appelle son `main`.

**Conséquence.** Un seul objet module, une seule classe `SyncReport`, et le
piège est neutralisé pour les deux pipelines (lot 2 compris) sans toucher au
contrat documenté.
