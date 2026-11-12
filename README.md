# Benchmark énergétique d'algorithmes de tri

Projet de développement soutenable, M1 CNS Systèmes et Réseaux (SR).
**UNIVERSITE D'EVRY PARIS SACLAY** · Année universitaire 2026-2027

## Équipe

- Meziane Nouali
- Katia Yahmi
- Said Guermour
- Thomas Galinier

## Objectif

Comparer plusieurs algorithmes de tri en mesurant leur **temps d'exécution**, leur **consommation de mémoire** et leur **énergie**, afin de voir quel est le coût réel du choix d'un algorithme et quels compromis il implique.

Le projet s'appuie sur l'article de Pereira et al. (2017), _Energy Efficiency across Programming Languages_, qui compare des langages de programmation. Notre démarche est la même, appliquée à des algorithmes de tri en Python, avec la mémoire comme indicateur supplémentaire.

## Lien avec le numérique soutenable

Un code plus efficace consomme moins d'électricité à chaque exécution, sans changer de matériel. Ce projet mesure cet écart et discute ses limites, notamment l'effet rebond (un code plus rapide peut être lancé plus souvent).

## Algorithmes comparés

| Algorithme                     | Complexité moyenne |
| ------------------------------ | ------------------ |
| Tri à bulles                   | O(n²)              |
| Tri par insertion              | O(n²)              |
| Tri fusion                     | O(n log n)         |
| Tri rapide                     | O(n log n)         |
| `sorted()` de Python (Timsort) | O(n log n)         |

## Méthode

- Tableaux d'entiers aléatoires, tailles n = 500, 1000, 2000, 4000 (graine fixée pour la reproductibilité).
- 5 répétitions par mesure, la **médiane** est retenue.
- **Temps** : `time.perf_counter`.
- **Mémoire** : pic mesuré avec `tracemalloc`, dans une exécution séparée (cet outil ralentit le code).
- **Énergie** :
  - si RAPL est lisible (Linux, processeur Intel ou AMD) : mesure réelle en joules ;
  - sinon : **estimation** = temps × puissance supposée (15 W par défaut, modifiable dans le script). Le script indique au lancement quel mode est utilisé.

## Installation et utilisation

```bash
pip install -r requirements.txt
python benchmark_energie.py
```

Pour une vraie mesure d'énergie sous Linux :

```bash
sudo python benchmark_energie.py
```

Conditions recommandées : machine branchée sur secteur, applications inutiles fermées, mode économie d'énergie désactivé.

## Fichiers

| Fichier                   | Rôle                                       |
| ------------------------- | ------------------------------------------ |
| `benchmark_energie.py`    | Script de mesure et de tracé               |
| `requirements.txt`        | Dépendances Python                         |
| `resultats_benchmark.csv` | Résultats bruts (généré)                   |
| `graphique_benchmark.png` | Temps, énergie et mémoire selon n (généré) |

## Limites

- Énergie estimée et non mesurée si RAPL est indisponible.
- Une seule machine, un seul langage, des données aléatoires uniquement.
- Le gain réel dépend de la fréquence d'utilisation de l'algorithme.
- Résultats non transposables tels quels à une autre machine.

## Pistes d'amélioration

- Tester des données triées, inversées et presque triées.
- Soustraire la consommation de la machine au repos.
- Comparer avec CodeCarbon.
- Ajouter un second langage (C ou Java), pour rejoindre la comparaison de Pereira et al.

## Références

- Pereira R., Couto M., Ribeiro F., Rua R., Cunha J., Fernandes J. P., Saraiva J. (2017). _Energy Efficiency across Programming Languages: How Do Energy, Time, and Memory Relate?_ SLE '17, ACM. https://doi.org/10.1145/3136014.3136031
- Henderson P. et al. (2020). _Towards the Systematic Reporting of the Energy and Carbon Footprints of Machine Learning._
- Documentation CodeCarbon et RAPL (Intel).
