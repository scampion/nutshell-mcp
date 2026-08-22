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

**Contexte.** `TERRITORIAL_DATA_DIR` déplace tout l'état sur disque.

**Décision.** `registry/*.yaml` ne suit pas `TERRITORIAL_DATA_DIR` : il est
versionné dans le dépôt, comme le code. Une variable dédiée,
`TERRITORIAL_REGISTRY_DIR`, permet de le déplacer (utilisée par les tests).

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

**Décision.** `python -m territorial_mcp.mirror --project-only [--datasets a,b]`.

**Conséquence.** `sync.py` garde une interface unique et orthogonale
(`--source`), tandis que `mirror.py` reste l'outil bas niveau du miroir natif,
conformément à sa conservation demandée « comme aujourd'hui ».
