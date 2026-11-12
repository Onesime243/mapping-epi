"""Doublons possibles : même cas saisi deux fois (plusieurs ordinateurs, paquets de fiches, imports).

Deux règles, sans rien supprimer ni fusionner (la décision revient à l'équipe) :
- même N° EPID (après normalisation : majuscules, espaces et tirets ignorés) ;
- même zone de santé, même sexe, âge à ± 1 an et début des symptômes à ± 2 jours.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import List

from core.models import Case


@dataclass
class Doublon:
    a: Case
    b: Case
    raison: str
    certitude: str      # « forte » ou « à vérifier »


def _norm(s: str) -> str:
    from core.links import _id
    return _id(s or "")


def doublons(cases: List[Case]) -> List[Doublon]:
    from core.lieux import cle
    out: List[Doublon] = []
    vus = set()
    par_code = {}
    for c in cases:
        k = _norm(c.code_cas)
        if k:
            par_code.setdefault(k, []).append(c)
    for k, grp in par_code.items():
        for a, b in combinations(grp, 2):
            out.append(Doublon(a, b, f"même N° EPID ({a.code_cas})", "forte"))
            vus.add(frozenset((a.id, b.id)))
    par_zs = {}
    for c in cases:
        if c.zs and c.debut_symptomes and c.sexe in ("M", "F") and c.age is not None:
            par_zs.setdefault(cle(c.zs), []).append(c)
    for grp in par_zs.values():
        for a, b in combinations(grp, 2):
            if frozenset((a.id, b.id)) in vus:
                continue
            if (a.sexe == b.sexe and a.age_unite == b.age_unite and abs(a.age - b.age) <= 1
                    and abs((a.debut_symptomes - b.debut_symptomes).days) <= 2):
                if a.code_cas and b.code_cas:
                    raison = "même ZS, sexe, âge et début des symptômes, mais N° EPID différents"
                else:
                    raison = "même ZS, sexe, âge et début des symptômes"
                out.append(Doublon(a, b, raison, "à vérifier"))
    return sorted(out, key=lambda d: (d.certitude != "forte", d.a.zs, d.a.code_cas))
