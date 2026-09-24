# Exemples de prompts — à quoi sert nutshell-mcp

🇫🇷 Français · [🇬🇧 English](examples.md) · [← README](../README.fr.md)

Chaque exemple est un prompt à coller dans n'importe quel client MCP connecté
au serveur (`https://nutshell.scamp.fr/mcp`, ou votre propre instance). Le
modèle n'écrit jamais d'URL SDMX, de requête Overpass ni de requête CDS : il
choisit un tool, le serveur valide et répond depuis les données locales.

> Les sorties de tools sont en français. Le modèle répond dans la langue de
> votre prompt.

| # | Exemple | Tools enchaînés | Montre |
|---|---|---|---|
| 1 | [Où ouvrir une clinique gériatrique ?](#1-où-ouvrir-une-clinique-gériatrique-) | couche unifiée + grain natif | croisement Eurostat / OSM, flags qualité |
| 2 | [Comparer quatre régions](#2-comparer-quatre-régions) | 3 tools unifiés | un tableau, une colonne par indicateur |
| 3 | [Quand le registre s'arrête à NUTS2](#3-quand-le-registre-sarrête-à-nuts2) | couche unifiée → grain natif | repli sur NUTS3, erreurs actionnables |
| 4 | [Le tourisme, au-delà du registre](#4-le-tourisme-au-delà-du-registre) | grain natif Eurostat | le catalogue de 10 301 datasets |
| 5 | [Un nouvel indicateur en un fichier YAML](#5-un-nouvel-indicateur-en-un-fichier-yaml) | grain natif → registre | le modèle rédige le YAML |
| 6 | [Canicules et personnes âgées](#6-canicules-et-personnes-âgées) | couche unifiée, 3 lots | climat × vieillissement × hôpitaux (3 sources) |
| 7 | [Déménager avec de jeunes enfants](#7-déménager-avec-de-jeunes-enfants) | un seul appel `get_indicators` | 5 indicateurs issus de 3 sources |

---

## 1. Où ouvrir une clinique gériatrique ?

La démo phare : une question de décision qu'aucune source ne traite seule.

```
Je dois choisir la région européenne où ouvrir une clinique gériatrique.
Compare les régions NUTS2 de la France, de la Belgique et du Luxembourg :
je veux celles où la population est la plus âgée, où l'offre hospitalière
(OSM) est la plus faible rapportée à la population, avec un PIB par habitant
correct. Donne-moi un top 5 justifié, avec un tableau des chiffres, et
précise la fiabilité de chaque source.
```

**Ce qui se passe.** Le modèle découvre les indicateurs avec
`search_indicators`, liste les zones de chaque pays avec `list_zones`, puis
appelle `get_indicators` en plusieurs lots (limite : 5 indicateurs et 100 zones
par appel). Insatisfait du *nombre* d'hôpitaux OSM (il compte des sites, pas des
lits), il descend au grain natif — `search_datasets` → `get_structure` →
`list_codes` → `query_data` — pour trouver les vrais *lits* d'hôpitaux par
région.

**Ce qu'un vrai run a produit** (extrait condensé — [réponse complète](results/01-geriatric-clinic.md)) :

| # | Région (NUTS2) | Dépendance 65+ | Lits / 100 000 hab. | PIB / hab. |
|---|---|---|---|---|
| 1 | Brabant wallon (BE31) | 33,4 % | 225,3 | 69 500 € |
| 2 | Poitou-Charentes (FRI3) | 47,3 % | 492,9 | 34 900 € |
| 3 | Vlaams-Brabant (BE24) | 32,5 % | 377,4 | 57 100 € |
| 4 | Basse-Normandie (FRD1) | 44,3 % | 557,2 | 34 600 € |
| 5 | Corse (FRM0) | 43,2 % | 552,0 | 37 500 € |

Le classement est un score composite (z-scores) calculé par le modèle
(pondérations : 40 % âge, 40 % offre, 20 % PIB), sur 39 zones.

**Pourquoi c'est convaincant.** L'intérêt n'est pas le tableau, mais ce que la
couche de provenance a permis au modèle d'en dire :

- Les lits belges portent tous le flag `d` (*définition différente*) : le modèle
  a averti que la comparaison FR/BE est *indicative, pas une mesure* — et que les
  rangs 1 et 3 sont belges.
- OSM renvoyait 0 hôpital pour les cinq départements d'outre-mer ; le modèle a
  repéré le défaut de complétude (`osm_completeness_unknown`) et les a exclus.
- Le Luxembourg ne renvoyait aucune donnée de lits ; le modèle a signalé *un
  trou de données, pas un mauvais score*, et l'a classé sur la seule démographie.
- Les valeurs `[p]` (provisoires) de 2025 ont été signalées comme telles.

La recommandation finale est nuancée en conséquence — c'est tout l'intérêt : un
modèle qui voit les flags qualité se comporte en analyste, pas en moteur de
recherche.

**Ce que le modèle a mal lu.** Il a averti que les données françaises portaient
sur la « géographie régionale d'avant 2016 » (Poitou-Charentes plutôt que
Nouvelle-Aquitaine) et recommandé de refaire l'analyse en NUTS 2021. C'est une
erreur de lecture : en NUTS 2021 comme en 2024, les régions françaises actuelles
forment le niveau NUTS1 (`FRI` Nouvelle-Aquitaine), tandis que le niveau NUTS2
conserve les anciennes régions (`FRI3` Poitou-Charentes). Les données étaient à
jour ; c'est le niveau NUTS2 qui ne correspond pas aux régions administratives
d'aujourd'hui.

---

## 2. Comparer quatre régions

Le prompt utile le plus court — une question, trois appels de tools.

```
Compare le chômage, l'âge médian et le PIB par habitant de l'Île-de-France,
de l'Oberbayern, de la Lombardie et de la Catalogne. Laquelle paraît la plus
dynamique, et pourquoi ?
```

**Vrai run** avec Qwen3.8-27B (prompt en anglais) —
[transcript complet](results/02-compare-regions.md). Le modèle a lancé en
parallèle 3 `search_indicators` et 4 `list_zones`, a relancé une fois
`list_zones` (`contains="Île-de-France"` ne trouve rien : le nom GISCO est
`Ile-de-France`, sans accent), puis 2 appels `get_indicators` :

```
geo_code | time | unemployment_rate | median_age | gdp_per_capita
DE21 | 2025 | 3 | 43.3 |
DE21 | 2024 | 2.7 | 43.3 | 75700 [e]
DE21 | 2023 | 2.3 | 43.3 [b] | 74700 [p]
ES51 | 2025 | 8.4 [d] | 44.6 |
ES51 | 2024 | 8.9 [d] | 44.4 | 37500 [p]
…
[Source : eurostat (unemployment_rate 30.06.2026, median_age 10.07.2026, gdp_per_capita 10.02.2026)]
```

Réponse (extrait, traduit) :

| Région | Chômage | Âge médian | PIB / hab. |
|---|---|---|---|
| **Oberbayern** (DE21) | **2,7 %** (2024) | 43,3 | **75 700 €** |
| **Île-de-France** (FR10) | 8,0 % (2024) | **38,2** | 69 500 € |
| **Lombardia** (ITC4) | 3,7 % (2024) | 48,1 | 50 400 € |
| **Cataluña** (ES51) | 8,9 % (2024) | 44,4 | 37 500 € |

> **L'Oberbayern est la plus dynamique *aujourd'hui* (richesse + plein
> emploi).** Si l'on entend le dynamisme comme un *potentiel de croissance*,
> c'est la population jeune de l'Île-de-France qui se distingue.

Sans filtre temporel, le serveur renvoie les 3 dernières périodes : le modèle
voit la tendance sans effort. Point de vigilance avec un modèle 27B : dans son
raisonnement, il a pris le flag `[d]` pour « non disponible » au lieu de
*définition différente* — demander explicitement la fiabilité (exemple 1) pousse
le modèle à vérifier.

---

## 3. Quand le registre s'arrête à NUTS2

```
Give me the gdp_capita of FR10 for the last 3 years, then the GDP per capita
of the NUTS3 zone FR101.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/03-nuts3-fallback.md).
Le modèle n'a jamais envoyé la faute de frappe : il a d'abord appelé
`search_indicators("GDP per capita")` et utilisé le bon identifiant,
`gdp_per_capita`. Le registre s'arrête à NUTS2 : il a obtenu FR10 via
`get_indicators`, puis est descendu au grain natif pour Paris :

```
search_datasets("GDP NUTS")          → nama_10r_3gdp | Gross domestic product (GDP) at current market prices by NUTS 3 region
get_structure("nama_10r_3gdp")       → unit: EUR_HAB (Euro per inhabitant), …
query_data("nama_10r_3gdp", {"geo": "FR101", "unit": "EUR_HAB"}, 2022–2024)

freq | unit | geo | time | value | flag
A | EUR_HAB | FR101 | 2022 | 123100.0 | p
A | EUR_HAB | FR101 | 2023 | 125300.0 | p
A | EUR_HAB | FR101 | 2024 | 133700.0 | p
[Source : miroir local, données Eurostat du 10.02.2026]
```

Réponse : FR10 63 200 € → 66 800 € → 69 500 €, FR101 123 100 € → 125 300 € →
133 700 € (2022–2024, toutes provisoires).

**Erreurs actionnables.** Si le modèle avait envoyé la faute de frappe ou
demandé NUTS3 au registre, le serveur aurait répondu avec la correction
(vraies sorties du serveur) :

```
get_indicators(["gdp_capita"], ["FR10"])
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.

get_indicators(["gdp_per_capita"], ["FR101"])
'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).
```

Chaque erreur nomme l'action corrective et propose 3 suggestions au plus
(`difflib`) : c'est ce qui permet à un modèle de 27B de suivre des enchaînements
de tools sans humain.

> *Ce run a révélé une faiblesse depuis corrigée :* quatre appels à
> `search_datasets` (« gross domestic product regions », « GDP regions »…) ne
> renvoyaient rien, car la recherche exigeait chaque mot à l'identique. Elle
> accepte désormais les pluriels et, si aucun titre ne contient tous les mots,
> se replie sur « au moins un mot » en le signalant.

---

## 4. Le tourisme, au-delà du registre

Le registre contient un jeu d'indicateurs choisis ; le grain natif expose tout
Eurostat.

```
Find in Eurostat a dataset on nights spent at tourist accommodation by region.
Which five NUTS2 regions of Spain and Italy had the most nights in the latest
year available? Tell me which filters you used.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/04-tourism.md). Le
modèle a cherché dans le catalogue, comparé `tour_occ_nin2` et `tour_occ_nin2dc`
avec `get_structure`, listé les codes espagnols et italiens avec `list_codes`,
puis lancé un seul `query_data` sur les 40 régions :

| Rang | Région | Code | Année | Nuitées |
|---|---|---|---|---|
| 1 | Canarias | ES70 | 2024 | 99 488 821 |
| 2 | Cataluña | ES51 | 2024 | 88 670 191 |
| 3 | Andalucía | ES61 | 2024 | 77 308 673 |
| 4 | Veneto | ITH3 | 2025 | 74 157 131 |
| 5 | Illes Balears | ES53 | 2024 | 73 845 222 |

Il a indiqué ses filtres (`unit=NR`, `c_resid=TOTAL`, `nace_r2=I551-I553`,
`freq=A`) et signalé de lui-même que la dernière année est 2024 pour l'Espagne et
2025 pour l'Italie — puis vérifié qu'une comparaison à année égale donne le même
top 5. Tous les chiffres correspondent au miroir.

> *Un premier run a révélé une faiblesse du serveur, depuis corrigée* —
> [transcript](results/04-tourism-before-fix.md). `list_codes(contains="ES")`
> cherchait aussi dans les libellés (« Bruxell**es** », « H**es**sen »…), qui
> occupaient 36 des 60 lignes affichées ; ES63, ES64 et ES70 tombaient après la
> coupure. Le modèle a ignoré l'indication `… et 53 autres, affinez 'contains'`
> pour l'Espagne, a oublié les Canaries et donné un mauvais n° 1. Les codes qui
> commencent par le filtre passent désormais en premier, niveaux hauts d'abord.

---

## 5. Un nouvel indicateur en un fichier YAML

Ajouter un indicateur au registre ne demande aucun code — voir
[Ajouter un indicateur](../README.fr.md#ajouter-un-indicateur--un-fichier-yaml).
Le modèle peut même écrire le YAML :

```
I run a nutshell-mcp server and want to add a new indicator: hospital beds per
100,000 inhabitants at NUTS2 level. Find the right Eurostat dataset and the
filter codes, then write the registry YAML file using this schema: id, label,
unit, source: eurostat, frequency: A, geo_levels, extraction: {dataset,
filters, value_dim: geo}. Check that the codes you use really exist.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/05-new-indicator-yaml.md).
Le modèle a comparé trois datasets candidats avec `get_structure`, vérifié
chaque code avec `list_codes`, lancé un `query_data` de test, puis écrit :

```yaml
id: hospital_beds_per_100k
label: "Lits d'hôpital disponibles pour 100 000 habitants"
unit: P_HTHAB
source: eurostat
frequency: A
geo_levels:
  - NUTS2
extraction:
  dataset: hlth_rs_bdsrg
  filters:
    freq: A
    unit: P_HTHAB
    facility: HBEDT
  value_dim: geo
```

Ce fichier passe tel quel `python -m nutshell_mcp.registry validate`. Le modèle
a aussi signalé de lui-même que le dataset mélange des générations NUTS (`DE1`,
`ITC4`) et s'arrête vers 2020.

**Ce qu'un humain doit encore vérifier.** Cette réserve est l'indice :
`hlth_rs_bdsrg` s'intitule *« Hospital beds by NUTS 2 region - historical data
(1993-2016) »*. La série courante est `hlth_rs_bdsrg2` (*Available beds in
hospitals by NUTS 2 region*, 1993–2025). Remplacer le dataset, puis :

```bash
.venv/bin/python -m nutshell_mcp.registry validate
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators hospital_beds_per_100k
```

Le serveur relit le registre à chaud : l'indicateur apparaît dans
`search_indicators` sans redémarrage, et l'exemple 1 peut alors l'utiliser via
`get_indicators` plutôt que par le grain natif. (Le modèle proposait aussi de
ranger le fichier sous `indicators/` ; le répertoire du registre est
`registry/`.)

---

## Croiser les trois sources

Les exemples précédents combinent surtout deux sources. Les questions
ci-dessous exigent les trois regards à la fois sur un territoire :
**socio-économique** (qui y vit — Eurostat), **géographique** (quel est le
milieu — Copernicus) et **infrastructures** (de quoi dispose-t-on —
OpenStreetMap).

## 6. Canicules et personnes âgées

```
Heatwaves hit the elderly hardest. Among the NUTS3 regions of Spain and Italy,
which ones combine the hottest summers, the oldest population and the fewest
hospitals per 100,000 inhabitants? Give me a ranked top 10 with the figures,
and explain how much each data source can be trusted.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/06-heat-ageing.md).
Le modèle a trouvé les quatre indicateurs (`lst_summer_mean`,
`old_age_dependency`, `population`, `hospitals_count`), listé les 159 régions
NUTS3 avec `list_zones`, puis écrit un petit script via l'outil `mcpScript` du
harness, qui appelle `get_indicators` en trois lots (limite de 100 zones par
appel) et classe les régions par centiles :

| # | Région | Temp. estivale (°C) | 65+ / 15–64 (%) | Hôpitaux (OSM) | Pour 100 000 |
|---|---|---|---|---|---|
| 1 | Asti (ITC17) | 25,1 | 45,2 | 2 | 0,97 |
| 2 | Lecce (ITF45) | 27,8 | 42,6 | 18 | 2,35 |
| 3 | Terni (ITI22) | 24,8 | 48,0 | 4 | 1,86 |
| 4 | Cagliari (ITG2G) | 25,9 | 49,5 | 4 | 2,70 |
| 5 | Trapani (ITG11) | 27,7 | 39,8 | 8 | 1,94 |
| … | | | | | |
| 10 | Salamanca (ES415) | 23,3 | 46,3 | 6 | 1,83 |

Sa section fiabilité classe les sources comme le ferait un analyste : Eurostat
« confiance élevée », température « modérée », comptages d'hôpitaux OSM
« confiance la plus faible, le maillon faible » — cartographie inégale, et un
ratio pour 100 000 qui bascule sur un seul hôpital manquant quand les effectifs
sont petits. Conclusion : *lire le top 10 comme une liste indicative, pas comme
un ordre précis.*

**Ce que nous avons vérifié.** Ratios de dépendance, nombres d'hôpitaux et
populations correspondent exactement au miroir. Pas les températures : le modèle
les annonce « 2024 », mais son script lisait la troisième ligne de chaque zone,
qui est **2023** (Asti 25,1 °C en 2023, 23,8 °C en 2024). Le classement est donc
un classement de chaleur 2023. Le modèle décrit aussi la température comme une
température de surface satellitaire ; c'est la température de peau de la
réanalyse ERA5-Land, marquée `[sampled]` sur ce serveur de démonstration
(estimation du fournisseur ARCO, sans clé).

## 7. Déménager avec de jeunes enfants

```
My family with two young children wants to move to Germany or Austria. Compare
their NUTS2 regions: we want mild summers, low unemployment, and as many
schools and train stations as possible relative to population. Suggest the 5
best regions with a table of figures, and tell me what the data cannot tell us.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/07-family-relocation.md).
Quatre `search_indicators`, deux `list_zones`, puis **un seul appel
`get_indicators`** : 5 indicateurs issus de 3 sources sur 45 régions —
exactement les limites d'un appel :

```
get_indicators(["lst_summer_mean", "unemployment_rate", "schools_count",
                "train_stations_count", "population"], [DE11 … AT34])
```

| # | Région | Été (°C) | Chômage | Écoles / 1 000 hab. | Gares / 1 000 hab. |
|---|---|---|---|---|---|
| 1 | Oberösterreich (AT31) | 19,7 | 3,8 % | 0,640 | 0,091 |
| 2 | Steiermark (AT22) | 18,4 | 4,4 % | 0,608 | 0,095 |
| 3 | Lüneburg (DE93) | 18,7 | 2,7 % | 0,488 | 0,078 |
| 4 | Oberfranken (DE24) | 18,4 | 2,7 % | 0,521 | 0,059 |
| 5 | Tübingen (DE14) | 18,4 | 2,8 % | 0,531 | 0,056 |

Tous les chiffres du tableau correspondent au miroir. Le modèle a rendu « doux »
explicite (17,5–20 °C), proposé l'autre lecture (des étés *frais* placent le
Tyrol en tête) et listé ce que les données ne disent pas : places en crèche, coût
du logement, fréquence des trains plutôt que nombre de gares, fréquence des
canicules plutôt qu'une moyenne estivale, et le biais par habitant qui favorise
les petites régions peu peuplées.

---

## Conseils pour une démo

- **Demandez la provenance.** « Précise la fiabilité de chaque source » déclenche
  le raisonnement sur les flags qualité qui fait la force de l'exemple 1.
- **Forcez un niveau de raisonnement moyen/bas** sur les petits modèles locaux :
  le défaut `xhigh` sur-réfléchit les enchaînements de tools simples.
- **Surveillez les limites.** 5 indicateurs et 100 zones par appel à
  `get_indicators` : un bon modèle fait des lots seul ; un modèle plus faible
  suivra le message de troncature.
- **Les indicateurs `SNAPSHOT`** (comptages OSM comme `hospitals_count`) décrivent
  l'état courant et sont répétés sur chaque période de la zone, marqués
  `[snapshot AAAA-MM]` — ne pas les lire comme une série temporelle.
