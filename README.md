# Coût énergétique des algorithmes de tri : temps, énergie, mémoire

Projet informatique : mesure et comparaison de cinq tris — bulles, insertion, fusion, rapide et `sorted()` de Python (Timsort) — selon trois indicateurs (temps, énergie, mémoire), quatre types de données (aléatoires, triées, inversées, presque triées) et quatre tailles (`n = 500` à `4 000`).

Les quatre tris écrits en Python pur sont comparés entre eux. `sorted()` (implémenté en C) est présenté séparément comme référence. Le tri à bulles sert de référence « naïve ».

## Reproduire les résultats

```bash
pip install -r requirements.txt
python benchmark_energie.py
python analyse_resultats.py
python graphiques.py
python impact.py --colonne energie_nette_J
```

- `benchmark_energie.py` réalise les mesures (environ 30 minutes selon la machine) et produit `data/resultats_benchmark.csv` et `data/metadonnees.json`.
- `analyse_resultats.py` produit les analyses dans `results/`.
- `graphiques.py` produit les figures dans `figures/`.
- `impact.py` extrapole les émissions à partir de l'énergie nette et produit `results/impact.csv` et `figures/impact_emissions.png`.

Le dossier `data/` contient les mesures utilisées pour les résultats présentés ici. Les trois dernières commandes peuvent être relancées sans refaire le benchmark. **Après chaque modification de `data/resultats_benchmark.csv`, relancer les trois dernières commandes dans cet ordre.** Pour obtenir de nouvelles mesures, relancer d'abord le benchmark, puis les trois scripts d'analyse.

## Mesure de l'énergie selon le système

Le benchmark sélectionne une source d'énergie selon le système :

- **Linux** : compteur RAPL (`/sys/class/powercap/intel-rapl:0`). L'accès peut nécessiter des droits élevés selon la configuration.
- **Windows** : compteur « Energy Meter » / compteur d'énergie Windows, lu par `rapl_windows.py`. La présence du compteur peut être vérifiée avec `typeperf -qx | Select-String RAPL`. L'unité du compteur est convertie en joules avec le facteur prévu par le programme ; le script `py diagnostic_windows.py` permet de contrôler cette conversion sur la machine utilisée.
- **Autre cas** (par exemple macOS ou absence de compteur compatible) : estimation à partir d'une puissance supposée multipliée par la durée. Dans ce cas, `energie_mesuree = False` : il s'agit d'une estimation et non d'une mesure directe.

Pour limiter les perturbations, brancher l'ordinateur sur secteur, fermer les applications non nécessaires et éviter toute interaction pendant le benchmark. Le programme mesure d'abord la puissance au repos. Une activité de fond variable peut affecter l'estimation de l'énergie nette.

## Protocole de mesure

- **Temps et énergie** : chaque mesure répète le tri pendant au moins une seconde, puis ramène le résultat à une exécution. Cette répétition permet de mieux exploiter la résolution du compteur pour les tris très courts. La médiane de 10 mesures est retenue par instance de données ; trois instances sont utilisées pour les jeux aléatoires et presque triés. Une exécution de chauffe précède la mesure et le ramasse-miettes est désactivé pendant celle-ci.
- **Énergie brute** (`energie_J`) : énergie mesurée pour le package CPU pendant l'exécution, incluant sa consommation de base.
- **Énergie nette** (`energie_nette_J`) : estimation du surplus d'énergie associé au tri, calculée par soustraction de l'énergie correspondant à la puissance au repos multipliée par la durée :

  `E_nette = E_brute - (P_repos × durée)`

  Cette estimation suppose que la puissance de fond reste relativement stable. Elle est plus sensible au bruit que l'énergie brute, car elle résulte de la différence entre deux valeurs proches ; elle doit être interprétée comme un ordre de grandeur, surtout pour les tris très rapides.

- **Mémoire** : pic d'allocation Python mesuré avec `tracemalloc`, séparément du chronométrage (car cet outil ralentit l'exécution). La mesure est effectuée une fois par combinaison. Elle porte sur les allocations Python suivies par `tracemalloc` — notamment les listes et listes intermédiaires — et non sur la mémoire physique totale du processus.
- **Données** : les instances sont générées avec des graines fixées afin de rendre les jeux de données reproductibles.

## Conditions du jeu de données fourni

- Machine : AMD Ryzen 7 5800X (AMD64 Family 25 Model 33 Stepping 2), 48 Go de RAM DDR4-3200.
- Système : Windows 11.
- Python : 3.13.14.
- Source d'énergie : compteur d'énergie Windows (Energy Meter / RAPL, package CPU).
- Puissance au repos mesurée pour ce jeu de données : **51,05 W**, pendant 10 secondes.
- Un seul benchmark complet est conservé. La date et les paramètres exacts figurent dans `data/metadonnees.json`.

La valeur de 51,05 W est propre à cette exécution et à l'état de la machine au moment de la mesure ; elle ne doit pas être considérée comme une constante valable sur une autre machine ou à un autre moment.

## Lien avec l'article de référence

