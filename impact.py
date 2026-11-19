"""
Extrapolation de l'énergie mesurée à un usage réel, émissions de CO2 associées et effet rebond.

Usage :
    python impact.py
    python impact.py --n 4000 --donnees aleatoire --tris-par-jour 1000000
    python impact.py --colonne energie_nette_J           # (par défaut : nette si disponible)

ATTENTION : le scénario (nombre de tris par jour, taille des tableaux) est une HYPOTHÈSE de travail
pour donner un ordre de grandeur, pas une mesure. Modifiez-la pour votre cas d'usage.

Ce qui est compté : l'énergie électrique du processeur mesurée par RAPL (package CPU).
Ce qui n'est PAS compté : le reste de la machine, le refroidissement et les pertes du centre de
données (PUE), la fabrication du matériel, le réseau.

Intensités carbone par défaut (gCO2e/kWh), France 2025 :
- 19.6 : RTE, émissions directes de la production d'électricité, 2025 (borne basse) ;
- 51.9 : ADEME, Base Carbone, mix de consommation (cycle de vie, électricité 2024) (valeur centrale).
À vérifier et citer avec leur date dans le rapport.

Effet rebond : si un algorithme divise l'énergie par un facteur g mais que l'usage est multiplié par
m, l'énergie totale est multipliée par m / g. Le gain est annulé dès que m >= g (seuil de rebond).
"""
import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd

REFERENCE_PAR_DEFAUT = "bulles"
J_PAR_KWH = 3.6e6


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fichier", default="data/resultats_benchmark.csv")
    p.add_argument("--n", type=int, default=4000, help="taille des tableaux du scénario")
    p.add_argument("--donnees", default="aleatoire", help="type de données du scénario")
    p.add_argument("--tris-par-jour", type=float, default=1e6, help="HYPOTHÈSE : nombre de tris par jour")
    p.add_argument("--intensites", type=float, nargs="+", default=[19.6, 51.9],
                   help="intensité carbone de l'électricité (gCO2e/kWh)")
    p.add_argument("--reference", default=REFERENCE_PAR_DEFAUT, help="algorithme de la situation de référence")
    p.add_argument("--colonne", default=None,
                   help="énergie utilisée : energie_nette_J (par défaut si présente : surplus dû au tri) ou energie_nette_J (brute)")
    p.add_argument("--sortie", default="results")
    p.add_argument("--figures", default="figures")
    return p


def main():
    args = parser().parse_args()
    os.makedirs(args.sortie, exist_ok=True)
    os.makedirs(args.figures, exist_ok=True)

    df = pd.read_csv(args.fichier)
    if args.colonne is None:
        net_ok = "energie_nette_J" in df.columns and (df["energie_nette_J"] > 0).all()
        args.colonne = "energie_nette_J" if net_ok else "energie_nette_J"
        if "energie_nette_J" in df.columns and not net_ok:
            print("Énergie nette inutilisable (valeurs <= 0) : l'énergie brute est utilisée.")
    if args.colonne not in df.columns:
        raise SystemExit(f"Colonne {args.colonne} absente de {args.fichier} "
                         "(energie_nette_J n'existe que si le benchmark a pu lire RAPL).")
    d = df[(df["donnees"] == args.donnees) & (df["n"] == args.n)].set_index("algo")
    if d.empty:
        raise SystemExit(f"Aucune ligne pour donnees={args.donnees}, n={args.n}")
    if args.reference not in d.index:
        raise SystemExit(f"Algorithme de référence inconnu : {args.reference}")

    e_ref = d.loc[args.reference, args.colonne]
    jours = 365
    lignes = []
    for algo, r in d.iterrows():
        e = r[args.colonne]
        kwh_an = e * args.tris_par_jour * jours / J_PAR_KWH
        ligne = {"algo": algo, "energie_par_tri_J": e, "kWh_par_an": kwh_an,
                 "facteur_gain_vs_ref": e_ref / e,
                 "seuil_rebond_multiplicateur_usage": e_ref / e}
        for i in args.intensites:
            ligne[f"gCO2e_par_an@{i:g}"] = kwh_an * i
        lignes.append(ligne)
    res = pd.DataFrame(lignes).sort_values("energie_par_tri_J", ascending=False)
    res.to_csv(os.path.join(args.sortie, "impact.csv"), index=False)

    print(f"\nScénario (HYPOTHÈSE) : {args.tris_par_jour:,.0f} tris/jour, n={args.n}, données {args.donnees}")
    print(f"Référence : {args.reference} ({e_ref:.4f} J par tri). Énergie utilisée : {args.colonne}\n")
    aff = res.copy()
    aff["energie_par_tri_J"] = aff["energie_par_tri_J"].map("{:.5f}".format)
    print(aff.round(3).to_string(index=False))
    print("\nLecture : si l'usage est multiplié par le « seuil de rebond » ou plus à cause du gain, "
          "l'économie d'énergie est annulée.")

    # --- figure : émissions annuelles, deux intensités ---
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    algos = list(res["algo"])
    largeur = 0.8 / len(args.intensites)
    for k, i in enumerate(args.intensites):
        vals = res[f"gCO2e_par_an@{i:g}"].to_numpy()
        pos = [x + k * largeur for x in range(len(algos))]
        barres = ax.bar(pos, vals, width=largeur, label=f"{i:g} gCO₂e/kWh")
        for b, v in zip(barres, vals):
            etiquette = f"{v:,.0f}".replace(",", " ") if v >= 1000 else f"{v:.3g}"
            ax.annotate(etiquette, (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom", fontsize=8)
    ax.set_xticks([x + largeur * (len(args.intensites) - 1) / 2 for x in range(len(algos))])
    ax.set_xticklabels(algos, rotation=15)
    ax.set_yscale("log")
    ax.set_ylabel("Émissions (gCO₂e par an)")
    nature = "énergie nette" if args.colonne == "energie_nette_J" else "énergie brute"
    tris = f"{args.tris_par_jour:,.0f}".replace(",", " ")
    ax.set_title(f"{tris} tris/jour de {args.n} éléments, {nature} (scénario hypothétique)", fontsize=11)
    ax.legend(title="Intensité du réseau")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.figures, "impact_emissions.png"), dpi=200)
    plt.close(fig)
    print(f"\nFichiers : {args.sortie}/impact.csv, {args.figures}/impact_emissions.png")


if __name__ == "__main__":
    main()