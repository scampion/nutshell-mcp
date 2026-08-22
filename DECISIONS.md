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

## Lot 2 — OSM

### ADR-L2-1. Périmètre configuré par variable d'environnement, défaut Luxembourg seul

**Contexte.** §7.3 laisse le choix du périmètre (« Europe entière ~30 Go, ou par
pays ») sans mécanisme de configuration. Deux options envisageables : variable
d'environnement, ou fichier `osm_extracts.txt`.

**Décision.** `NUTSHELL_OSM_EXTRACTS="europe/luxembourg,europe/belgium"`
(chemins Geofabrik complets, séparés par des virgules), sur le modèle des
autres variables du socle (`NUTSHELL_DATA_DIR`, `NUTSHELL_REGISTRY_DIR`) plutôt
qu'un fichier dédié — un pipeline de plus qui lirait son propre fichier de
config aurait cassé l'uniformité « tout se configure par variable
d'environnement » déjà en place. Défaut si absente : `("europe/luxembourg",)`
seul — jamais un extrait continental par défaut, conformément à la contrainte
d'environnement (ne jamais déclencher un gros téléchargement par accident).

**Conséquence.** `ingest_osm.configured_extracts()` est une fonction pure,
testable sans effet de bord. Étendre le périmètre à un troisième pays ne
touche aucun code, seulement la variable d'environnement (ou le cron qui
l'exporte).

### ADR-L2-2. Signal de fraîcheur en deux temps : md5 sidecar puis timestamp d'en-tête

**Contexte.** Le spike (A1) établit que le timestamp fiable est celui embarqué
dans l'en-tête du `.pbf` (`osmium fileinfo -e -g header.option.timestamp`), pas
le `Last-Modified` HTTP. Mais ce timestamp n'est lisible qu'une fois le fichier
téléchargé — potentiellement des centaines de Mo pour rien si l'extrait n'a pas
changé.

**Décision.** Le sidecar `.md5` (quelques octets) est récupéré et comparé à
l'état local *avant* tout téléchargement du `.pbf`. Un md5 inchangé implique un
contenu inchangé, donc un timestamp d'en-tête inchangé — le téléchargement et
le retraitement (filtrage, jointure) sont alors sautés, et le GeoParquet POI
déjà présent sur disque est réutilisé tel quel pour l'union multi-extraits.

**Conséquence.** Rejouer `sync --source osm` sans changement côté Geofabrik ne
retélécharge jamais l'extrait (vérifié empiriquement sur le Luxembourg réel,
voir rapport de mission). Économie substantielle pour la Belgique (~600 Mo) à
chaque cron mensuel où rien n'a changé.

### ADR-L2-3. Clip transfrontalier par préfixe pays du `geo_code`

