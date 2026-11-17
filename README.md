# Coût énergétique des algorithmes de tri : temps, énergie, mémoire

Projet informatique : mesure et comparaison de cinq tris (bulles, insertion, fusion, rapide, `sorted` de Python/Timsort)
selon trois indicateurs (temps, énergie, mémoire), quatre types de données (aléatoires, triées, inversées, presque triées)
et quatre tailles (n = 500 à 4000). Les tris en Python pur sont comparés entre eux ; `sorted` (écrit en C) sert de référence à part.

## Reproduire les résultats

```bash
pip install -r requirements.txt
sudo python benchmark_energie.py        # mesure (environ 30 min) -> data/resultats_benchmark.csv + data/metadonnees.json
python analyse_resultats.py             # normalisation, Pareto, pentes -> results/
python graphiques.py                    # figures/benchmark_*.png, figures/synthese_energie_memoire.png
python impact.py                        # extrapolation à un usage réel -> results/impact.csv, figures/impact_emissions.png
```

### Sous Windows

Windows expose le compteur RAPL sous le nom « Energy Meter » (sur un Windows en français : « Compteur Énergie »).
Vérification : `typeperf -qx | Select-String RAPL` doit afficher `RAPL_Package0_PKG`. Puis :

```powershell
py -m pip install -r requirements.txt
py diagnostic_windows.py                              # détecte l'unité du compteur (environ 15 s, ne touchez à rien)
py benchmark_energie.py --facteur-joules <valeur>     # valeur affichée par le diagnostic
```

Pendant les mesures : branchez le secteur, fermez les autres programmes, désactivez l'économiseur de batterie.
Sans compteur disponible, le benchmark bascule sur une estimation (`energie_mesuree = False`) : à signaler sur le poster.

Le dossier `data/` contient les mesures du protocole initial (une instance par jeu de données, énergie brute RAPL). Pour le rendu final, relancer le benchmark : il produit en plus `energie_nette_J` et `metadonnees.json` (à joindre). Les trois derniers scripts s'exécutent sans droits
particuliers à partir de ce CSV. Seul le benchmark a besoin de `sudo` (lecture du compteur RAPL sous Linux) ;
sans RAPL, l'énergie est estimée (puissance supposée x temps) et la colonne `energie_mesuree` vaut `False`.

Les graines des jeux de données sont fixées, la mesure de temps et d'énergie reste soumise au bruit de la machine :
l'écart-type est fourni pour chaque point.

## Protocole de mesure

- **Temps et énergie** : chaque mesure répète le tri pendant au moins 1 s (le compteur RAPL est trop grossier pour un seul tri de
  quelques microsecondes) et ramène le résultat à une exécution. On retient la médiane de 10 mesures par instance.
- **Énergie** : compteur RAPL (énergie du « package » CPU, en joules). Une puissance de repos est mesurée au départ ;
  si disponible, la colonne `energie_nette_J` retire cette consommation de base.
