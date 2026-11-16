import pandas as pd

FICHIER = "resultats_benchmark.csv"
REFERENCE = "sorted (Timsort)"   # ecrit en C : analyse a part des tris Python
CRITERES = ["energie_J", "temps_s", "memoire_Ko"]
GROUPE = ["donnees", "n"]        # une analyse par type de donnees et par taille
ENSEMBLES = {
    "energie_temps_memoire": CRITERES,
    "energie_temps": ["energie_J", "temps_s"],
    "energie_memoire": ["energie_J", "memoire_Ko"],
    "temps_memoire": ["temps_s", "memoire_Ko"],
}


def non_domines(groupe, colonnes):
    valeurs = groupe[colonnes].to_numpy()
    garde = []
    for i, v in enumerate(valeurs):
        domine = any((w <= v).all() and (w < v).any()
                     for j, w in enumerate(valeurs) if j != i)
        garde.append(not domine)
    return groupe[garde]


def main():
    df = pd.read_csv(FICHIER)
    if "donnees" not in df.columns:          # ancien CSV : donnees aleatoires seulement
        df["donnees"] = "aleatoire"

    # sorted() (C) a part, les 4 tris Python sont analyses entre eux
    df_ref = df[df["algo"] == REFERENCE].copy()
    df = df[df["algo"] != REFERENCE].copy()

    df["puissance_W"] = df["energie_J"] / df["temps_s"]
    df_ref["puissance_W"] = df_ref["energie_J"] / df_ref["temps_s"]

    if "energie_std_J" in df.columns:
        df["energie_cv_pct"] = 100 * df["energie_std_J"] / df["energie_J"]
        df["temps_cv_pct"] = 100 * df["temps_std_s"] / df["temps_s"]

    for c in CRITERES:
        df[c + "_norm"] = df[c] / df.groupby(GROUPE)[c].transform("min")

    normalise_global = (df.groupby(["donnees", "algo"])[[c + "_norm" for c in CRITERES]]
                        .mean()
                        .sort_values(["donnees", "energie_J_norm"]))

    lignes = []
    for nom, colonnes in ENSEMBLES.items():
        for (donnees, n), g in df.groupby(GROUPE):
            for algo in non_domines(g, colonnes)["algo"]:
                lignes.append({"criteres": nom, "donnees": donnees, "n": n, "algo": algo})
    pareto = pd.DataFrame(lignes)

    df.to_csv("resultats_analyse.csv", index=False)
    normalise_global.to_csv("normalise_global.csv")
    pareto.to_csv("pareto.csv", index=False)
    df_ref.to_csv("reference_sorted.csv", index=False)

    colonnes_affichees = ["donnees", "algo", "n", "puissance_W"] + [c + "_norm" for c in CRITERES]
    if "energie_cv_pct" in df.columns:
        colonnes_affichees += ["energie_cv_pct", "temps_cv_pct"]

    print("\nTris Python : puissance moyenne, valeurs normalisees (1.00 = meilleur pour ce type de donnees et ce n), dispersion\n")
    print(df[colonnes_affichees].round(3).to_string(index=False))

    print("\nTableau normalise global (moyenne sur les tailles, 1.00 = meilleur)\n")
    print(normalise_global.round(2).to_string())

    nmax = df["n"].max()
    print(f"\nClassement en energie pour n={nmax}, selon le type de donnees (du plus econome au moins econome)\n")
    for donnees, g in df[df["n"] == nmax].groupby("donnees"):
        print(f"{donnees:<14} {' < '.join(g.sort_values('energie_J')['algo'])}")

    print("\nEnsembles de Pareto (algorithmes non domines)\n")
    for (nom, donnees, n), g in pareto.groupby(["criteres", "donnees", "n"]):
        print(f"{nom:<22} {donnees:<13} n={n:<6} {', '.join(g['algo'])}")

    if len(df_ref):
        aff = df_ref.copy()
        aff["temps_ms"] = aff["temps_s"] * 1000
        print(f"\nReference : {REFERENCE} (ecrit en C), a part des tris Python\n")
        print(aff[["donnees", "n", "temps_ms", "energie_J", "memoire_Ko", "puissance_W"]]
              .round(4).to_string(index=False))


if __name__ == "__main__":
    main()
