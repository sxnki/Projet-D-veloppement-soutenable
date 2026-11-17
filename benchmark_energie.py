"""
Benchmark énergétique d'algorithmes de tri : temps, mémoire, énergie.

Usage :
    python benchmark_energie.py                       # protocole complet
    sudo python benchmark_energie.py                  # souvent nécessaire pour lire RAPL (Linux)
    python benchmark_energie.py --tailles 500 1000 --repetitions 3 --duree-min 0.2   # test rapide

Énergie :
- Windows : compteur « Energy Meter » (voir rapl_windows.py) : lancer d'abord diagnostic_windows.py,
  puis  py benchmark_energie.py --facteur-joules <valeur donnée par le diagnostic>
- Si RAPL est lisible (Linux, Intel/AMD) : mesure réelle en joules (énergie du « package » CPU).
  Une puissance de repos est mesurée au départ, ce qui permet de donner aussi une énergie NETTE
  (énergie brute - puissance de repos x temps) en plus de l'énergie brute.
- Sinon : ESTIMATION = temps x PUISSANCE_ESTIMEE_W (colonne energie_mesuree = False).
  À signaler explicitement si les résultats sont présentés.

Sorties (dans --sortie) :
- resultats_benchmark.csv   une ligne par (type de données, algo, n)
- metadonnees.json          machine, version de Python, paramètres, puissance de repos
"""
import argparse
import gc
import json
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from datetime import datetime

import pandas as pd

RAPL = "/sys/class/powercap/intel-rapl:0/energy_uj"
RAPL_MAX = "/sys/class/powercap/intel-rapl:0/max_energy_range_uj"

TYPES_DONNEES = ["aleatoire", "trie", "inverse", "presque_trie"]
TYPES_ALEATOIRES = {"aleatoire", "presque_trie"}   # plusieurs instances (graines) pour ceux-là