Le projet reprend la démarche de Pereira et al., _Energy Efficiency across Programming Languages: How Do Energy, Time, and Memory Relate?_ (SLE 2017) : mesure de l'énergie par RAPL, répétitions, mesure du temps et de la mémoire, normalisation par rapport au meilleur résultat et analyse des ensembles de Pareto. La démarche est ici appliquée à des **algorithmes de tri**, et non à une comparaison de langages.

| Point                | Article                                 | Ce projet                                                                                                                                                                    |
| -------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Énergie              | RAPL, CPU + DRAM, processus entier      | Compteur d'énergie du package CPU                                                                                                                                            |
| Objet comparé        | Langages et environnements d'exécution  | Algorithmes de tri, principalement dans un même langage                                                                                                                      |
| Pareto énergie/temps | Analyse des compromis entre indicateurs | Le classement énergie/temps des quatre tris Python est identique dans les 16 combinaisons type de données × taille                                                           |
| Mémoire              | Mesure du pic mémoire                   | Pic des allocations Python suivi par `tracemalloc` ; l'énergie DRAM n'est pas mesurée                                                                                        |
| Compilé / interprété | Comparaison de langages                 | `sorted()` est implémenté en C, tandis que les quatre autres tris sont écrits en Python ; cette comparaison est donc indicative et ne compare pas uniquement les algorithmes |

Les résultats ne sont pas directement interchangeables avec ceux de l'article : les périmètres de mesure, les programmes et les environnements sont différents.

## Résultats principaux du dernier CSV

Les valeurs ci-dessous concernent `n = 4 000`. Les énergies nettes sont calculées avec la puissance au repos de **51,05 W** enregistrée dans les métadonnées.

### Classement énergétique selon les données

| Type de données | Tri Python pur le moins énergivore | Énergie nette par tri |
| --------------- | ---------------------------------- | --------------------: |
| Aléatoires      | Rapide                             |             0,02341 J |
| Inversées       | Fusion                             |            0,007434 J |
| Presque triées  | Rapide                             |            0,007977 J |
| Déjà triées     | Insertion                          |            0,000604 J |

`sorted()` est le moins énergivore des cinq algorithmes dans les quatre types de données mesurés. Il reste présenté à part, car il est implémenté en C.

### Comparaison sur données aléatoires

| Algorithme           | Énergie brute par tri | Énergie nette par tri | Mémoire de pointe |
| -------------------- | --------------------: | --------------------: | ----------------: |
| Bulles               |              28,539 J |               2,665 J |          31,51 Ko |
| Insertion            |              13,651 J |               1,350 J |          31,39 Ko |
| Fusion               |               0,343 J |             0,04962 J |         126,06 Ko |
| Rapide               |               0,260 J |             0,02341 J |          90,30 Ko |
| `sorted()` (Timsort) |             0,01305 J |            0,000832 J |          46,82 Ko |

Sur ces données, le tri à bulles consomme environ **110 fois** plus d'énergie brute et **114 fois** plus d'énergie nette que le tri rapide. `sorted()` consomme environ **20 fois moins d'énergie brute** que le tri rapide.

### Temps, énergie et mémoire

Pour les quatre tris Python pur, le classement selon le temps et selon l'énergie brute est identique dans les 16 combinaisons de type de données et de taille du CSV. Sur cette charge de travail, le temps et l'énergie brute sont donc fortement liés ; ils ne constituent pas deux critères indépendants dans les classements observés.

Le compromis apparaît notamment avec la mémoire : sur données aléatoires à `n = 4 000`, fusion et rapide utilisent davantage de mémoire de pointe que bulles et insertion. L'insertion présente ici la plus faible allocation mesurée parmi les quatre tris Python pur, mais son avantage mémoire sur le tri à bulles est très faible (environ 0,13 Ko).

Les pentes log-log du temps décrivent le comportement observé sur les tailles testées ; elles ne constituent pas une preuve de complexité asymptotique. Les tailles étudiées restent modestes (`n ≤ 4 000`).

## Lien avec le développement soutenable et émissions estimées

L'énergie d'un tri isolé est faible. Pour illustrer l'effet d'un usage répété, `impact.py` extrapole les mesures à un scénario **hypothétique** d'un million de tris de 4 000 éléments par jour pendant 365 jours.

Les émissions sont calculées à partir de l'énergie nette par tri :

`CO₂e (g/an) = [E_nette (J) × nombre annuel de tris / 3 600 000] × intensité carbone (gCO₂e/kWh)`

Deux intensités carbone sont utilisées dans le scénario :

- **19,6 gCO₂e/kWh** : valeur attribuée au bilan électrique RTE 2025 dans le projet ;
- **51,9 gCO₂e/kWh** : valeur attribuée à la Base Carbone de l'ADEME dans le projet.

