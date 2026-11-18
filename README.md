# Coût énergétique des algorithmes de tri : temps, énergie, mémoire

Projet informatique : mesure et comparaison de cinq tris (bulles, insertion, fusion, rapide, `sorted` de Python/Timsort)
selon trois indicateurs (temps, énergie, mémoire), quatre types de données (aléatoires, triées, inversées, presque triées)
et quatre tailles (n = 500 à 4000). Les quatre tris écrits en Python pur sont comparés entre eux ; `sorted` (écrit en C)
sert de référence à part. La situation de référence « naïve » est le tri à bulles.

## Reproduire les résultats

```bash
pip install -r requirements.txt
python benchmark_energie.py             # mesures (environ 30 min) -> data/resultats_benchmark.csv + data/metadonnees.json
python analyse_resultats.py             # normalisation, Pareto, pentes -> results/
python graphiques.py                    # figures/benchmark_*.png, figures/synthese_energie_memoire.png
python impact.py --colonne energie_nette_J    # extrapolation à un usage réel -> results/impact.csv, figures/impact_emissions.png
```

Le dossier `data/` contient les mesures qui ont servi aux résultats ci-dessous : les trois dernières commandes
s'exécutent sans refaire le benchmark et sans droits particuliers. **À chaque changement de `data/resultats_benchmark.csv`,
relancer ces trois commandes dans cet ordre.**

### Mesure de l'énergie selon le système

Le benchmark détecte le système tout seul :

- **Linux** : compteur RAPL (`/sys/class/powercap/intel-rapl:0`). Lancer avec `sudo` (lecture réservée à root).
- **Windows** : compteur « Energy Meter » (sur un Windows en français : « Compteur Énergie »), lu par `rapl_windows.py`.
  Vérification : `typeperf -qx | Select-String RAPL` doit afficher `RAPL_Package0_PKG`. L'unité du compteur est supposée
  être le picowatt-heure ; `py diagnostic_windows.py` (facultatif, environ 15 s) la vérifie sur une autre machine.
- **Autre cas** (macOS, compteur absent) : estimation (puissance supposée x temps), colonne `energie_mesuree = False`.
  Ce n'est plus une mesure et il faut le signaler.

Pendant les mesures : branchez le secteur, fermez **tous** les autres programmes (jeu, navigateur, antivirus en analyse),
ne touchez pas à l'ordinateur. Le benchmark mesure d'abord la puissance au repos ; si elle est trop proche de la puissance sous
charge, il l'indique (énergies nettes négatives).

## Protocole de mesure

- **Temps et énergie** : chaque mesure répète le tri pendant au moins 1 s (le compteur est trop grossier pour un seul tri de
  quelques microsecondes) et ramène le résultat à une exécution. On retient la médiane de 10 mesures par instance de données,
  avec 3 instances pour les jeux aléatoires et presque triés. Le ramasse-miettes est désactivé pendant chaque mesure, après une
  exécution de chauffe.
- **Énergie brute** (`energie_J`) : tout ce que consomme le processeur (package) pendant le tri, y compris sa consommation de base.
- **Énergie nette** (`energie_nette_J`) : énergie brute moins (puissance au repos x temps), soit le surplus dû au tri.
  Elle est moins stable que la brute (différence de deux grandeurs proches) : à lire comme un ordre de grandeur.
- **Mémoire** : pic d'allocation mesuré par `tracemalloc`, séparément du temps (l'outil ralentit le code), une seule fois par combinaison (sur la première instance de données). Cela compte les listes créées
  (copie du tableau, listes intermédiaires), pas les entiers eux-mêmes.
- **Données** : instances générées avec une graine fixée.

## Conditions de mesure du jeu de données fourni

- Machine : AMD Ryzen 7 5800X (AMD64 Family 25 Model 33 Stepping 2), 48 Go de RAM DDR4-3200, Windows 11, Python 3.13.14.
- Énergie : compteur d'énergie Windows (RAPL, package CPU). Puissance au repos mesurée : 43,7 W.
- Un seul run complet est conservé (`metadonnees.json` en donne la date et les paramètres).