# ---------- Algorithmes ----------
def tri_bulles(a):
    a = a[:]
    n = len(a)
    for i in range(n):
        for j in range(n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a


def tri_insertion(a):
    a = a[:]
    for i in range(1, len(a)):
        cle, j = a[i], i - 1
        while j >= 0 and a[j] > cle:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = cle
    return a


def tri_fusion(a):
    if len(a) <= 1:
        return a[:]
    m = len(a) // 2
    g, d = tri_fusion(a[:m]), tri_fusion(a[m:])
    res, i, j = [], 0, 0
    while i < len(g) and j < len(d):
        if g[i] <= d[j]:
            res.append(g[i]); i += 1
        else:
            res.append(d[j]); j += 1
    return res + g[i:] + d[j:]


def tri_rapide(a):
    if len(a) <= 1:
        return a[:]
    pivot = a[len(a) // 2]
    return (tri_rapide([x for x in a if x < pivot])
            + [x for x in a if x == pivot]
            + tri_rapide([x for x in a if x > pivot]))


def tri_python(a):
    return sorted(a)


ALGOS = {
    "bulles": tri_bulles,
    "insertion": tri_insertion,
    "fusion": tri_fusion,
    "rapide": tri_rapide,
    "sorted (Timsort)": tri_python,   # écrit en C : à analyser à part des tris Python
}


# ---------- Mesures ----------
class SourceRapl:
    """Compteur RAPL sous Linux : énergie cumulée du package CPU, en joules."""
    nom = "RAPL (Linux, powercap)"

    def __init__(self):
        with open(RAPL) as f:
            int(f.read())                      # lève une exception si le compteur est illisible
        with open(RAPL_MAX) as f:
            self.max_j = int(f.read()) / 1e6

    def lire(self):
        with open(RAPL) as f:
            return int(f.read()) / 1e6

    def delta(self, e0, e1):
        return e1 - e0 if e1 >= e0 else e1 + self.max_j - e0   # le compteur a pu déborder


def creer_source(facteur_joules, chemin_windows):
    """Retourne une source d'énergie réelle (Linux RAPL, ou compteur Windows), ou None (=> estimation)."""
    try:
        return SourceRapl()
    except (OSError, ValueError):
        pass
    if platform.system() == "Windows":
        if facteur_joules is None:
            print("Windows : compteur d'énergie non utilisé car --facteur-joules n'est pas donné.\n"
                  "          Lancez d'abord :  py diagnostic_windows.py")
            return None
        try:
            from rapl_windows import SourceWindows
            return SourceWindows(facteur_joules, chemin_windows)
        except Exception as exc:
            print(f"Windows : compteur d'énergie indisponible ({exc}).")
    return None


def puissance_repos(source, duree_s):
    """Puissance du package au repos (W) : moyenne sur duree_s secondes sans charge."""
    e0, t0 = source.lire(), time.perf_counter()
    time.sleep(duree_s)
    e1, t1 = source.lire(), time.perf_counter()
    return source.delta(e0, e1) / (t1 - t0)


def mesurer(fonction, donnees, source, duree_min, p_estimee):
    """UNE mesure : on répète le tri pendant >= duree_min secondes (pour que le compteur soit
    lisible) et on retourne les valeurs pour UNE exécution moyenne : (temps_s, energie_J)."""
    gc.collect()
    gc.disable()                  # évite qu'un passage du ramasse-miettes tombe au milieu d'une mesure
    try:
        e0 = source.lire() if source else None
        n_exec = 0
        t0 = time.perf_counter()
        while True:
            fonction(donnees)
            n_exec += 1
            t = time.perf_counter() - t0
            if t >= duree_min:
                break
        e1 = source.lire() if source else None
    finally:
        gc.enable()
    t_moy = t / n_exec
    if source:
        return t_moy, source.delta(e0, e1) / n_exec
    return t_moy, t_moy * p_estimee


def memoire_pic(fonction, donnees):
    """Mesure séparée : tracemalloc ralentit le code, on ne la mêle pas au temps.
    Compte les listes créées (copie du tableau, listes intermédiaires), pas les entiers eux-mêmes."""
    tracemalloc.start()
    fonction(donnees)
    _, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pic / 1024  # Ko


def generer(type_donnees, n, graine):
    """Tableau de n entiers, selon le type de données (reproductible via la graine)."""
    rng = random.Random(f"{type_donnees}-{n}-{graine}")
    a = [rng.randint(0, 10**6) for _ in range(n)]
    if type_donnees == "trie":
        a.sort()
    elif type_donnees == "inverse":
        a.sort(reverse=True)
    elif type_donnees == "presque_trie":
        a.sort()
        for _ in range(max(1, n // 20)):      # ~5 % d'éléments déplacés
            i, j = rng.randrange(n), rng.randrange(n)
            a[i], a[j] = a[j], a[i]
    return a


def ecart_type(valeurs):
    """Écart-type, 0 s'il n'y a qu'une seule valeur (statistics.stdev lève une erreur dans ce cas)."""
    valeurs = list(valeurs)
    return statistics.stdev(valeurs) if len(valeurs) > 1 else 0.0


def modele_cpu():
    try:
        with open("/proc/cpuinfo") as f:
            for ligne in f:
                if ligne.startswith("model name"):
                    return ligne.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "inconnu"


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tailles", type=int, nargs="+", default=[500, 1000, 2000, 4000])
    p.add_argument("--repetitions", type=int, default=10, help="mesures par instance de données")
    p.add_argument("--graines", type=int, default=3,
                   help="instances différentes pour les données aléatoires / presque triées")
    p.add_argument("--duree-min", type=float, default=1.0, help="durée minimale d'une mesure (s)")
    p.add_argument("--repos-s", type=float, default=10.0, help="durée de la mesure de puissance au repos (s)")
    p.add_argument("--puissance-estimee", type=float, default=15.0,
                   help="puissance (W) supposée si RAPL est indisponible")
    p.add_argument("--facteur-joules", type=float, default=None,
                   help="Windows : joules par unité du compteur d'énergie (donné par diagnostic_windows.py)")
    p.add_argument("--chemin-windows", default=None,
                   help="Windows : chemin PDH du compteur d'énergie, si le chemin par défaut ne fonctionne pas")
    p.add_argument("--sortie", default="data", help="dossier de sortie")
    return p


def main():
    args = parser().parse_args()
    os.makedirs(args.sortie, exist_ok=True)

    source = creer_source(args.facteur_joules, args.chemin_windows)
    rapl = source is not None
    p_repos = None
    if rapl:
        print(f"Mesure de la puissance au repos ({args.repos_s:.0f} s, ne touchez pas à la machine)...")
        p_repos = puissance_repos(source, args.repos_s)
        print(f"Énergie : {source.nom} (mesure réelle). Puissance au repos : {p_repos:.2f} W")
    else:
        print(f"Énergie : ESTIMÉE ({args.puissance_estimee} W x temps). RAPL indisponible.")

    lignes = []
    for type_donnees in TYPES_DONNEES:
        nb_graines = args.graines if type_donnees in TYPES_ALEATOIRES else 1
        for n in args.tailles:
            instances = [generer(type_donnees, n, g) for g in range(nb_graines)]
            for nom, f in ALGOS.items():
                f(instances[0])                      # une exécution de chauffe, non mesurée
                res = [mesurer(f, d, source, args.duree_min, args.puissance_estimee)
                       for d in instances for _ in range(args.repetitions)]
                temps = [r[0] for r in res]
                energie = [r[1] for r in res]
                ligne = {
                    "donnees": type_donnees,
                    "algo": nom,
                    "n": n,
                    "temps_s": statistics.median(temps),
                    "energie_J": statistics.median(energie),
                    "memoire_Ko": memoire_pic(f, instances[0]),
                    "energie_mesuree": rapl,
                    "temps_std_s": ecart_type(temps),
                    "energie_std_J": ecart_type(energie),
                }
                if rapl:
                    nette = [e - p_repos * t for t, e in res]
                    ligne["energie_nette_J"] = statistics.median(nette)
                lignes.append(ligne)
                print(f"{type_donnees:<12} n={n:<5} {nom:<17} "
                      f"{ligne['temps_s']*1000:9.3f} ms  {ligne['energie_J']:.5f} J  "
                      f"{ligne['memoire_Ko']:.0f} Ko")

    chemin = os.path.join(args.sortie, "resultats_benchmark.csv")
    pd.DataFrame(lignes).to_csv(chemin, index=False)

    meta = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "cpu": modele_cpu(),
        "systeme": platform.platform(),
        "python": sys.version,
        "rapl": rapl,
        "source_energie": source.nom if rapl else "estimation (puissance supposée x temps)",
        "puissance_repos_W": p_repos,
        "parametres": vars(args),
    }
    with open(os.path.join(args.sortie, "metadonnees.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Fichiers : {chemin}, metadonnees.json")


if __name__ == "__main__":
    main()
