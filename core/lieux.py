"""Identification des lieux entre étapes et entre cas.

Deux écritures du même lieu (« Carrière minière Makasi (AS Bolebole) » et « carrière miniere Makasi »)
doivent être reconnues comme un seul lieu : la clé ignore la casse, les accents, la ponctuation et les
précisions entre parenthèses.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional

from config import theme
from core.models import Case

# lieux trop vagues pour relier des cas entre eux
VAGUES = {"", "?", "inconnu", "domicile", "menage", "maison", "route", "village", "quartier", "autre"}


def cle(nom: str) -> str:
    s = unicodedata.normalize("NFKD", str(nom or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)              # précisions entre parenthèses
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def case_label(c: Case) -> str:
    """Étiquette courte d'un cas : ID alphanumérique, sinon rang, sinon AS + J0."""
    if (c.code_cas or "").strip():
        return c.code_cas.strip()
    if c.rang:
        return f"Cas {c.rang}"
    j0 = f" {c.debut_symptomes:%d/%m}" if c.debut_symptomes else ""
    return f"Cas {c.aire_sante or c.zs or '?'}{j0}".strip()


@dataclass
class LieuFrequente:
    cle: str
    nom: str
    cas: List[Case] = field(default_factory=list)
    visites: int = 0
    types: Counter = field(default_factory=Counter)
    debut: Optional[date] = None
    fin: Optional[date] = None
    risque: str = "Inconnu"
    aires: Counter = field(default_factory=Counter)

    @property
    def n_cas(self) -> int:
        return len(self.cas)


def _noms_du_cas(c: Case):
    """(nom, étape ou None, type de lieu) pour chaque mention d'un lieu dans la fiche."""
    for p in c.places:
        yield p.nom, None, p.type
    for e in c.events:
        for loc in (e.lieu, e.lieu_arrivee):
            if loc:
                yield loc, e, ""


def frequentes(cases: Iterable[Case], min_cas: int = 1) -> List[LieuFrequente]:
    """Lieux mentionnés dans les fiches, triés par nombre de cas distincts puis de passages."""
    from core import rules
    lieux: Dict[str, LieuFrequente] = {}
    noms: Dict[str, Counter] = defaultdict(Counter)
    for c in cases:
        vus = set()
        for nom, ev, typ in _noms_du_cas(c):
            k = cle(nom)
            if k in VAGUES:
                continue
            L = lieux.setdefault(k, LieuFrequente(k, nom.strip()))
            noms[k][nom.strip()] += 1
            if typ:
                L.types[typ] += 1
            if ev is not None:
                L.visites += 1
                if ev.type:
                    L.types[ev.type] += 1
                d1, d2 = ev.date_debut, ev.date_fin or ev.date_debut
                if d1:
                    L.debut = min(L.debut, d1) if L.debut else d1
                    L.fin = max(L.fin, d2) if L.fin else d2
                r = rules.event_risk(ev, c)
                if theme.risk_rank(r) > theme.risk_rank(L.risque):
                    L.risque = r
            if k not in vus:
                vus.add(k)
                L.cas.append(c)
                L.aires[c.aire_sante or "?"] += 1
    for k, L in lieux.items():
        L.nom = noms[k].most_common(1)[0][0]
    out = [L for L in lieux.values() if L.n_cas >= min_cas]
    out.sort(key=lambda L: (-L.n_cas, -L.visites, L.nom.lower()))
    return out


# ---------------------------------------------------------------------------
# Écriture harmonisée des noms de lieux (même règle que la fiche web, web/static/editor.js)
# ---------------------------------------------------------------------------
SIGLES_LIEUX = {"HGR", "CS", "CM", "PS", "CSR", "CSDT", "CTE", "CTI", "CH", "CHU", "HGRB", "HGRK", "CBCA", "CEBCE",
                "CEPAC", "CBCE", "CECA", "ZS", "AS", "CRS", "PMI", "BCZ", "MSF", "ALIMA", "IRC", "ONG", "RN", "RN2",
                "RN4", "EP", "ITM", "IT", "DPS", "UPC", "UNIKIN", "MONUSCO", "FARDC", "PNC", "CTA", "ECC", "8E", "55E"}
PETITS_MOTS = {"de", "du", "des", "la", "le", "les", "et", "à", "a", "au", "aux", "en", "sur", "sous", "pour", "par"}


def harmoniser(nom: str) -> str:
    """« hgr beni » ou « HGR BENI » → « HGR Beni ». Sigles en majuscules ; si le nom est écrit tout en minuscules ou
    tout en majuscules, petits mots en minuscules et une majuscule aux autres mots."""
    mots = (nom or "").split()
    sans_sigles = " ".join(m for m in mots if re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", m).upper() not in SIGLES_LIEUX)
    # écrit tout en minuscules ou tout en majuscules : on met des majuscules aux noms ; sinon on respecte l'écriture
    # de l'agent (« Lieu de culte Monzombo » reste tel quel) et on ne corrige que les sigles et la 1re lettre
    uniforme = sans_sigles.islower() or sans_sigles.isupper()
    out = []
    for i, m in enumerate(mots):
        lettres = re.sub(r"[^A-Za-zÀ-ÿ0-9]", "", m)
        if lettres.upper() in SIGLES_LIEUX:
            out.append(m.upper())
        elif i > 0 and m.lower() in PETITS_MOTS:
            out.append(m.lower())
        elif any(ch.isdigit() for ch in m):
            out.append(m)
        elif not uniforme:
            out.append(m[:1].upper() + m[1:] if i == 0 else m)
        elif m.islower() or m.isupper():
            pre = ""
            if len(m) > 2 and m[1] in "'’" and m[0].lower() in "dl":     # d'Oicha, l'Église
                pre, m = m[:2].lower(), m[2:]
            out.append(pre + m[:1].upper() + m[1:].lower())
        else:
            out.append(m)
    return " ".join(out)


def lieux_de_zone(cases: Iterable[Case], zs: str, province: str = "", exclure: str = "") -> List[dict]:
    """Lieux déjà saisis dans les fiches d'une zone de santé : écriture la plus fréquente (harmonisée) et nombre
    de fiches qui les citent, du plus cité au moins cité."""
    zk = cle(zs)
    pk = cle(province)
    par_cle: Dict[str, Counter] = defaultdict(Counter)
    fiches: Dict[str, set] = defaultdict(set)
    for c in cases:
        if c.exemple() or c.id == exclure or not zk or cle(c.zs) != zk or (pk and c.province and cle(c.province) != pk):
            continue
        for nom, _e, _t in _noms_du_cas(c):
            k = cle(nom)
            if not k or k in VAGUES or "→" in nom:
                continue
            par_cle[k][harmoniser(nom.strip())] += 1
            fiches[k].add(c.id)
    out = [{"nom": cnt.most_common(1)[0][0], "n": len(fiches[k])} for k, cnt in par_cle.items()]
    return sorted(out, key=lambda d: (-d["n"], d["nom"].lower()))
