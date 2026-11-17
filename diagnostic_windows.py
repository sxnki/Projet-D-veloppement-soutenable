"""
Diagnostic du compteur d'énergie de Windows : à lancer UNE FOIS avant le benchmark.

    py diagnostic_windows.py

Il mesure 6 s au repos puis 6 s sous charge (un cœur à 100 %), puis :
- déduit l'unité du compteur (picowatt-heure, microjoule, ...) en vérifiant que les puissances obtenues
  sont plausibles ET cohérentes avec le compteur de puissance de Windows ;
- mesure la finesse de mise à jour du compteur (s'il ne change que toutes les secondes, il faut des
  mesures plus longues : option --duree-min du benchmark).

Fermez les autres programmes, branchez le secteur et ne touchez pas à l'ordinateur pendant le test.
"""
import statistics
import time

DUREE_PHASE_S = 6.0

# unités candidates : (nom, joules par unité)
UNITES_ENERGIE = [
    ("picowatt-heure", 3.6e-9), ("nanowatt-heure", 3.6e-6), ("microwatt-heure", 3.6e-3),
    ("milliwatt-heure", 3.6), ("watt-heure", 3600.0),
    ("picojoule", 1e-12), ("nanojoule", 1e-9), ("microjoule", 1e-6), ("millijoule", 1e-3), ("joule", 1.0),
]
UNITES_PUISSANCE = [("watt", 1.0), ("milliwatt", 1e-3), ("microwatt", 1e-6)]


def deviner_unite(taux_repos, taux_charge, pw_repos=None, pw_charge=None):
    """taux_* : variation du compteur d'énergie par seconde (unités brutes / s).
    pw_* : valeurs brutes moyennes du compteur de puissance (facultatif).
    Retourne la liste des unités compatibles : (nom, facteur_joules, P_repos_W, P_charge_W, unite_puissance)."""
    resultats = []
    for nom, f in UNITES_ENERGIE:
        p0, p1 = taux_repos * f, taux_charge * f
        if not (0.3 <= p0 <= 40 and 3 <= p1 <= 300 and p1 > 1.2 * p0):
            continue
        if pw_charge is None:
            resultats.append((nom, f, p0, p1, None))
            continue
        for nom_p, g in UNITES_PUISSANCE:
            if abs(p1 - pw_charge * g) <= 0.35 * p1 and (pw_repos is None or abs(p0 - pw_repos * g) <= 0.5 * max(p0, 1)):
                resultats.append((nom, f, p0, p1, nom_p))
    return resultats


def phase(source, duree, charge):
    """Lit le compteur en continu pendant `duree` s. Retourne (taux brut/s, puissance brute moyenne, intervalles)."""
    t_debut = time.perf_counter()
    mesures = []                      # (temps, énergie brute)
    puissances = []
    while True:
        if charge:
            sum(i * i for i in range(3000))      # occupe un cœur
        else:
            time.sleep(0.02)
        t = time.perf_counter() - t_debut
        mesures.append((t, source.lire_energie_brute()))
        p = source.lire_puissance_brute()
        if p is not None:
            puissances.append(p)
        if t >= duree:
            break
    (t0, e0), (t1, e1) = mesures[0], mesures[-1]
    taux = (e1 - e0) / (t1 - t0)
    changements = [t for (t, e), (_, e_prec) in zip(mesures[1:], mesures[:-1]) if e != e_prec]
    intervalles = [b - a for a, b in zip(changements, changements[1:])]
    return taux, (statistics.mean(puissances) if puissances else None), intervalles, mesures


def rapport(taux_repos, taux_charge, pw_repos, pw_charge, intervalles):
    print(f"\nVariation brute du compteur d'énergie : {taux_repos:.6g} /s au repos, {taux_charge:.6g} /s sous charge")
    if pw_charge is not None:
        print(f"Compteur de puissance (brut) : {pw_repos:.6g} au repos, {pw_charge:.6g} sous charge")
    else:
        print("Compteur de puissance indisponible (la vérification croisée est ignorée).")

    if taux_charge <= taux_repos * 1.05:
        print("\nProblème : le compteur n'augmente pas plus sous charge qu'au repos. "
              "Il ne mesure peut-être pas ce qu'on attend ; envoyez cette sortie telle quelle.")
        return None

    candidats = deviner_unite(taux_repos, taux_charge, pw_repos, pw_charge)
    if len(candidats) == 1:
        nom, f, p0, p1, nom_p = candidats[0]
        print(f"\nUnité probable du compteur d'énergie : {nom} (puissance déduite : {p0:.1f} W au repos, {p1:.1f} W en charge)")
        if nom_p:
            print(f"Compteur de puissance en {nom_p} : cohérent.")
        print(f"\n>>> Utilisez :  py benchmark_energie.py --facteur-joules {f:g}")
        res = f
    elif not candidats:
        print("\nAucune unité usuelle ne donne des puissances plausibles : envoyez cette sortie telle quelle.")
        res = None
    else:
        print("\nPlusieurs unités possibles, vérification impossible automatiquement :")
        for nom, f, p0, p1, nom_p in candidats:
            print(f"  - {nom}: facteur {f:g}  ({p0:.1f} W repos, {p1:.1f} W charge)")
        res = None

    if intervalles:
        med = statistics.median(intervalles) * 1000
        print(f"\nLe compteur change toutes les ~{med:.0f} ms (médiane).")
        if med > 200:
            print("Mise à jour lente : utilisez --duree-min 5 (ou plus) pour que l'erreur reste faible.")
    else:
        print("\nImpossible d'estimer la finesse de mise à jour (le compteur n'a presque pas changé).")
    return res


def main():
    from rapl_windows import SourceWindows
    source = SourceWindows(facteur_joules=1.0)
    print(f"Compteurs ouverts. Repos pendant {DUREE_PHASE_S:.0f} s, ne touchez à rien...")
    taux0, pw0, _, _ = phase(source, DUREE_PHASE_S, charge=False)
    print(f"Charge pendant {DUREE_PHASE_S:.0f} s...")
    taux1, pw1, intervalles, _ = phase(source, DUREE_PHASE_S, charge=True)
    rapport(taux0, taux1, pw0, pw1, intervalles)


if __name__ == "__main__":
    main()