**Contexte.** Piège n°3 du spike : un extrait pays Geofabrik déborde toujours
un peu sur les pays voisins (POI géométriquement situés en France/Belgique/
Allemagne dans l'extrait Luxembourg). Sans traitement, ingérer deux extraits
limitrophes (LU + BE) compterait deux fois les POI proches de la frontière.

**Décision.** Un POI d'un extrait n'est retenu que s'il tombe dans une zone dont
le préfixe pays du `geo_code` (2 premiers caractères, convention NUTS/Eurostat)
correspond au pays déclaré de l'extrait (`ingest_osm.GEOFABRIK_COUNTRY`, indexé
par nom court d'extrait). Un POI qui déborde géométriquement chez le voisin
est donc écarté par l'extrait d'origine, et n'est compté par l'extrait voisin
que si ce dernier le possède réellement dans son propre fichier — sinon il est
perdu, ce qui est le comportement correct (mieux vaut un POI en bordure non
compté qu'un double comptage systématique).

**Conséquence.** La convention NUTS est utilisée plutôt que l'ISO 3166-1 : la
Grèce (`EL`, pas `GR`) et le Royaume-Uni (`UK`, pas `GB`) auraient sinon cassé
silencieusement le clip pour ces deux pays si l'extension venait à les couvrir.
`GEOFABRIK_COUNTRY` documente ce choix en commentaire.

### ADR-L2-4. Zéro explicite pour toute zone du périmètre sans POI

**Contexte.** §7.3 demande d'inclure les zones à 0 POI, distinctes des zones hors
périmètre.

**Décision.** « Périmètre » = union des pays couverts par au moins un extrait
configuré (préfixe `geo_code`). Toute zone de ce périmètre reçoit une ligne
(valeur 0 si aucun POI ne correspond) ; toute zone d'un pays non couvert
n'apparaît pas du tout dans la partition.

**Conséquence.** `get_indicators(["hospitals_count"], ["LU000", "BE100"])`
renvoie une valeur pour les deux même si l'une vaut 0, alors qu'une zone
allemande n'apparaît jamais tant qu'aucun extrait allemand n'est configuré —
la distinction entre « aucun hôpital » et « donnée non collectée » reste
lisible par le modèle.

### ADR-L2-5. Une seule partition par indicateur, union de tous les extraits

**Contexte.** `indicators.write_partition` remplace toujours la partition
entière (pas d'append). Avec plusieurs extraits, il faut donc décider où vit
l'agrégation multi-extraits.

**Décision.** `ingest_osm.sync()` calcule les comptages de **tous** les extraits
configurés (en relisant le GeoParquet des extraits inchangés plutôt qu'en les
retraiter) avant un unique appel `write_partition` par indicateur. `time` et
`source_date` du batch entier prennent le mois le plus récent parmi les
extraits utilisés (`f"extrait {AAAA-MM}"`) — le schéma canonique ne porte
qu'une `source_date` par écriture, pas une par ligne.

**Conséquence.** La partition d'un indicateur OSM est toujours cohérente et
complète après un `sync`, jamais un mélange de deux écritures partielles. Un
indicateur n'est re-matérialisé que si au moins un extrait a changé (ou
`--full`), sinon il est rapporté `unchanged` sans toucher au disque.

### ADR-L2-6. `railway=halt` exclu de `train_stations_count`

**Contexte.** §7.3 ne tranche pas si les arrêts sans bâtiment voyageurs
(`railway=halt`) comptent comme des « gares ».

**Décision.** Exclus. `train_stations_count` ne couvre que `railway=station`.

**Conséquence.** Le nombre reste comparable à travers l'Europe (le partage
gare/halte varie fortement par pays et n'est pas toujours cartographié de
façon cohérente) et concorde avec la valeur de plausibilité mesurée sur le
Luxembourg réel (~65). Un futur indicateur `railway_stops_count` (station +
halt) pourrait être ajouté comme fichier YAML séparé sans toucher au pipeline.

### ADR-L2-7. `geometry: [node, way, relation]` pour les trois indicateurs

**Contexte.** Le registre initial ne déclarait que `[node, way]` pour les trois
indicateurs OSM. Le spike a mesuré, sur le Luxembourg réel, que les hôpitaux
sont 13 way + 2 relation (0 node), et les écoles 352 way + 34 node + 7
relation : omettre `relation` sous-compte silencieusement.

**Décision.** Les trois YAML déclarent `geometry: [node, way, relation]`, y
compris `train_stations_count` (65 node, 0 way/relation sur le Luxembourg) par
précaution pour d'autres pays où de grandes gares peuvent être cartographiées
en relation.

**Conséquence.** Aucun coût mesurable (une expression `osmium tags-filter` de
plus par catégorie) ; couverture correcte dès le premier extrait ingéré.

### ADR-L2-8. Doublons node/way non dédupliqués (limite connue, assumée)

**Contexte.** Piège n°4 du spike : un hôpital peut être cartographié à la fois
comme nœud isolé et comme empreinte de bâtiment ; aucun tag OSM standard ne
relie les deux représentations.

**Décision.** Aucune déduplication. Documenté en commentaire de code
(`ingest_osm.py`, docstring de module) et dans le README.

**Conséquence.** Cohérent avec `quality = "osm_completeness_unknown"`, déjà
systématique sur tous les indicateurs OSM (§7.3) : le modèle est prévenu que
ces comptages sont approximatifs, sans prétendre à une précision que la donnée
source ne permet pas de garantir à ce stade.