- **Mémoire** : pic mesuré par `tracemalloc`, séparément du temps (l'outil ralentit le code). Cela compte les listes créées
  (copie du tableau, listes intermédiaires), pas les entiers eux-mêmes.
- **Données** : instances générées avec une graine fixée ; plusieurs instances pour les jeux aléatoires et presque triés.
- Le ramasse-miettes est désactivé pendant chaque mesure, après une exécution de chauffe.

## Lien avec l'article de référence

Le projet reprend la démarche de Pereira et al., *Energy Efficiency across Programming Languages* (SLE 2017) :
mesure de l'énergie par RAPL, 10 répétitions par mesure, temps et mémoire mesurés en parallèle, valeurs normalisées par rapport
au meilleur (comme leur Table 4) et ensembles de Pareto (leur Table 5), le tout appliqué à des **algorithmes de tri** plutôt qu'à des langages.

| Point | Article | Ce projet |
|---|---|---|
| Énergie | RAPL, CPU + DRAM, processus entier | RAPL, package CPU, tri mesuré dans le processus |
| Temps et énergie liés ? | Non pas toujours : la puissance varie d'un langage à l'autre | Oui pour des tris dans un même langage : puissance quasi constante (environ 7,2 W) |
| Pareto énergie/temps | Se réduit presque toujours à un élément | Même constat ; le compromis apparaît avec la mémoire |
| Mémoire | Pic mesuré par `time` ; faible corrélation avec l'énergie DRAM (Spearman 0,21) | Pic mesuré par `tracemalloc` ; énergie DRAM non mesurée |
| Compilé contre interprété | Énergie moyenne environ 20 fois plus élevée en interprété | `sorted` (C) contre tri rapide Python : environ 14 fois moins d'énergie, mais algorithmes différents, donc indicatif seulement |

Ces deux résultats ne se contredisent pas : l'article compare des langages (donc des runtimes différents), ici on compare des algorithmes
dans un seul langage, avec une charge de calcul pur sur un cœur.

## Résultats principaux (mesures du dossier `data/`)

| Constat | Valeur |
|---|---|
| Puissance moyenne pendant les tris | environ 7,2 W, quasi constante : **énergie ≈ puissance x temps** (corrélation log-log r = 0,9997) |
| Classements énergie et temps | identiques dans 100 % des cas pour les 4 tris Python |
| Complexité observée (pente log-log du temps) | bulles ≈ 2,1 ; insertion ≈ 2,05 (≈ 1,07 sur données triées) ; fusion et rapide ≈ 1,1 |
| Plus économe, Python pur, n = 4000 | rapide (données aléatoires, inversées, presque triées) ; insertion (données triées) |
| Bulles contre rapide, n = 4000, données aléatoires | environ 118 fois plus d'énergie |
| Compromis mémoire (n = 4000) | fusion et rapide utilisent jusqu'à environ 4 fois plus de mémoire que bulles et insertion (126 Ko contre 31 Ko) |
| Non dominés énergie/mémoire (n = 4000) | insertion et rapide ; insertion seul sur données triées |

Un tri plus rapide consomme donc proportionnellement moins d'énergie : sur cette charge, énergie et temps ne sont pas deux
critères indépendants. Le vrai compromis se situe entre énergie et mémoire.

## Lien avec le développement soutenable et effet rebond

L'énergie d'un seul tri est minuscule (de l'ordre du millijoule pour les bons algorithmes), l'enjeu apparaît à l'échelle d'un
usage répété. `impact.py` extrapole à un scénario **hypothétique** (par défaut 1 million de tris par jour de 4000 éléments)
et convertit en émissions avec l'intensité carbone du réseau électrique français : 19,6 gCO₂e/kWh (RTE, émissions directes, 2025)
et 51,9 gCO₂e/kWh (ADEME, Base Carbone, cycle de vie). Dans ce scénario, passer du tri à bulles au tri rapide divise
l'énergie par environ 118.

**Effet rebond** : un gain de facteur g est annulé si l'usage est multiplié par g ou plus. Le fichier `results/impact.csv`
donne ce seuil pour chaque algorithme. Un tri plus économe peut aussi encourager à trier plus souvent ou de plus grands
volumes.

## Limites

- Une seule machine, un seul système, une seule version de Python (`metadonnees.json`, écrit par le benchmark) ; à compléter : **matériel exact**.
- Énergie du processeur seulement : pas de RAM, de refroidissement, de pertes de centre de données ni de fabrication du matériel.
- Tailles testées modestes (n <= 4000) ; les écarts entre complexités s'accentuent avec n.
- Le tri `sorted` est écrit en C : l'écart avec les tris Python est surtout un effet du langage, il est donc isolé de l'analyse.
- Le scénario d'extrapolation est une hypothèse de travail.
- Les valeurs d'intensité carbone dépendent du périmètre retenu (émissions directes ou cycle de vie) et de l'année.

## Structure

```
benchmark_energie.py     mesures (temps, énergie, mémoire)
rapl_windows.py          lecture du compteur d'énergie sous Windows
diagnostic_windows.py    unité et finesse du compteur Windows (à lancer avant le benchmark)
analyse_resultats.py     normalisation, dispersion, puissance, pentes, Pareto
graphiques.py            figures
impact.py                extrapolation, émissions, effet rebond
data/                    résultats bruts
results/                 tableaux d'analyse
figures/                 graphiques pour le poster
```

## Sources

- R. Pereira, M. Couto, F. Ribeiro, R. Rua, J. Cunha, J. P. Fernandes, J. Saraiva, *Energy Efficiency across Programming Languages: How Do Energy, Time, and Memory Relate?*, SLE 2017, doi:10.1145/3136014.3136031.
- RTE, Bilan électrique 2025 (intensité carbone de la production : 19,6 gCO₂e/kWh).
- ADEME, Base Carbone (électricité, mix de consommation : 51,9 gCO₂e/kWh).
- Documentation Linux `powercap` / Intel RAPL ; documentation Python (`tracemalloc`, `sorted`/Timsort).
