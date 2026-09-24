# Example 1 — Where to open a geriatric clinic?

Real run by the project author against `https://nutshell.scamp.fr/mcp`. Only the final answer was recorded (no tool trace); it is reproduced verbatim below, in French as returned.

## Prompt

> Je dois choisir la région européenne où ouvrir une clinique gériatrique. Compare les régions NUTS2 de la France, de la Belgique et du Luxembourg : je veux celles où la population est la plus âgée, où l'offre hospitalière (OSM) est la plus faible rapportée à la population, avec un PIB par habitant correct. Donne-moi un top 5 justifié, avec un tableau des chiffres, et précise la fiabilité de chaque source.

## Answer

Je vais construire cette analyse en croisant plusieurs sources. Commençons par identifier les indicateurs disponibles.

Excellent, il existe de vraies données de lits d'hôpitaux au niveau NUTS2. Vérifions leur structure.

Il existe de vraies données Eurostat de lits d'hôpitaux par NUTS2. Récupérons les données croisées.

Les données françaises sont bien présentes (millésime NUTS 2013, régions pré-fusion). Il manque le Luxembourg sur les lits — je le récupère, et j'ajoute les lits en soins de longue durée, très pertinents pour une clinique gériatrique.

Bon, j'ai l'essentiel. Pour calculer un ratio de lits rapporté à la population âgée (plus pertinent qu'un ratio global), je cherche la part des 65+ exacte.

## Ce que j'ai pu construire — et une alerte préalable

J'ai croisé 4 indicateurs Eurostat + 1 source OSM sur **39 zones NUTS2** (27 France, 11 Belgique, 1 Luxembourg). Un point de vigilance important avant tout : **les données de ce référentiel portent sur la géographie NUTS 2013 pour la France**, pas sur les régions actuelles. Vérification empirique : `FRC1 "Bourgogne"` compte 1 622 910 habitants et `FRC2 "Franche-Comté"` 1 177 270 — donc Bourgogne et Franche-Comté sont **séparées**, comme Basse/Haute-Normandie, Nord-Pas-de-Calais/Picardie, etc. Le découpage correspond aux 22 régions pré-fusion. C'est la limite n°1 de fiabilité (détaillée en fin de réponse).

### Méthode

Trois critères, chacun standardisé (z-score) pour être agrégeable :

| Critère | Indicateur retenu | Poids | Sens |
|---|---|---|---|
| Population âgée | Ratio de dépendance 65+ / 15-64 ans (2025) | 40 % | ↑ = mieux |
| Faiblesse de l'offre | Lits d'hôpitaux pour 100 000 hab. **et** pour 1 000 hab. de 65 ans + (moyenne des deux) | 40 % | ↓ = mieux |
| Solvabilité | PIB par habitant (2024) | 20 % | ↑ = mieux |

**Décision méthodologique importante :** j'ai testé *deux* dénominateurs pour l'offre. Le critère littéral (« lits / population ») et un critère métier (« lits / population de 65 ans et plus ») ne donnent pas le même classement. J'ai donc retenu la moyenne des deux, ce qui rend le résultat robuste aux deux lectures. Un classement sur le seul critère littéral donnerait : Brabant wallon, Poitou-Charentes, Vlaams-Brabant, **Pays de la Loire, Basse-Normandie**.

---

## Top 5 justifié

| # | Région (NUTS2) | Âge médian 2025 | Dépendance 65+ 2025 | Pop. 65+ (2024) | Part 65+ | Lits / 100 000 hab. | Lits / 1 000 hab. 65+ | PIB/hab. 2024 | Score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Prov. Brabant wallon (BE31)** | 43,3 ans | 33,4 % | 85 670 | 20,6 % | **225,3** | **10,9** | **69 500 €** | **+1,35** |
| 2 | **Poitou-Charentes (FRI3)** | 48,1 ans | **47,3 %** | 498 079 | **27,0 %** | 492,9 | 18,2 | 34 900 € | **+0,85** |
| 3 | **Prov. Vlaams-Brabant (BE24)** | 42,5 ans | 32,5 % | 241 568 | 20,2 % | **377,4** | 18,7 | 57 100 € | **+0,52** |
| 4 | **Basse-Normandie (FRD1)** | 46,5 ans | 44,3 % | 380 011 | 25,6 % | 557,2 | 21,8 | 34 600 € | **+0,41** |
| 5 | **Corse (FRM0)** | 47,0 ans | 43,2 % | 90 806 | 25,3 % | 552,0 | 21,8 | 37 500 € | **+0,40** |

**Lecture de chaque cas :**

- **Brabant wallon (BE31)** — Le profil « double tension » le plus net : population âgée plutôt aisée (PIB 2ᵉ plus élevé de tout le panel) et **aucune capacité hospitalière significative sur le territoire** (~940 lits pour 416 000 habitants). La province est en réalité un bassin résidentiel qui se soigne à Bruxelles et à Namur : les lits existent, mais pas *sur place*. Pour une clinique, c'est un territoire d'implantation, pas un territoire déjà couvert. **Attention : c'est aussi l'observation la plus fragile du lot** (voir fiabilité).
- **Poitou-Charentes (FRI3)** — Le candidat le plus **robuste** : 2ᵉ sur le score, mais 1ᵉ sur le critère de loin le plus consensuel (population très âgée + lits faibles *quel que soit le dénominateur*). 498 000 habitants de 65 ans et plus, 27 % de la population, et seulement 18,2 lits pour 1 000 seniors — alors que la moyenne des 33 zones est de 24,8. PIB modeste mais suffisant.
- **Vlaams-Brabant (BE24)** — Offre hospitalière la plus faible rapportée à la population de tout le panel (377 lits/100 000). Population plus jeune (32,5 %) car polarisée par Louvain, mais très solvable. Bon potentiel sur le segment 80+ et la dépendance lourde.
- **Basse-Normandie (FRD1)** — Combinaison la plus équilibrée côté France : 44,3 % de dépendance et 21,8 lits / 1 000 seniors. Tissu de petites villes (Caen, Cherbourg, Alençon), marché de taille intermédiaire.
- **Corse (FRM0)** — 47 ans d'âge médian, 21,8 lits / 1 000 seniors, PIB correct. Le seul bémol est la **taille du marché** (90 806 seniors seulement) : suffisant pour une clinique ciblée, probablement pas pour plusieurs. L'insularité joue en revanche en faveur de la captivité de la demande.

**Ce que le classement rejette, et pourquoi :**

- **Limousin (FRI2)** est la zone la plus âgée du panel (49,5 %) mais c'est aussi celle qui a le **plus de lits** (741,7 / 100 000 ; 26,3 / 1 000 seniors) : l'offre est déjà dimensionnée. Idem **Auvergne (FRK1)** et **Bourgogne (FRC1)**.
- **Luxembourg (LU00)** : exclu du top 5. C'est le territoire le plus riche (127 000 €/hab.) mais **le 2ᵉ plus jeune** (dépendance 22,0 % ; 15 % de 65+). Démographiquement, c'est l'inverse de la cible. De plus il n'a **aucune donnée de lits d'hôpitaux** dans le référentiel — il est donc également non classable sur le critère d'offre.
- **Bruxelles (BE10)** : 18,7 % de dépendance et 52,6 lits / 1 000 seniors. À l'opposé absolu de la cible (score −1,64).
- **Île-de-France (FR10)** : malgré des lits faibles rapportés à la population (473/100 000), la structure d'âge est jeune (24,9 %) → score négatif.

---

## Classement complet des 39 zones

Score composite : moyenne 0, écart-type 1. Au-dessus de +0,3 = profil nettement favorable.

| Rang | Zone | Dép. 65+ 2025 | Lits/100k 2024 | Lits/1 000 65+ | PIB/hab. € | Score |
|---|---|---|---|---|---|---|
| 1 | BE31 Prov. Brabant wallon | 33,4 % | 225,3 | 10,9 | 69 500 | +1,35 |
| 2 | FRI3 Poitou-Charentes | 47,3 % | 492,9 | 18,2 | 34 900 | +0,85 |
| 3 | BE24 Prov. Vlaams-Brabant | 32,5 % | 377,4 | 18,7 | 57 100 | +0,52 |
| 4 | FRD1 Basse-Normandie | 44,3 % | 557,2 | 21,8 | 34 600 | +0,41 |
| 5 | FRM0 Corse | 43,2 % | 552,0 | 21,8 | 37 500 | +0,40 |
| 6 | FRG0 Pays de la Loire | 37,3 % | 449,8 | 20,2 | 37 500 | +0,30 |
| 7 | BE22 Prov. Limburg | 36,3 % | 464,5 | 20,9 | 42 200 | +0,26 |
| 8 | FRH0 Bretagne | 41,0 % | 540,7 | 22,4 | 36 600 | +0,25 |
| 9 | FRC1 Bourgogne | 45,1 % | 631,8 | 24,3 | 35 900 | +0,24 |
| 10 | FRI1 Aquitaine | 40,6 % | 545,2 | 22,5 | 37 700 | +0,23 |
| 11 | FRB0 Centre — Val de Loire | 41,1 % | 554,6 | 23,1 | 35 500 | +0,19 |
| 12 | BE25 Prov. West-Vlaanderen | 40,9 % | 635,9 | 25,9 | 52 400 | +0,18 |
| 13 | FRI2 Limousin | 49,5 % | 741,7 | 26,3 | 32 100 | +0,15 |
| 14 | FRC2 Franche-Comté | 38,5 % | 506,5 | 22,1 | 31 900 | +0,11 |
| 15 | FRK1 Auvergne | 44,8 % | 659,6 | 25,4 | 34 400 | +0,10 |
| 16 | FRL0 Provence-Alpes-Côte d'Azur | 41,7 % | 624,9 | 25,5 | 41 800 | +0,09 |
| 17 | FRJ1 Languedoc-Roussillon | 42,9 % | 617,1 | 24,6 | 33 000 | +0,08 |
| 18 | FRF2 Champagne-Ardenne | 39,0 % | 557,7 | 24,1 | 37 800 | +0,06 |
| 19 | BE21 Prov. Antwerpen | 32,6 % | 526,2 | 26,0 | 60 700 | +0,03 |
| 20 | FRJ2 Midi-Pyrénées | 37,9 % | 563,8 | 24,5 | 38 600 | −0,03 |
| 21 | FRD2 Haute-Normandie | 36,3 % | 534,7 | 24,7 | 35 800 | −0,11 |
| 22 | FRF1 Alsace | 33,8 % | 507,0 | 24,3 | 38 700 | −0,15 |
| 23 | FRK2 Rhône-Alpes | 33,0 % | 511,3 | 25,3 | 43 400 | −0,17 |
| 24 | FRF3 Lorraine | 37,1 % | 566,0 | 25,2 | 31 300 | −0,22 |
| 25 | BE34 Prov. Luxembourg (BE) | 28,2 % | 390,3 | 21,7 | 32 500 | −0,26 |
| 26 | BE23 Prov. Oost-Vlaanderen | 32,9 % | 568,6 | 27,6 | 49 500 | −0,28 |
| 27 | FR10 Île-de-France | 24,9 % | 473,2 | 29,3 | 69 500 | −0,30 |
| 28 | BE35 Prov. Namur | 31,7 % | 501,7 | 25,2 | 35 800 | −0,34 |
| 29 | FRE2 Picardie | 34,3 % | 544,7 | 26,4 | 31 700 | −0,38 |
| 30 | BE33 Prov. Liège | 31,7 % | 559,5 | 28,2 | 38 400 | −0,52 |
| 31 | FRE1 Nord-Pas-de-Calais | 31,8 % | 557,9 | 28,6 | 33 500 | −0,60 |
| 32 | BE32 Prov. Hainaut | 31,5 % | 597,7 | 30,3 | 32 300 | −0,78 |
| 33 | BE10 Région de Bruxelles-Capitale | 18,7 % | 679,6 | 52,6 | 85 300 | −1,64 |
| — | **LU00 Luxembourg** | 22,0 % | **n.d.** | **n.d.** | **127 000** | non classé |
| — | FRY1-FRY5 (DOM) | 5 – 43 % | 147 – 553 | n.d. | 13 100 – 29 900 | exclus |

*DOM exclus : OSM renvoie 0 hôpital pour les 5 départements, ce qui est factuellement faux et prouve un défaut de complétude de la source. Par ailleurs leur PIB/hab. est très inférieur au seuil de solvabilité.*

---

## Fiabilité des sources — lecture critique

| Source | Indicateurs utilisés | Millésime | Fiabilité | Limites identifiées |
|---|---|---|---|---|
| Eurostat — statistiques démographiques | Âge médian, dépendance 65+, population, effectifs par classe d'âge | extraction 10.07 et 10.08.2026 | **Élevée** | Valeurs 2025 **provisoires** (`[p]`) pour toute la France, pas pour la Belgique → légère asymétrie FR/BE. Fiable au niveau NUTS2. |
| Eurostat — comptes régionaux | PIB par habitant | extraction 10.02.2026 | **Élevée** | 2024 provisoire (`[p]`) ; le PIB régional est une estimation descendante, moins précise que le national. |
| Eurostat — lits d'hôpitaux (`tgs00064`, `hlth_rs_bdsrg2`) | Lits disponibles / 100 000 hab. | extraction 13.07.2026 | **Moyenne à élevée** | Voir ci-dessous : deux problèmes distincts. |
| OSM | Nombre d'hôpitaux (comptage de sites) | extrait 2026-08 | **Faible** | Complétude explicitement *inconnue* ; 0 hôpital dans les DOM (défaut avéré) ; compte des **sites**, pas des lits. Utilisé uniquement en corroboration directionnelle. |
| Calculs dérivés | Part des 65+, lits / 1 000 hab. 65+, score composite | — | **Héritée** | Ce sont **mes** calculs ; le score dépend des pondérations (sensibilité testée, voir méthode). |

### Trois problèmes de fiabilité qui pèsent sur la décision

**1. Les lits belges portent tous le flag `d` (« definition differs »).** Les 11 zones belges sont marquées `d`, aucune zone française ne l'est. Cela signifie que le périmètre statistique des « lits d'hôpitaux » **n'est pas identique** entre les deux pays. J'ai vérifié la cohérence interne : la moyenne pondérée des zones belges (536 lits/100 000) reproduit exactement le chiffre national BE (536,2) — les données ne sont donc pas erronées, mais **la comparaison FR/BE en niveau est à considérer comme indicative, pas comme une mesure**. Or les rangs 1 et 3 de mon top 5 sont belges. C'est la principale fragilité de ce classement.

**2. Les deux valeurs belges extrêmes sont instables et probablement dues à des flux de patients.** Le Brabant wallon passe de 225,3 (2024) à **187,3 (2025)** lits/100 000 en un an, soit −17 % — aucune fermeture d'hôpital de cette ampleur n'est plausible. Ce chiffre reflète une **attribution administrative** : les lits des cliniques universitaires Saint-Luc et du CHIREC sont comptés à Bruxelles, où résident leurs patients. Dit autrement : la faiblesse de l'offre mesurée au Brabant wallon et en Vlaams-Brabant (UZ Leuven est à Louvain) est en partie un **artefact de découpage**, pas une pénurie réelle de soins accessibles. Pour un projet de clinique, l'argument garde du sens (peu de lits *sur le territoire*), mais il faut le vérifier sur le terrain avant d'investir.

**3. Le Luxembourg est un trou de données, pas un mauvais résultat.** `LU00` figure dans la liste des codes mais renvoie « aucune valeur » ; `LU` est absent du dataset de lits NUTS2, et l'absence est confirmée au niveau pays (`hlth_rs_bds2`). Je ne peux donc **rien affirmer** sur l'offre hospitalière luxembourgeoise. Sa mise à l'écart du top 5 repose uniquement sur la démographie, qui est un critère suffisant : avec 22 % de dépendance et 15 % de 65+, le Luxembourg est objectivement hors cible.

### Limites à garder en tête

- **Géographie NUTS 2013 pour la France** (limite majeure). Bourgogne, Franche-Comté, Basse-Normandie, Poitou-Charentes, Limousin etc. sont des **régions qui n'existent plus** administrativement. Correspondance pour mon top 5 : Poitou-Charentes → **Nouvelle-Aquitaine** ; Basse-Normandie → **Normandie** ; Corse → inchangée. Si vous croisez ces chiffres avec le site Eurostat actuel, vous verrez des régions fusionnées et donc des valeurs différentes — ce n'est pas une contradiction, c'est un changement de millésime. À refaire sur la géographie NUTS 2021 avant tout arbitrage.
- **Mélange de millésimes** : âge 2025, lits et PIB 2024. Impact marginal sur un classement relatif.
- **Ce que les données ne disent pas.** Les lits d'hôpitaux ne mesurent pas l'offre de soins gériatriques (EHPAD, MRS, services de soins infirmiers à domicile, hôpitaux de jour). Le Japon, les Pays-Bas ou le Danemark ont des ratios de lits bas parce que l'ensemble du modèle a basculé vers l'ambulatoire — un ratio bas n'est pas mécaniquement un besoin non couvert. Aucune donnée disponible ici sur les **lits en soins de longue durée au niveau NUTS2** : la seule série Eurostat existante (`hlth_rs_bdltc`) n'est publiée qu'au niveau pays (FR 969, BE 1 249, LU 1 175 lits/100 000 en 2025), ce qui n'est pas exploitable pour un choix régional.
- **Faisabilité réglementaire** : non couverte par les données. En France une clinique nécessite une autorisation ARS dans le cadre du SROS ; en Belgique l'ouverture de lits relève de la programmation hospitalière fédérale ; au Luxembourg, du ministère. **Avant de retenir un site, c'est le premier filtre à passer** — et il peut invalider un classement purement statistique.

---

## Recommandation

Si je devais n'en garder qu'une : **Poitou-Charentes (aujourd'hui Nouvelle-Aquitaine)**. C'est le seul candidat du top 5 qui combine un très fort signal d'âge (47,3 % de dépendance, 27 % de 65+), une offre hospitalière faible **quelle que soit la façon de la mesurer** (18,2 lits / 1 000 seniors), une population suffisamment large (498 000 seniors), et **aucun des problèmes de comparabilité ou d'instabilité qui affectent les deux zones belges**. Son PIB/hab. de 34 900 € est modeste mais c'est le moins décisif des trois critères.

Le **Brabant wallon** est statistiquement le meilleur profil et mériterait une investigation de terrain — mais je ne le recommanderais pas sur la seule foi de ces chiffres.

**Prochaines étapes que je suggère :** (1) refaire tourner l'analyse sur la géographie NUTS 2021 ; (2) remplacer « lits totaux » par une capacité gériatrique réelle (lits de soins de longue durée + EHPAD/MRS) sur les 5 zones retenues, via les sources nationales (SAE en France, SPF Santé en Belgique) ; (3) vérifier la contrainte d'autorisation avant toute analyse financière. Si vous voulez, je peux lancer l'étape (1) ou explorer les zones NUTS3 à l'intérieur du Poitou-Charentes pour identifier les sous-territoires les plus tendus.


