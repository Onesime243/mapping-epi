"""Liens entre cas : chaînes de transmission et lieux communs.

- Chaîne : le champ « ID du cas source » d'une fiche est comparé à l'ID (code_cas) des autres fiches.
  S'il correspond, les deux cas sont reliés (cas source → cas secondaire) ; sinon l'ID saisi devient
  une source « hors périmètre » (cas d'une autre zone, non saisi, ou ID mal orthographié).
  Le trait du lien suit le statut de contact : contact connu suivi, contact connu, autre.
- Lieux communs : lieux (chronologie + onglet Lieux) fréquentés par au moins deux cas, avec la période
  de chaque cas lors du passage (contagieux / fenêtre d'exposition). Un lieu où un cas était contagieux
  et un autre dans sa fenêtre d'exposition, à une date compatible, est signalé « transmission possible » :
  piste à investiguer, pas une preuve.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from core import rules
from core.lieux import VAGUES, case_label, cle
from core.models import Case


def case_long_label(c: Case) -> str:
    return f"{case_label(c)} · ZS {c.zs or '?'}"


def _id(s: str) -> str:
    return cle(s).replace(" ", "")


# ---------------------------------------------------------------------------
# Chaînes de transmission
# ---------------------------------------------------------------------------
@dataclass
class Node:
    key: str                      # id interne du cas, ou « src:<ID> » pour une source hors périmètre
    case: Optional[Case] = None
    label: str = ""
    children: List["Node"] = field(default_factory=list)
    lien: str = ""                # statut de contact du cas enfant (Contact connu suivi, Contact connu…)
    gen: int = 0


@dataclass
class Chains:
    roots: List[Node]             # racines des chaînes (au moins un cas secondaire)
    isolated: List[Case]          # cas sans aucun lien
    edges: List[Tuple[str, str]]  # (parent, enfant) entre cas présents
    ignored: List[str]            # liens écartés (boucle, ID en double)


def build_chains(cases: List[Case]) -> Chains:
    by_id = {c.id: c for c in cases}
    by_code: Dict[str, List[Case]] = defaultdict(list)
    for c in cases:
        if (c.code_cas or "").strip():
            by_code[_id(c.code_cas)].append(c)
    parent: Dict[str, str] = {}
    ignored: List[str] = []
    for c in cases:
        src = (c.id_cas_source or "").strip()
        if not src:
            continue
        hits = [x for x in by_code.get(_id(src), []) if x.id != c.id]
        if len(hits) > 1:
            ignored.append(f"ID source « {src} » porté par {len(hits)} fiches : lien de {case_label(c)} ignoré")
            continue
        parent[c.id] = hits[0].id if hits else "src:" + _id(src)
    # boucles : on coupe le lien qui referme le cycle
    for cid in list(parent):
        seen, cur = {cid}, parent.get(cid)
        while cur and not cur.startswith("src:"):
            if cur in seen:
                ignored.append(f"{case_long_label(by_id[cid])} : boucle dans les cas sources (lien ignoré)")
                parent.pop(cid, None)
                break
            seen.add(cur)
            cur = parent.get(cur)

    nodes: Dict[str, Node] = {c.id: Node(c.id, c, case_long_label(c)) for c in cases}
    for cid, pid in parent.items():
        if pid.startswith("src:") and pid not in nodes:
            nodes[pid] = Node(pid, None, by_id[cid].id_cas_source.strip())
    for cid, pid in parent.items():
        child = nodes[cid]
        child.lien = by_id[cid].contact_connu
        nodes[pid].children.append(child)

    def j0(n: Node):
        return (n.case.debut_symptomes if n.case and n.case.debut_symptomes else date.max, n.label)

    for n in nodes.values():
        n.children.sort(key=j0)
    roots = sorted((n for k, n in nodes.items() if k not in parent and n.children), key=j0)

    def set_gen(n: Node, g: int):
        n.gen = g
        for ch in n.children:
            set_gen(ch, g + 1)
    for r in roots:
        set_gen(r, 0)
    linked = set(parent) | set(parent.values())
    isolated = sorted((c for c in cases if c.id not in linked), key=lambda c: (c.debut_symptomes or date.max))
    edges = [(p, c) for c, p in parent.items() if not p.startswith("src:")]
    return Chains(roots, isolated, edges, ignored)


def serial_interval(parent: Optional[Case], child: Optional[Case]) -> Optional[int]:
    """Jours entre les J0 rapportés du cas source et du cas secondaire."""
    if parent and child and parent.debut_symptomes and child.debut_symptomes:
        return (child.debut_symptomes - parent.debut_symptomes).days
    return None


# ---------------------------------------------------------------------------
# Lieux communs
# ---------------------------------------------------------------------------
@dataclass
class Visit:
    case: Case
    debut: Optional[date]
    fin: Optional[date]
    phase: str                    # « contagieux », « exposition » ou ""
    quoi: str


@dataclass
class SharedPlace:
    name: str
    visits: List[Visit]
    pistes: List[Tuple[Case, Case]] = field(default_factory=list)   # (contagieux, exposé)

    @property
    def cases(self) -> List[Case]:
        out: List[Case] = []
        for v in self.visits:
            if v.case not in out:
                out.append(v.case)
        return out


def _visits(c: Case) -> Dict[str, Tuple[str, List[Visit]]]:
    w = rules.windows(c)
    out: Dict[str, Tuple[str, List[Visit]]] = {}

    def add(name: str, v: Visit):
        name = (name or "").strip()
        key = cle(name)
        if key in VAGUES:
            return
        out.setdefault(key, (name, []))[1].append(v)

    for ev in c.events:
        for loc in (ev.lieu, ev.lieu_arrivee):
            add(loc, Visit(c, ev.date_debut, ev.date_fin or ev.date_debut, rules.event_phase(ev, w),
                           ev.titre or ev.type))
    for p in c.places:
        if cle(p.nom) not in out:
            add(p.nom, Visit(c, None, None, "", p.type))
    return out


def shared_places(cases: List[Case], focus: Optional[Case] = None) -> List[SharedPlace]:
    where: Dict[str, List[Visit]] = defaultdict(list)
    names: Dict[str, str] = {}
    for c in cases:
        for key, (disp, visits) in _visits(c).items():
            names.setdefault(key, disp)
            where[key].extend(visits)
    out: List[SharedPlace] = []
    for key, visits in where.items():
        ids = {v.case.id for v in visits}
        if len(ids) < 2 or (focus and focus.id not in ids):
            continue
        sp = SharedPlace(names[key], sorted(visits, key=lambda v: (v.debut or date.max)))
        for a in visits:
            for b in visits:
                if a.case.id == b.case.id or a.phase != "contagieux" or b.phase != "exposition":
                    continue
                if a.debut and b.fin and b.fin >= a.debut and (a.case, b.case) not in sp.pistes:
                    sp.pistes.append((a.case, b.case))
        out.append(sp)
    out.sort(key=lambda s: (-bool(s.pistes), -len(s.cases), s.name.lower()))
    return out