## Lien avec l'article de référence

Le projet reprend la démarche de Pereira et al., *Energy Efficiency across Programming Languages* (SLE 2017) :
mesure de l'énergie par RAPL, 10 répétitions par mesure, temps et mémoire mesurés en parallèle, valeurs normalisées par rapport
au meilleur (leur Table 4) et ensembles de Pareto (leur Table 5), appliqués à des **algorithmes de tri** plutôt qu'à des langages.

| Point | Article | Ce projet |
|---|---|---|
| Énergie | RAPL, CPU + DRAM, processus entier | RAPL, package CPU, tri mesuré dans le processus |
| Temps et énergie liés ? | Pas toujours : la puissance varie d'un langage à l'autre | Oui pour des tris dans un même langage : puissance quasi constante sur nos essais (environ 62 W en brut, 18 W en net) |
| Pareto énergie/temps | Se réduit presque toujours à un élément | Même constat ; le compromis apparaît avec la mémoire |
| Mémoire | Pic mesuré par `time` ; faible corrélation avec l'énergie DRAM (Spearman 0,21) | Pic mesuré par `tracemalloc` ; énergie DRAM non mesurée |
| Compilé contre interprété | Énergie moyenne environ 20 fois plus élevée en interprété | `sorted` (C) contre tri rapide Python : environ 20 fois moins d'énergie, mais algorithmes différents, donc indicatif seulement |

Ces résultats ne se contredisent pas : l'article compare des langages (donc des runtimes différents), ici on compare des algorithmes
dans un seul langage, avec une charge de calcul pur sur un cœur.

## Résultats principaux (`data/`, `results/`)

| Constat | Valeur |
|---|---|
| Puissance moyenne observée pendant les tris | environ 62 W en brut (57 à 69 W), environ 18 W en net ; énergie ≈ puissance x temps (corrélation log-log r = 0,9999) |
| Classements énergie et temps | identiques dans 100 % des cas pour les 4 tris Python |
| Complexité observée (pente log-log du temps) | bulles ≈ 2,1 ; insertion ≈ 2,05 à 2,1 (≈ 1,05 sur données triées) ; fusion et rapide ≈ 1,1 |
| Plus économe, Python pur, n = 4000 | rapide (données aléatoires, inversées, presque triées) ; insertion (données triées) |
| Bulles contre rapide, n = 4000, données aléatoires | environ 102 fois plus d'énergie en brut (30,3 J contre 0,30 J), environ 100 fois en net |
| `sorted` contre rapide, n = 4000, données aléatoires | environ 20 fois moins d'énergie |
| Compromis mémoire (n = 4000, aléatoire) | fusion 126 Ko et rapide 90 Ko, contre 31 Ko pour bulles et insertion |
| Non dominés énergie/mémoire (n = 4000) | insertion et rapide ; insertion seul sur données triées |

Un tri plus rapide consomme donc proportionnellement moins d'énergie : sur cette charge, énergie et temps ne sont pas deux
critères indépendants. Le vrai compromis se situe entre énergie et mémoire, et dépend des données : sur données triées,
l'insertion bat le tri rapide.

## Lien avec le développement soutenable et effet rebond

