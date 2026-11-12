"""
Benchmark energetique d'algorithmes de tri : temps, memoire, energie.

Usage :
    python benchmark_energie.py
    sudo python benchmark_energie.py     # souvent necessaire pour lire RAPL (Linux)

Energie :
- Si RAPL est lisible (Linux, Intel/AMD) : mesure reelle en joules.
- Sinon : ESTIMATION = temps x PUISSANCE_ESTIMEE_W (a signaler sur le poster !).
"""
import os
import random
import statistics
import time
import tracemalloc

import matplotlib.pyplot as plt
import pandas as pd

PUISSANCE_ESTIMEE_W = 15.0   # puissance CPU supposee si RAPL indisponible
REPETITIONS = 5
TAILLES = [500, 1000, 2000, 4000]

RAPL = "/sys/class/powercap/intel-rapl:0/energy_uj"
RAPL_MAX = "/sys/class/powercap/intel-rapl:0/max_energy_range_uj"


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
    "sorted (Timsort)": tri_python,
}


# ---------- Mesures ----------
def rapl_disponible():
    try:
        with open(RAPL) as f:
            int(f.read())
        return True
    except (OSError, ValueError):
        return False


def lire_rapl():
    with open(RAPL) as f:
        return int(f.read())  # microjoules


def mesurer(fonction, donnees, rapl):
    """Retourne (temps_s, energie_J, energie_mesuree?)."""
    if rapl:
        e0 = lire_rapl()
    t0 = time.perf_counter()
    fonction(donnees)
    t = time.perf_counter() - t0
    if rapl:
        e1 = lire_rapl()
        if e1 < e0:  # le compteur a debord
            with open(RAPL_MAX) as f:
                e1 += int(f.read())
        return t, (e1 - e0) / 1e6, True
    return t, t * PUISSANCE_ESTIMEE_W, False


def memoire_pic(fonction, donnees):
    """Mesure separee : tracemalloc ralentit le code, on ne la mele pas au temps."""
    tracemalloc.start()
    fonction(donnees)
    _, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pic / 1024  # Ko


def main():
    random.seed(1)
    rapl = rapl_disponible()
    print("Energie :", "RAPL (mesure reelle)" if rapl
          else f"ESTIMEE ({PUISSANCE_ESTIMEE_W} W x temps)")

    lignes = []
    for n in TAILLES:
        donnees = [random.randint(0, 10**6) for _ in range(n)]
        for nom, f in ALGOS.items():
            res = [mesurer(f, donnees, rapl) for _ in range(REPETITIONS)]
            lignes.append({
                "algo": nom,
                "n": n,
                "temps_s": statistics.median(r[0] for r in res),
                "energie_J": statistics.median(r[1] for r in res),
                "memoire_Ko": memoire_pic(f, donnees),
                "energie_mesuree": res[0][2],
            })
            print(f"n={n:<5} {nom:<17} {lignes[-1]['temps_s']*1000:8.1f} ms  "
                  f"{lignes[-1]['energie_J']:.4f} J  {lignes[-1]['memoire_Ko']:.0f} Ko")

    df = pd.DataFrame(lignes)
    df.to_csv("resultats_benchmark.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, col, titre in zip(axes,
                              ["temps_s", "energie_J", "memoire_Ko"],
                              ["Temps (s)", "Energie (J)", "Memoire pic (Ko)"]):
        for nom, g in df.groupby("algo"):
            ax.plot(g["n"], g[col], "o-", label=nom)
        ax.set_xlabel("Taille du tableau n")
        ax.set_ylabel(titre)
        ax.set_yscale("log")
        ax.set_title(titre)
    axes[0].legend()
    plt.tight_layout()
    plt.savefig("graphique_benchmark.png", dpi=200)
    print("Fichiers : resultats_benchmark.csv, graphique_benchmark.png")


if __name__ == "__main__":
    main()
