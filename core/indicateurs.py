"""Indicateurs de la riposte calculés sur la base des fiches.

- Catégories des zones de santé (config/categories_zs.yaml) selon les jours depuis le dernier cas notifié ;
- alertes « nouveau foyer possible » : premier cas d'une ZS / AS, ou reprise après une longue période sans cas ;
- délais : début des symptômes → notification, notification → confirmation ;
- incubation observée : début des symptômes − date du dernier contact avec le cas source (contacts connus) ;
- intervalle sériel : début des symptômes du cas − celui de son cas source enregistré.
Les dates manquantes sont exclues et comptées (rien n'est inventé).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Optional, Tuple

import yaml

from core import pyramide
from core.models import Case

ROOT = Path(__file__).resolve().parent.parent
_CFG: Optional[dict] = None


def config() -> dict:
    global _CFG
    if _CFG is None:
        with open(ROOT / "config" / "categories_zs.yaml", encoding="utf-8") as f:
            _CFG = yaml.safe_load(f)
    return _CFG


def date_notification(c: Case) -> Tuple[Optional[date], str]:
    """Date de notification ; à défaut la confirmation, puis le début des symptômes (origine indiquée)."""
    if c.date_notification:
        return c.date_notification, "notification"
    if c.date_confirmation:
        return c.date_confirmation, "confirmation"
    if c.debut_symptomes:
        return c.debut_symptomes, "début des symptômes"
    return None, ""


def categorie(jours: Optional[int]) -> dict:
    cats = config()["categories"]
    if jours is None:
        return {"num": None, "nom": "Aucun cas daté", "couleur": "#6B7785"}
    for cat in cats:
        if cat["max_jours"] is None or jours <= cat["max_jours"]:
            return cat
    return cats[-1]


@dataclass
class ZoneInfo:
    province: str
    zs: str
    n: int = 0
    n7: int = 0
    n21: int = 0
    dernier: Optional[date] = None
    jours: Optional[int] = None
    cat: dict = field(default_factory=dict)
    aires: int = 0
    sans_date: int = 0


@dataclass
class Alerte:
    case: Case
    quand: date
    niveau: str        # « ZS » ou « AS »
    lieu: str
    texte: str


def zones(cases: List[Case], ref: Optional[date] = None) -> List[ZoneInfo]:
    ref = ref or date.today()
    out: Dict[Tuple[str, str], ZoneInfo] = {}
    aires: Dict[Tuple[str, str], set] = {}
    for c in cases:
        key = (c.province or "?", c.zs or "?")
        z = out.setdefault(key, ZoneInfo(*key))
        z.n += 1
        aires.setdefault(key, set()).add(pyramide.norm(c.aire_sante) if c.aire_sante else "?")
        d, _src = date_notification(c)
        if not d:
            z.sans_date += 1
            continue
        if d <= ref:
            age = (ref - d).days
            z.n7 += age < 7
            z.n21 += age < 21
            if not z.dernier or d > z.dernier:
                z.dernier = d
    for key, z in out.items():
        z.aires = len(aires[key])
        z.jours = (ref - z.dernier).days if z.dernier else None
        z.cat = categorie(z.jours)
    return sorted(out.values(), key=lambda z: (z.cat.get("num") or 9, z.jours if z.jours is not None else 10 ** 6,
                                               pyramide.norm(z.zs)))


def alertes_foyers(cases: List[Case]) -> List[Alerte]:
    """Premier cas d'une ZS ou d'une AS, ou reprise après plus de `jours_foyer` jours sans cas."""
    seuil = int(config().get("jours_foyer", 21))
    dated = sorted(((d, c) for c in cases for d in [date_notification(c)[0]] if d), key=lambda x: x[0])
    last: Dict[Tuple[str, ...], date] = {}
    out: List[Alerte] = []
    for d, c in dated:
        zs_key = (pyramide.norm(c.province), pyramide.norm(c.zs))
        as_key = zs_key + (pyramide.norm(c.aire_sante),)
        prev_zs = last.get(zs_key)
        if c.zs:
            if prev_zs is None:
                out.append(Alerte(c, d, "ZS", c.zs, "premier cas notifié dans la ZS : nouveau foyer possible"))
            elif (d - prev_zs).days > seuil:
                out.append(Alerte(c, d, "ZS", c.zs, f"reprise après {(d - prev_zs).days} jours sans cas dans la ZS"))
            elif c.aire_sante and as_key not in last:
                out.append(Alerte(c, d, "AS", c.aire_sante, f"première aire touchée : AS {c.aire_sante} (ZS {c.zs})"))
        last[zs_key] = d
        last[as_key] = d
    return sorted(out, key=lambda a: a.quand, reverse=True)


@dataclass
class Stat:
    nom: str
    valeurs: List[int]
    exclus: int
    note: str = ""

    @property
    def n(self) -> int:
        return len(self.valeurs)

    def texte(self) -> str:
        if not self.valeurs:
            return "?"
        v = self.valeurs
        return f"médiane {median(v):g} j (moyenne {mean(v):.1f} ; {min(v)} à {max(v)} j)"


def delais(cases: List[Case]) -> List[Stat]:
    from core.links import _id
    by_code = {_id(c.code_cas): c for c in cases if c.code_cas}
    notif, conf, incub, serial = [], [], [], []
    ex = {"notif": 0, "conf": 0, "incub": 0, "serial": 0}
    for c in cases:
        if c.debut_symptomes and c.date_notification:
            notif.append((c.date_notification - c.debut_symptomes).days)
        else:
            ex["notif"] += 1
        if c.date_notification and c.date_confirmation:
            conf.append((c.date_confirmation - c.date_notification).days)
        else:
            ex["conf"] += 1
        if c.contact_connu in ("Contact connu", "Contact connu suivi"):
            if c.debut_symptomes and c.date_contact_source and c.date_contact_source <= c.debut_symptomes:
                incub.append((c.debut_symptomes - c.date_contact_source).days)
            else:
                ex["incub"] += 1
            src = by_code.get(_id(c.id_cas_source)) if c.id_cas_source else None
            if src and src.debut_symptomes and c.debut_symptomes:
                serial.append((c.debut_symptomes - src.debut_symptomes).days)
            else:
                ex["serial"] += 1
    return [
        Stat("Début des symptômes → notification", notif, ex["notif"],
             "délai de détection : plus il est court, moins le cas a eu de contacts non suivis"),
        Stat("Notification → confirmation", conf, ex["conf"], "circuit d'alerte, prélèvement et laboratoire"),
        Stat("Incubation observée", incub, ex["incub"],
             "contacts connus : début des symptômes − dernier contact avec le cas source"),
        Stat("Intervalle sériel", serial, ex["serial"],
             "début des symptômes du cas − celui de son cas source enregistré dans l'outil"),
    ]
