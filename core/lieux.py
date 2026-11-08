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