L'énergie d'un seul tri est minuscule (de l'ordre de 0,1 J pour les bons algorithmes, à n = 4000), l'enjeu apparaît à l'échelle
d'un usage répété. `impact.py` extrapole à un scénario **hypothétique** (par défaut 1 million de tris par jour de 4000 éléments)
et convertit en émissions avec l'intensité carbone du réseau électrique français : 19,6 gCO₂e/kWh (RTE, émissions directes, 2025)
et 51,9 gCO₂e/kWh (ADEME, Base Carbone, cycle de vie).

| Algorithme (énergie nette) | Énergie par tri | Émissions par an |
|---|---|---|
| Bulles | 8,05 J | 16 à 42 kg CO₂e |
| Insertion | 3,82 J | 7,6 à 20 kg |
| Fusion | 0,092 J | 184 à 486 g |
| Rapide | 0,081 J | 161 à 425 g |
| `sorted` (C) | 0,0036 J | 7 à 19 g |

En énergie brute, les valeurs sont environ 3,8 fois plus élevées (par exemple environ 60 à 159 kg par an pour le tri à bulles) :
l'énergie nette est ce que le tri ajoute, la brute est une borne haute. Dans les deux cas, passer du tri à bulles au tri rapide
divise l'énergie par environ 100.

**Effet rebond** : un gain de facteur g est annulé si l'usage est multiplié par g ou plus. Le fichier `results/impact.csv` donne ce
seuil pour chaque algorithme (environ 100 pour le tri rapide contre le tri à bulles). Un tri plus économe peut aussi encourager à
trier plus souvent ou de plus grands volumes. Ces valeurs absolues sont très faibles à l'échelle du numérique : l'intérêt du
résultat est surtout de montrer l'écart entre algorithmes, pas un gain climatique à lui seul.

## Limites

- Tous les résultats viennent d'un seul run sous Windows ; la lecture RAPL sous Linux est prévue par le code mais n'a pas été validée sur ces mesures. Une seule machine, un seul système, une seule version de Python ; un seul run conservé : la reproductibilité n'est pas démontrée
  par ce dépôt (le bruit de mesure est donné par les écarts-types du CSV, 8 à 9 % en moyenne sur l'énergie, jusqu'à 20 %).
- Sur AMD, RAPL est une estimation interne du processeur, pas une mesure physique à la prise.
- Énergie du processeur seulement : pas de RAM, de refroidissement, de pertes de centre de données ni de fabrication du matériel.
- Mesures sous Windows, donc sensibles à l'activité de fond : la médiane limite l'effet, mais les petits écarts (par exemple entre
  fusion et rapide) ne sont pas significatifs.
- Les mesures de `sorted` durent quelques microsecondes : elles sont les plus sensibles au bruit, et sa pente log-log (1,57 sur
  données aléatoires) ne doit pas être lue comme une complexité.
- Tailles testées modestes (n <= 4000) ; les écarts entre complexités s'accentuent avec n.
- Le tri `sorted` est écrit en C : l'écart avec les tris Python est surtout un effet du langage, il est donc isolé de l'analyse.
- Le scénario d'extrapolation est une hypothèse de travail, et les intensités carbone dépendent du périmètre retenu et de l'année.

## Structure

```
benchmark_energie.py     mesures (temps, énergie, mémoire)
rapl_windows.py          lecture du compteur d'énergie sous Windows
diagnostic_windows.py    vérification de l'unité du compteur Windows (facultatif)
analyse_resultats.py     normalisation, dispersion, puissance, pentes, Pareto
graphiques.py            figures
impact.py                extrapolation, émissions, effet rebond
requirements.txt         dépendances (pandas, numpy, matplotlib)
data/                    résultats bruts (CSV + métadonnées)
results/                 tableaux d'analyse
figures/                 graphiques pour le poster
```

## Sources

- R. Pereira, M. Couto, F. Ribeiro, R. Rua, J. Cunha, J. P. Fernandes, J. Saraiva, *Energy Efficiency across Programming Languages: How Do Energy, Time, and Memory Relate?*, SLE 2017, doi:10.1145/3136014.3136031.
- RTE, Bilan électrique 2025 (intensité carbone de la production : 19,6 gCO₂e/kWh).
- ADEME, Base Carbone (électricité, mix de consommation : 51,9 gCO₂e/kWh).
- Documentation Linux `powercap` / Intel RAPL ; documentation Python (`tracemalloc`, `sorted`/Timsort).