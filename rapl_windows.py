"""
Lecture du compteur d'énergie de Windows (« Energy Meter », alimenté par RAPL) via l'API PDH.
Aucune dépendance externe : uniquement ctypes. Ne fonctionne que sous Windows, sur un matériel dont
les pilotes exposent ce compteur (vérification : typeperf -qx | Select-String RAPL).

Les unités du compteur ne sont pas documentées de façon fiable : lancez d'abord
    py diagnostic_windows.py
qui détecte l'unité et affiche la valeur à passer à  --facteur-joules  (joules par unité du compteur).
"""
import ctypes

PDH_FMT_LARGE = 0x00000400

# Chemins de compteurs essayés dans l'ordre. L'anglais est indépendant de la langue de Windows ;
# les chemins français sont un repli (ce sont ceux affichés par typeperf sur un Windows en français).
ENERGIE_EN = [r"\Energy Meter(RAPL_Package0_PKG)\Energy"]
PUISSANCE_EN = [r"\Energy Meter(RAPL_Package0_PKG)\Power"]
ENERGIE_FR = [r"\Compteur Énergie(RAPL_Package0_PKG)\Énergie"]
PUISSANCE_FR = [r"\Compteur Énergie(RAPL_Package0_PKG)\Alimentation"]


class _Valeur(ctypes.Union):
    _fields_ = [("longValue", ctypes.c_long),
                ("doubleValue", ctypes.c_double),
                ("largeValue", ctypes.c_longlong)]


class _FmtValeur(ctypes.Structure):          # PDH_FMT_COUNTERVALUE
    _fields_ = [("CStatus", ctypes.c_ulong), ("u", _Valeur)]


class SourceWindows:
    """Énergie cumulée du package CPU, en joules (valeur brute du compteur x facteur_joules)."""
    nom = "Compteur d'énergie Windows (Energy Meter / RAPL)"

    def __init__(self, facteur_joules=1.0, chemin_energie=None, chemin_puissance=None):
        if not hasattr(ctypes, "WinDLL"):
            raise OSError("ce module ne fonctionne que sous Windows")
        self.facteur = facteur_joules
        pdh = ctypes.WinDLL("pdh.dll")
        self._pdh = pdh
        u = ctypes.c_size_t
        h = ctypes.c_void_p
        pdh.PdhOpenQueryW.argtypes = [ctypes.c_wchar_p, u, ctypes.POINTER(h)]
        pdh.PdhAddCounterW.argtypes = [h, ctypes.c_wchar_p, u, ctypes.POINTER(h)]
        pdh.PdhAddEnglishCounterW.argtypes = [h, ctypes.c_wchar_p, u, ctypes.POINTER(h)]
        pdh.PdhCollectQueryData.argtypes = [h]
        pdh.PdhGetFormattedCounterValue.argtypes = [h, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                                                    ctypes.POINTER(_FmtValeur)]
        for f in (pdh.PdhOpenQueryW, pdh.PdhAddCounterW, pdh.PdhAddEnglishCounterW,
                  pdh.PdhCollectQueryData, pdh.PdhGetFormattedCounterValue):
            f.restype = ctypes.c_long

        self._requete = h()
        self._verifier(pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._requete)), "PdhOpenQuery")
        self._energie = self._ajouter(chemin_energie, ENERGIE_EN, ENERGIE_FR)
        try:
            self._puissance = self._ajouter(chemin_puissance, PUISSANCE_EN, PUISSANCE_FR)
        except OSError:
            self._puissance = None            # facultatif : sert seulement au diagnostic
        self._verifier(pdh.PdhCollectQueryData(self._requete), "PdhCollectQueryData")

    @staticmethod
    def _verifier(code, nom):
        if code != 0:
            raise OSError(f"{nom} a échoué (code PDH 0x{code & 0xFFFFFFFF:08X})")

    def _ajouter(self, chemin_perso, chemins_en, chemins_fr):
        essais = []
        if chemin_perso:
            essais.append((self._pdh.PdhAddCounterW, chemin_perso))
        essais += [(self._pdh.PdhAddEnglishCounterW, c) for c in chemins_en]
        essais += [(self._pdh.PdhAddCounterW, c) for c in chemins_fr]
        for fonction, chemin in essais:
            compteur = ctypes.c_void_p()
            if fonction(self._requete, chemin, 0, ctypes.byref(compteur)) == 0:
                return compteur
        raise OSError("aucun compteur trouvé parmi : " + " | ".join(c for _, c in essais))

    def _lire_brut(self, compteur):
        self._verifier(self._pdh.PdhCollectQueryData(self._requete), "PdhCollectQueryData")
        type_c = ctypes.c_ulong()
        val = _FmtValeur()
        self._verifier(self._pdh.PdhGetFormattedCounterValue(
            compteur, PDH_FMT_LARGE, ctypes.byref(type_c), ctypes.byref(val)), "PdhGetFormattedCounterValue")
        return float(val.u.largeValue)

    def lire_energie_brute(self):
        return self._lire_brut(self._energie)

    def lire_puissance_brute(self):
        return self._lire_brut(self._puissance) if self._puissance is not None else None

    # interface commune avec la source Linux
    def lire(self):
        return self.lire_energie_brute() * self.facteur

    def delta(self, e0, e1):
        return e1 - e0