| Algorithme           | Énergie nette par tri | Émissions annuelles estimées |
| -------------------- | --------------------: | ---------------------------: |
| Bulles               |               2,665 J |         5,30 à 14,02 kg CO₂e |
| Insertion            |               1,350 J |          2,68 à 7,10 kg CO₂e |
| Fusion               |             0,04962 J |            98,6 à 261 g CO₂e |
| Rapide               |             0,02341 J |            46,5 à 123 g CO₂e |
| `sorted()` (Timsort) |            0,000832 J |           1,65 à 4,38 g CO₂e |

Ces résultats sont des extrapolations, pas des émissions directement mesurées. Ils ne représentent que l'énergie du package CPU mesurée par le compteur, et non l'empreinte environnementale complète de l'ordinateur ou du service numérique.

**Effet rebond :** un gain d'énergie par opération peut être annulé si le nombre d'opérations augmente suffisamment. À titre d'exemple, le rapport d'environ 114 entre l'énergie nette du tri à bulles et celle du tri rapide sur données aléatoires indique qu'il faudrait multiplier le nombre de tris rapides par environ 114 pour atteindre la même énergie nette totale, dans les hypothèses de ce benchmark. Ce scénario ne prédit pas un comportement réel des utilisateurs.

## Pourquoi les valeurs peuvent-elles varier ?

- **Énergie brute ou nette** : l'énergie brute inclut la consommation du package CPU pendant le tri ; l'énergie nette retire l'estimation de la consommation au repos. Elles répondent à deux questions différentes.
- **Puissance au repos** : elle est mesurée avant le benchmark et dépend de l'état de la machine, des processus en arrière-plan, du mode d'alimentation et de la température. La valeur de 51,05 W n'est pas une constante universelle.
- **Puissance moyenne pendant le tri** : elle varie selon l'algorithme et la durée. Le rapport énergie/durée fournit une puissance moyenne sur la période mesurée, pas une puissance instantanée.
- **Données et taille** : les chemins d'exécution changent selon que la liste est aléatoire, triée, inversée ou presque triée. Les comparaisons doivent porter sur le même type de données et le même `n`.
- **Machine, système et Python** : le processeur, le système d'exploitation, la version de Python et l'état du système peuvent modifier les résultats.
- **Compteur Windows** : les résultats dépendent de la résolution et de l'échantillonnage du compteur ainsi que de la conversion de son unité. Le diagnostic de l'unité réduit le risque d'erreur de conversion, mais ne supprime pas les incertitudes de mesure.
- **`sorted()`** : cette fonction est implémentée en C et ses durées sont très courtes. Son énergie par tri est donc particulièrement sensible à la résolution du compteur et au protocole de répétition. Elle sert de référence distincte, et non de comparaison entre deux implémentations écrites dans le même langage.

## Limites

- Les résultats présentés proviennent d'un seul benchmark complet sur une seule machine, sous Windows, avec une seule version de Python. Ils ne démontrent pas à eux seuls la reproductibilité sur d'autres machines.
- Sur AMD, la valeur fournie par le compteur d'énergie est une estimation du package CPU ; ce n'est pas une mesure de la consommation électrique à la prise.
- La mesure ne couvre pas la RAM, le refroidissement, l'alimentation, l'écran, les périphériques, la fabrication du matériel ni l'infrastructure d'un centre de données.
- La mesure de la puissance au repos est réalisée une seule fois avant les essais. Les variations de l'activité en arrière-plan peuvent donc affecter l'énergie nette, surtout pour les algorithmes très rapides.
- `tracemalloc` mesure les allocations Python suivies par cet outil, pas toute la mémoire physique du processus.
- Les tailles testées sont modestes (`n ≤ 4 000`) ; les résultats ne doivent pas être extrapolés sans précaution à de très grands tableaux.
- Le scénario d'émissions est hypothétique. Les intensités carbone dépendent de leur source, de leur année et de leur périmètre (émissions directes ou cycle de vie).

## Structure du projet

```text
benchmark_energie.py     mesures (temps, énergie, mémoire)
rapl_windows.py          lecture du compteur d'énergie sous Windows
diagnostic_windows.py    vérification de l'unité du compteur Windows
analyse_resultats.py     normalisation, dispersion, puissance, pentes, Pareto
graphiques.py             figures
impact.py                 extrapolation, émissions, effet rebond
requirements.txt          dépendances (pandas, numpy, matplotlib)
data/                     résultats bruts (CSV + métadonnées)
results/                  tableaux d'analyse
figures/                  figures pour le poster
```

## Sources

- R. Pereira, M. Couto, F. Ribeiro, R. Rua, J. Cunha, J. P. Fernandes et J. Saraiva, _Energy Efficiency across Programming Languages: How Do Energy, Time, and Memory Relate?_, SLE 2017, DOI : [10.1145/3136014.3136031](https://doi.org/10.1145/3136014.3136031).
- RTE, _Bilan électrique 2025_ (valeur d'intensité carbone utilisée dans le projet : 19,6 gCO₂e/kWh).
- ADEME, _Base Carbone_ (valeur d'intensité carbone utilisée dans le projet : 51,9 gCO₂e/kWh).
- Documentation Linux `powercap` / Intel RAPL.
- Documentation Python : `tracemalloc` et `sorted()` / Timsort.
