"""
Graphiques du benchmark (à partir de data/resultats_benchmark.csv).

Usage :
    python graphiques.py
    python graphiques.py --fichier data/resultats_benchmark.csv --sortie figures

Figures produites :
- benchmark_<type>.png        temps, énergie (brute), mémoire en fonction de n (échelles log-log), un fichier par type de données
- synthese_energie_memoire.png compromis énergie / mémoire à la plus grande taille, pour les 4 types de données
"""
import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

REFERENCE = "sorted (Timsort)"
ORDRE = ["bulles", "insertion", "fusion", "rapide", REFERENCE]
STYLE = {   # couleur, marqueur, trait
    "bulles":    ("#1f77b4", "o", "-"),
    "insertion": ("#2ca02c", "s", "-"),
    "fusion":    ("#ff7f0e", "^", "-"),
    "rapide":    ("#d62728", "D", "-"),
    REFERENCE:   ("#7f7f7f", "v", "--"),     # pointillés : écrit en C, à part
}
LIBELLES = {"bulles": "Tri à bulles", "insertion": "Tri par insertion", "fusion": "Tri fusion",
            "rapide": "Tri rapide", REFERENCE: "sorted (Timsort, écrit en C)"}
TYPES = {"aleatoire": "données aléatoires", "trie": "données triées",
         "inverse": "données inversées", "presque_trie": "données presque triées"}
PANNEAUX = [("temps_s", "Temps par tri (s)"),
            ("energie_J", "Énergie brute par tri (J)"),
            ("memoire_Ko", "Mémoire de pointe (Ko)")]


def style_axe_n(ax, tailles):
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(tailles))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Taille du tableau n")
    ax.grid(True, which="major", alpha=0.3)


def figure_type(d, type_donnees, chemin):
    tailles = sorted(d["n"].unique())
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (col, titre) in zip(axes, PANNEAUX):
        for algo in ORDRE:
            g = d[d["algo"] == algo].sort_values("n")
            if g.empty:
                continue
            c, m, ls = STYLE[algo]
            ax.plot(g["n"], g[col], marker=m, linestyle=ls, color=c, label=LIBELLES[algo],
                    markersize=6, linewidth=1.8)
        ax.set_yscale("log")
        ax.set_ylabel(titre)
        ax.set_title(titre.split(" (")[0])
        style_axe_n(ax, tailles)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False,
               bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(f"Tris sur {TYPES[type_donnees]} (échelles logarithmiques)", y=1.0, fontsize=13)
    fig.tight_layout(rect=(0, 0.07, 1, 0.98))
    fig.savefig(chemin, dpi=200, bbox_inches="tight")
    plt.close(fig)


def figure_synthese(df, chemin):
    nmax = df["n"].max()
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.4), sharey=True)
    for ax, (type_donnees, titre) in zip(axes, TYPES.items()):
        d = df[(df["donnees"] == type_donnees) & (df["n"] == nmax)]
        for algo in ORDRE:
            g = d[d["algo"] == algo]
            if g.empty:
                continue
            c, m, _ = STYLE[algo]
            ax.scatter(g["memoire_Ko"], g["energie_J"], color=c, marker=m, s=90,
                       label=LIBELLES[algo], edgecolor="black", linewidth=0.5, zorder=3)
        ax.set_yscale("log")
        ax.set_xlabel("Mémoire de pointe (Ko)")
        ax.set_title(titre.capitalize())
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel(f"Énergie brute par tri (J), n = {nmax}")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Compromis énergie / mémoire (en bas à gauche = meilleur)", y=1.0, fontsize=13)
    fig.tight_layout(rect=(0, 0.08, 1, 0.97))
    fig.savefig(chemin, dpi=200, bbox_inches="tight")
    plt.close(fig)


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fichier", default="data/resultats_benchmark.csv")
    p.add_argument("--sortie", default="figures")
    return p


def main():
    args = parser().parse_args()
    os.makedirs(args.sortie, exist_ok=True)
    df = pd.read_csv(args.fichier)
    for type_donnees, d in df.groupby("donnees"):
        figure_type(d, type_donnees, os.path.join(args.sortie, f"benchmark_{type_donnees}.png"))
    figure_synthese(df, os.path.join(args.sortie, "synthese_energie_memoire.png"))
    print(f"Figures écrites dans {args.sortie}/")


if __name__ == "__main__":
    main()