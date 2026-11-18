"""
Analyse des résultats du benchmark : normalisation, dispersion, puissance, pentes, Pareto.

Usage :
    python analyse_resultats.py
    python analyse_resultats.py --fichier data/resultats_benchmark.csv --sortie results

Choix méthodologiques :
- sorted() (Timsort) est écrit en C : il est analysé à part des quatre tris écrits en Python pur.
- Les valeurs sont normalisées par groupe (type de données x n) : 1.00 = meilleur algorithme du groupe.
- Les ratios sont moyennés par MOYENNE GÉOMÉTRIQUE (la moyenne arithmétique de ratios serait dominée
  par les grands n, où les ratios explosent).
- Énergie et temps sont quasi proportionnels (puissance presque constante en calcul mono-cœur) :
  l'ensemble de Pareto (énergie, temps) serait donc sans intérêt. On ne garde que les ensembles
  contenant la mémoire, seul critère qui introduit de vrais compromis.
"""
import argparse
import os

import numpy as np
import pandas as pd

REFERENCE = "sorted (Timsort)"
CRITERES = ["energie_J", "temps_s", "memoire_Ko"]
GROUPE = ["donnees", "n"]
ENSEMBLES = {
    "energie_temps_memoire": CRITERES,
    "energie_memoire": ["energie_J", "memoire_Ko"],
}


def non_domines(groupe, colonnes):
    """Lignes dont aucune autre ligne n'est au moins aussi bonne partout et meilleure quelque part."""
    valeurs = groupe[colonnes].to_numpy()
    garde = []
    for i, v in enumerate(valeurs):
        domine = any((w <= v).all() and (w < v).any()
                     for j, w in enumerate(valeurs) if j != i)
        garde.append(not domine)
    return groupe[garde]


def moyenne_geometrique(s):
    return float(np.exp(np.log(s).mean()))


def pente_loglog(g, colonne):
    """Exposant b dans colonne ~ n^b (régression linéaire en échelle log-log)."""
    return float(np.polyfit(np.log(g["n"]), np.log(g[colonne]), 1)[0])


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fichier", default="data/resultats_benchmark.csv")
    p.add_argument("--sortie", default="results")
    return p


def main():
    args = parser().parse_args()
    os.makedirs(args.sortie, exist_ok=True)
    out = lambda nom: os.path.join(args.sortie, nom)

    df = pd.read_csv(args.fichier)
    if "energie_nette_J" in df.columns and (df["energie_nette_J"] <= 0).any():
        print(f"ATTENTION : {(df['energie_nette_J'] <= 0).sum()} énergies nettes <= 0 dans {args.fichier} : "
              "puissance de repos mal mesurée, utilisez seulement energie_J (brute).\n")
    df_ref = df[df["algo"] == REFERENCE].copy()
    df = df[df["algo"] != REFERENCE].copy()

    for d in (df, df_ref):
        d["puissance_W"] = d["energie_J"] / d["temps_s"]
        d["energie_cv_pct"] = 100 * d["energie_std_J"] / d["energie_J"]
        d["temps_cv_pct"] = 100 * d["temps_std_s"] / d["temps_s"]

    for c in CRITERES:
        df[c + "_norm"] = df[c] / df.groupby(GROUPE)[c].transform("min")

    cols_norm = [c + "_norm" for c in CRITERES]
    normalise_global = (df.groupby(["donnees", "algo"])[cols_norm]
                        .agg(moyenne_geometrique)
                        .sort_values(["donnees", "energie_J_norm"]))

    # --- énergie et temps : redondance ---
    corr = float(np.corrcoef(np.log(df["energie_J"]), np.log(df["temps_s"]))[0, 1])
    rang_e = df.groupby(GROUPE)["energie_J"].rank()
    rang_t = df.groupby(GROUPE)["temps_s"].rank()
    concordance = float((rang_e == rang_t).mean())
    puissance = (pd.concat([df, df_ref]).groupby("algo")["puissance_W"]
                 .agg(["mean", "std", "min", "max"]))

    # --- pentes log-log (complexité observée) ---
    lignes_pentes = []
    for (donnees, algo), g in pd.concat([df, df_ref]).groupby(["donnees", "algo"]):
        lignes_pentes.append({"donnees": donnees, "algo": algo,
                              "pente_temps": pente_loglog(g, "temps_s"),
                              "pente_energie": pente_loglog(g, "energie_J"),
                              "pente_memoire": pente_loglog(g, "memoire_Ko")})
    pentes = pd.DataFrame(lignes_pentes)

    # --- Pareto ---
    lignes = []
    for nom, colonnes in ENSEMBLES.items():
        for (donnees, n), g in df.groupby(GROUPE):
            for algo in non_domines(g, colonnes)["algo"]:
                lignes.append({"criteres": nom, "donnees": donnees, "n": n, "algo": algo})
    pareto = pd.DataFrame(lignes)

    df.to_csv(out("resultats_analyse.csv"), index=False)
    df_ref.to_csv(out("reference_sorted.csv"), index=False)
    normalise_global.to_csv(out("normalise_global.csv"))
    pareto.to_csv(out("pareto.csv"), index=False)
    pentes.to_csv(out("pentes_loglog.csv"), index=False)
    puissance.to_csv(out("puissance_par_algo.csv"))

    # --- affichage ---
    print(f"\nCorrélation log(énergie) / log(temps) : r = {corr:.4f}")
    print(f"Classements énergie et temps identiques dans {100 * concordance:.0f} % des cas "
          "(groupes type de données x n, tris Python)")
    print("\nPuissance moyenne par algorithme (W) : énergie = puissance x temps\n")
    print(puissance.round(2).to_string())

    print("\nTris Python : valeurs normalisées globales (moyenne géométrique sur les tailles, 1.00 = meilleur)\n")
    print(normalise_global.round(2).to_string())

    nmax = df["n"].max()
    print(f"\nClassement en énergie pour n={nmax} (du plus économe au moins économe)\n")
    for donnees, g in df[df["n"] == nmax].groupby("donnees"):
        print(f"{donnees:<14} {' < '.join(g.sort_values('energie_J')['algo'])}")

    print("\nPentes log-log du temps (≈2 : quadratique ; ≈1 : quasi-linéaire / n log n)\n")
    print(pentes.pivot(index="algo", columns="donnees", values="pente_temps").round(2).to_string())

    print("\nEnsembles de Pareto (algorithmes non dominés), n =", nmax, "\n")
    for (nom, donnees, n), g in pareto[pareto["n"] == nmax].groupby(["criteres", "donnees", "n"]):
        print(f"{nom:<22} {donnees:<13} n={n:<6} {', '.join(g['algo'])}")

    if len(df_ref):
        aff = df_ref.copy()
        aff["temps_ms"] = aff["temps_s"] * 1000
        print(f"\nRéférence : {REFERENCE} (écrit en C), à part des tris Python\n")
        print(aff[["donnees", "n", "temps_ms", "energie_J", "memoire_Ko", "puissance_W"]]
              .round(4).to_string(index=False))

    print(f"\nFichiers écrits dans {args.sortie}/")


if __name__ == "__main__":
    main()