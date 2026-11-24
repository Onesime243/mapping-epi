"""Tableau de bord : « Vue d'ensemble » (tour de contrôle des chefs de section et de pilier).

Tout est calculé à partir des fiches du périmètre et de la période (mêmes règles que le reste du tableau de bord) :
une donnée non renseignée n'est jamais comptée comme 0, elle est signalée « ? ». Chaque indicateur renvoie à la liste
des cas concernés (paramètre `focus`).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape as e
from statistics import mean, median
from typing import Dict, List, Optional, Tuple

from config import theme
from core import indicateurs as IND
from core import pyramide, rules
from core import tableau_bord as TB
from core.langue import tr, trf
from core.models import Case

CIBLE_COMPLETUDE = 95
SEUIL_LETALITE = 20
NAVY, RED, DRED, ORA, AMB, YEL, GRN, GREY = "#1F3A5F", "#C8202A", "#9B1B1B", "#E0492B", "#F28C28", "#F2C94C", "#2E8B57", "#9AA5B1"
CONNU = theme.CONTACT_AVEC_SOURCE


# ---------------------------------------------------------------------------------------------------------------------
# filtres croisés (AS, statut, risque, lien) : appliqués avant tout calcul
# ---------------------------------------------------------------------------------------------------------------------
def lien(c: Case) -> str:
    if c.contact_connu in CONNU:
        return "connu"
    return "inconnu" if c.contact_connu == "Non contact" else "investiguer"


def risque(c: Case) -> str:
    try:
        return rules.global_risk(c)[0]
    except Exception:
        return "Inconnu"


def filtrer(cases: List[Case], aire: str = "", statut: str = "", niveau_risque: str = "", lien_epi: str = "") -> List[Case]:
    out = []
    for c in cases:
        if aire and pyramide.norm(c.aire_sante) != pyramide.norm(aire):
            continue
        if statut and c.issue != statut:
            continue
        if niveau_risque and risque(c) != niveau_risque:
            continue
        if lien_epi and lien(c) != lien_epi:
            continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# petits graphiques SVG (mêmes couleurs que le mapping)
# ---------------------------------------------------------------------------------------------------------------------
def svg_barres(vals: List[Optional[float]], labels: List[str], couleurs: Optional[List[str]] = None, fmt: str = "{:.0f}",
               seuil: Optional[float] = None, w: int = 340, h: int = 150, px: int = 150) -> str:
    if not vals:
        return f'<p class="muted">{e(tr("Aucune donnée sur la période."))}</p>'
    connus = [v for v in vals if v is not None]
    m = max(connus + ([seuil] if seuil else []) + [1]) * 1.18
    bw = (w - 30) / len(vals)
    s = [f'<svg viewBox="0 0 {w} {h + 22}" width="100%" style="height:{px}px" role="img">']
    for i in range(5):
        y = 8 + (h - 8) * i / 4
        s.append(f'<line x1="26" x2="{w}" y1="{y:.0f}" y2="{y:.0f}" stroke="#E6EBF1"/>'
                 f'<text x="22" y="{y + 4:.0f}" font-size="10" text-anchor="end" fill="#5F6B7A">{m * (4 - i) / 4:.0f}</text>')
    for i, v in enumerate(vals):
        x = 30 + i * bw + bw * .15
        lab = e(labels[i][:12])
        s.append(f'<text x="{x + bw * .35:.1f}" y="{h + 15}" font-size="10.5" text-anchor="middle" fill="#3D4852">{lab}<title>{e(labels[i])}</title></text>')
        if v is None:
            s.append(f'<text x="{x + bw * .35:.1f}" y="{h - 6}" font-size="12" font-weight="700" text-anchor="middle" fill="#5F6B7A">?</text>')
            continue
        bh = (h - 8) * v / m
        c = couleurs[i] if couleurs else "#3E6FB0"
        s.append(f'<rect x="{x:.1f}" y="{h - bh:.1f}" width="{bw * .7:.1f}" height="{bh:.1f}" rx="2" fill="{c}"/>'
                 f'<text x="{x + bw * .35:.1f}" y="{h - bh - 4:.1f}" font-size="10.5" font-weight="700" text-anchor="middle" fill="#1F2933">{fmt.format(v)}</text>')
    if seuil:
        y = h - (h - 8) * seuil / m
        s.append(f'<line x1="26" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{RED}" stroke-dasharray="5 4" stroke-width="1.6"/>'
                 f'<text x="{w - 2}" y="{y - 4:.1f}" font-size="10" text-anchor="end" fill="{RED}" font-weight="700">'
                 f'{e(trf("seuil {s} j", s=seuil))}</text>')
    return "".join(s) + "</svg>"


def svg_ligne(points: List[Tuple[date, int]], w: int = 560, h: int = 140, px: int = 140) -> str:
    if not points or not any(v for _d, v in points):
        return f'<p class="muted">{e(tr("Aucun contact avec une date de dernier contact sur ces 21 jours."))}</p>'
    vals = [v for _d, v in points]
    m = max(vals) * 1.18 or 1
    pts = [(30 + i * (w - 36) / max(1, len(vals) - 1), 8 + (h - 8) * (1 - v / m)) for i, v in enumerate(vals)]
    s = [f'<svg viewBox="0 0 {w} {h + 20}" width="100%" style="height:{px}px" role="img">']
    for i in range(4):
        y = 8 + (h - 8) * i / 3
        s.append(f'<line x1="26" x2="{w}" y1="{y:.0f}" y2="{y:.0f}" stroke="#E6EBF1"/><text x="22" y="{y + 4:.0f}" font-size="10" text-anchor="end" fill="#5F6B7A">{m * (3 - i) / 3:.0f}</text>')
    s.append(f'<polygon points="{pts[0][0]:.1f},{h} ' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
             + f' {pts[-1][0]:.1f},{h}" fill="#2C5F9E" fill-opacity=".12"/>')
    s.append('<polyline fill="none" stroke="#2C5F9E" stroke-width="2.2" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
    for i in range(0, len(points), max(1, len(points) // 5)):
        s.append(f'<text x="{pts[i][0]:.0f}" y="{h + 15}" font-size="10" text-anchor="middle" fill="#5F6B7A">{points[i][0]:%d/%m}</text>')
    x, y = pts[-1]
    s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{NAVY}"/><text x="{x - 6:.1f}" y="{y - 8:.1f}" font-size="11" '
             f'text-anchor="end" font-weight="800" fill="{NAVY}">{vals[-1]}</text>')
    return "".join(s) + "</svg>"


def svg_camembert(parts: List[Tuple[str, int, str]]) -> str:
    tot = sum(v for _l, v, _c in parts)
    if not tot:
        return f'<p class="muted">{e(tr("Aucun cas sur la période."))}</p>'
    a, r = -math.pi / 2, 58
    s = ['<svg viewBox="0 0 310 140" width="100%" style="height:120px" role="img">']
    for l, v, c in parts:
        if not v:
            continue
        b = a + 2 * math.pi * v / tot
        if v == tot:
            s.append(f'<circle cx="70" cy="70" r="{r}" fill="{c}"/>')
        else:
            x0, y0, x1, y1 = 70 + r * math.cos(a), 70 + r * math.sin(a), 70 + r * math.cos(b), 70 + r * math.sin(b)
            s.append(f'<path d="M70 70 L{x0:.1f} {y0:.1f} A{r} {r} 0 {1 if b - a > math.pi else 0} 1 {x1:.1f} {y1:.1f} Z" '
                     f'fill="{c}" stroke="#fff" stroke-width="2"/>')
        a = b
    s.append(f'<circle cx="70" cy="70" r="28" fill="#fff"/><text x="70" y="75" font-size="15" font-weight="800" text-anchor="middle">{tot}</text>')
    for i, (l, v, c) in enumerate(parts):
        s.append(f'<rect x="150" y="{30 + i * 26}" width="12" height="12" rx="3" fill="{c}"/><text x="168" y="{40 + i * 26}" '
                 f'font-size="12">{e(l)} : <tspan font-weight="700">{v}</tspan> ({round(100 * v / tot)} %)</text>')
    return "".join(s) + "</svg>"


def spark(vals: List[int]) -> str:
    if len(vals) < 2 or not max(vals):
        return ""
    m = max(vals)
    pts = " ".join(f"{4 + i * 140 / (len(vals) - 1):.1f},{34 - 28 * v / m:.1f}" for i, v in enumerate(vals))
    return f'<svg viewBox="0 0 150 38" width="150" height="38" aria-hidden="true"><polyline fill="none" stroke="{GRN}" stroke-width="2.2" points="{pts}"/></svg>'


# ---------------------------------------------------------------------------------------------------------------------
# calculs
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Kpi:
    cle: str
    titre: str
    valeur: str
    detail: str
    ton: str = ""                 # "" | warn | alert
    bandeau: str = ""             # bandeau sous la tuile (alerte)
    bandeau_ton: str = ""         # "" (rouge) | o (orange)
    graphe: str = ""


@dataclass
class Vue:
    n: int
    completude: Optional[float]
    kpis: List[Kpi] = field(default_factory=list)
    carte: str = ""
    semaines: str = ""
    delais_zs: str = ""
    lien: str = ""
    notification: List[Tuple[str, str, bool]] = field(default_factory=list)
    contacts_cat: str = ""
    contacts_cat_info: str = ""
    actifs: str = ""
    top_zs: List[Tuple[str, int, Optional[int]]] = field(default_factory=list)
    pci: Dict[str, int] = field(default_factory=dict)
    sites: List[dict] = field(default_factory=list)
    actions: List[dict] = field(default_factory=list)
    qualite: List[Tuple[str, float]] = field(default_factory=list)
    qualite_svg: str = ""
    priorites: List[dict] = field(default_factory=list)
    prise_en_charge: List[Tuple[str, str, bool]] = field(default_factory=list)
    vaccination: List[Tuple[str, str, bool]] = field(default_factory=list)
    focus: Dict[str, List[Tuple[Case, str]]] = field(default_factory=dict)


def _moy(xs: List[float]) -> Optional[float]:
    return mean(xs) if xs else None


def _j(v: Optional[float]) -> str:
    return "?" if v is None else f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " " + tr("j")


def _isolement(c: Case) -> Optional[int]:
    if not c.debut_symptomes:
        return None
    ds = [ev.date_debut for ev in c.events if ev.type == "Hospitalisation" and ev.date_debut]
    d = min(ds) if ds else None
    return (d - c.debut_symptomes).days if d and d >= c.debut_symptomes else None


def actifs_jour(cases: List[Case], ref: date, jours: int = 21) -> List[Tuple[date, int]]:
    """Contacts encore dans leur période de suivi, jour par jour (date du dernier contact + 21 jours)."""
    fenetres = []
    for c in cases:
        for g in c.contacts:
            fin = rules.contact_followup_end(g, c)
            if g.dernier_contact and fin and g.nombre:
                fenetres.append((g.dernier_contact, fin, g.nombre))
    out = []
    for k in range(jours - 1, -1, -1):
        d = ref - timedelta(days=k)
        out.append((d, sum(n for a, b, n in fenetres if a <= d <= b)))
    return out


def construire(cases: List[Case], debut: date, fin: date, cases_perimetre: List[Case], niveau_carte: tuple,
               ref: Optional[date] = None) -> Vue:
    ref = ref or date.today()
    n = len(cases)
    comps = [rules.completeness(c)[0] for c in cases]
    v = Vue(n=n, completude=_moy(comps))
    foc: Dict[str, List[Tuple[Case, str]]] = defaultdict(list)

    # -- ligne 1 : indicateurs clés
    notif = {c.id: IND.date_notification(c)[0] for c in cases}
    n24 = sum(1 for c in cases if notif[c.id] and notif[c.id] >= ref - timedelta(days=1))
    n7 = sum(1 for c in cases if notif[c.id] and notif[c.id] >= ref - timedelta(days=6))
    lundi = fin - timedelta(days=fin.weekday())
    cumul, tot = [], 0
    hors = [c for c in cases_perimetre if not c.exemple()]
    for k in range(7, -1, -1):
        d0 = lundi - timedelta(days=7 * k)
        tot += sum(1 for c in hors if (lambda d: d and d0 <= d <= d0 + timedelta(days=6))(IND.date_notification(c)[0]))
        cumul.append(tot)
    for c in cases:
        foc["confirmes"].append((c, f"{notif[c.id]:%d/%m/%Y}" if notif[c.id] else "?"))
    v.kpis.append(Kpi("confirmes", tr("Cas confirmés"), str(n), trf("+{a} en 24 h · +{b} en 7 j", a=n24, b=n7), graphe=spark(cumul)))

    deces = [c for c in cases if c.issue == "Décès"]
    let = 100 * len(deces) / n if n else None
    foc["deces"] = [(c, f"{c.date_deces:%d/%m/%Y}" if c.date_deces else "?") for c in deces]
    v.kpis.append(Kpi("deces", tr("Décès (létalité)"), str(len(deces)),
                      trf("{p} % des cas", p=f"{let:.1f}".replace(".", ",")) if let is not None else "?",
                      "warn" if deces else "",
                      trf("au-dessus du seuil de vigilance ({s} %)", s=SEUIL_LETALITE) if let and let > SEUIL_LETALITE else "", "o"))

    delais = {c.id: TB.delai_conf(c) for c in cases}
    connus = [d for d in delais.values() if d is not None]
    seuil = TB.SEUILS["delai_conf"]
    au_dessus = [c for c in cases if delais[c.id] is not None and delais[c.id] > seuil]
    foc["delai"] = sorted([(c, f"{delais[c.id]} {tr('j')}") for c in au_dessus], key=lambda x: -delais[x[0].id])
    moy = _moy(connus)
    v.kpis.append(Kpi("delai", tr("Délai signes → confirmation"), _j(moy),
                      (trf("moyenne · médiane {m} · {k} cas > {s} j", m=_j(median(connus)), k=len(au_dessus), s=seuil)
                       if connus else tr("non renseigné dans les fiches")),
                      "alert" if moy is not None and moy > seuil else "",
                      trf("ALERTE · seuil {s} jours", s=seuil) if moy is not None and moy > seuil else ""))

    inconnus = [c for c in cases if lien(c) != "connu"]
    foc["lien"] = [(c, tr("non contact") if c.contact_connu == "Non contact" else tr("à investiguer")) for c in inconnus]
    v.kpis.append(Kpi("lien", tr("Lien épidémiologique inconnu"), str(len(inconnus)),
                      trf("{p} % des cas", p=round(100 * len(inconnus) / n)) if n else "?",
                      "warn" if inconnus else ""))

    hr_actifs, hr_cas = 0, []
    for c in cases:
        k = 0
        for g in c.contacts:
            fin_s = rules.contact_followup_end(g, c)
            if g.risque in TB.HAUT_RISQUE and g.nombre and fin_s and fin_s >= ref:
                k += g.nombre
        if k:
            hr_actifs += k
            hr_cas.append((c, trf("{n} contacts à haut risque en suivi", n=k)))
    foc["contacts"] = hr_cas
    v.kpis.append(Kpi("contacts", tr("Contacts à haut risque"), str(hr_actifs),
                      trf("en suivi actif (21 j) · {n} cas concernés", n=len(hr_cas))))

    critiques = [(c, s) for c in cases for s in c.ipc if s.statut in ("Non", "Inconnu")]
    foc["pci"] = [(c, f"{s.site or '?'} : {tr(s.statut)}") for c, s in critiques]
    v.kpis.append(Kpi("pci", tr("Sites PCI critiques"), str(len(critiques)), tr("non faits ou statut inconnu"),
                      "alert" if critiques else ""))

    # -- épidémiologie
    from core import carte as CARTE
    niv, prov, zs = niveau_carte
    try:
        v.carte = CARTE.svg_niveau(CARTE.construire(cases, {}), niv, prov, zs, ref, width=760, height=600)
    except Exception:
        v.carte = ""
    v.semaines = TB.svg_semaines(TB._semaines(cases, max(debut, fin - timedelta(days=55)), fin), 520, 200)
    par_zs: Dict[str, List[int]] = defaultdict(list)
    for c in cases:
        if delais[c.id] is not None:
            par_zs[c.zs or "?"].append(delais[c.id])
    top = sorted(par_zs.items(), key=lambda kv: -len(kv[1]))[:7]
    moyz = [mean(x) for _z, x in top]
    v.delais_zs = svg_barres(moyz, [z for z, _x in top],
                             [DRED if m > 2 * seuil else ORA if m > seuil else GRN for m in moyz], "{:.0f} j", seuil, px=130)
    v.lien = svg_camembert([(tr("Connu"), sum(1 for c in cases if lien(c) == "connu"), NAVY),
                            (tr("Inconnu (non contact)"), sum(1 for c in cases if lien(c) == "inconnu"), DRED),
                            (tr("À investiguer"), sum(1 for c in cases if lien(c) == "investiguer"), GREY)])
    rap, ret, ecart, tard = [], [], [], 0
    for c in cases:
        dn = notif[c.id]
        if dn and c.debut_symptomes:
            rap.append((dn - c.debut_symptomes).days)
            if (dn - c.debut_symptomes).days > 3:
                tard += 1
        j0r = rules.j0_retenu(c)
        if dn and j0r:
            ret.append((dn - j0r).days)
        if c.debut_symptomes and j0r:
            ecart.append(abs((c.debut_symptomes - j0r).days))
    v.notification = [(tr("J0 rapporté → notification"), _j(_moy(rap)), False),
                      (tr("J0 retenu → notification"), _j(_moy(ret)), False),
                      (tr("Écart J0 rapporté / retenu"), _j(_moy(ecart)), bool(ecart and _moy(ecart) > 0)),
                      (tr("Cas notifiés plus de 3 j après J0"), str(tard) if rap else "?", tard > 0)]

    # -- contacts
    cat_n: Counter = Counter()
    cat_s: Counter = Counter()
    for c in cases:
        for g in c.contacts:
            if g.nombre and g.suivis is not None:
                cat_n[g.categorie or "?"] += g.nombre
                cat_s[g.categorie or "?"] += min(g.suivis, g.nombre)
    cats = [k for k, _ in cat_n.most_common(7)]
    pcts = [100 * cat_s[k] / cat_n[k] for k in cats]
    v.contacts_cat = svg_barres(pcts, [tr(k) for k in cats], [GRN if p >= 90 else AMB if p >= 50 else DRED for p in pcts],
                                "{:.0f} %", w=560, px=150)
    sans = sum(1 for c in cases for g in c.contacts if g.nombre and g.suivis is None)
    v.contacts_cat_info = trf("{n} groupe(s) sans nombre de suivis : non comptés", n=sans) if sans else ""
    v.actifs = svg_ligne(actifs_jour(cases, ref))
    zs_act: Dict[str, int] = Counter()
    zs_lister: Dict[str, Optional[int]] = {}
    for c in cases:
        for g in c.contacts:
            fin_s = rules.contact_followup_end(g, c)
            if g.nombre and fin_s and fin_s >= ref:
                zs_act[c.zs or "?"] += g.nombre
            if g.nombre is not None and g.suivis is not None:
                zs_lister[c.zs or "?"] = (zs_lister.get(c.zs or "?") or 0) + max(0, g.nombre - g.suivis)
    v.top_zs = [(z, k, zs_lister.get(z)) for z, k in zs_act.most_common(5)]

    # -- PCI et opérations
    v.pci = dict(Counter(s.statut for c in cases for s in c.ipc))
    v.sites = [{"site": s.site or "?", "zs": c.zs or "?", "statut": s.statut, "cid": c.id, "code": TB._code(c)}
               for c, s in sorted(critiques, key=lambda x: (x[1].statut != "Non", x[0].zs))][:8]
    acts = [(c, a) for c in cases for a in c.actions if a.texte.strip() and a.priorite in ("Urgent", "Important")]
    grp: Dict[Tuple[str, str], dict] = {}
    for c, a in acts:
        k = (a.priorite, a.texte.strip())
        d = grp.setdefault(k, {"priorite": a.priorite, "texte": a.texte.strip(), "faites": 0, "total": 0, "retard": 0})
        d["total"] += 1
        cat = TB.categorie_action(a, ref)[0]
        d["faites"] += a.statut == "Fait"
        d["retard"] += cat == "retard"
    v.actions = sorted(grp.values(), key=lambda d: (d["priorite"] != "Urgent", -d["retard"], -d["total"]))[:6]
    par_q: Dict[str, List[int]] = defaultdict(list)
    for c, q in zip(cases, comps):
        par_q[c.zs or "?"].append(q)
    v.qualite = sorted(((z, mean(x)) for z, x in par_q.items()), key=lambda zq: zq[1])[:6]
    v.qualite_svg = svg_barres([q for _z, q in v.qualite], [z for z, _q in v.qualite],
                               [GRN if q >= CIBLE_COMPLETUDE else AMB if q >= 85 else DRED for _z, q in v.qualite],
                               "{:.0f} %", w=340, px=170)

    # -- priorités (risque × délai)
    rang = {"Très élevé": 0, "Élevé": 1}
    for c in cases:
        r = risque(c)
        if r not in rang:
            continue
        motifs = []
        if delais[c.id] is not None and delais[c.id] > seuil:
            motifs.append(trf("délai {d} j", d=delais[c.id]))
        urg = [a for a in c.actions if a.priorite == "Urgent" and a.statut != "Fait" and a.texte.strip()]
        if urg:
            motifs.append(trf("{n} action(s) urgente(s) ouverte(s)", n=len(urg)))
        if lien(c) != "connu":
            motifs.append(tr("lien inconnu"))
        if any(s.statut == "Non" for s in c.ipc):
            motifs.append(tr("site PCI non fait"))
        if motifs:
            v.priorites.append({"cid": c.id, "code": TB._code(c), "zs": c.zs or "?", "risque": r,
                                "delai": delais[c.id], "motifs": " · ".join(motifs), "rang": rang[r]})
    v.priorites.sort(key=lambda d: (d["rang"], -(d["delai"] or 0)))
    foc["priorites"] = [(next(c for c in cases if c.id == d["cid"]), d["motifs"]) for d in v.priorites]
    v.priorites = v.priorites[:10]

    # -- prise en charge, laboratoire, EDS
    iso = [x for x in (_isolement(c) for c in cases) if x is not None]
    lab = [h / 24 for h in (rules.lab_delay_hours(c) for c in cases) if h is not None]
    morts_ent = [c for c in deces if any(ev.type == "Enterrement" for ev in c.events)]
    eds = sum(1 for c in morts_ent if all(ev.securise for ev in c.events if ev.type == "Enterrement"))
    soignants = [c for c in cases if c.agent_sante == "Oui"]
    foc["soignants"] = [(c, c.agent_sante_structure or tr("agent de santé")) for c in soignants]
    v.prise_en_charge = [(tr("Délai signes → hospitalisation (médiane)"), _j(median(iso)) if iso else "?", False),
                         (tr("Délai prélèvement → résultat (médiane)"), _j(median(lab)) if lab else "?", False),
                         (tr("Enterrements dignes et sécurisés"), f"{eds} / {len(morts_ent)}" if morts_ent else "?",
                          bool(morts_ent) and eds < len(morts_ent)),
                         (tr("Agents de santé parmi les cas"), str(len(soignants)), bool(soignants)),
                         (tr("Cas vaccinés avant la maladie"), str(sum(1 for c in cases if c.vaccine == "Oui")), False)]
    vac_n = sum(g.nombre for c in cases for g in c.contacts if g.nombre and g.vaccines is not None)
    vac_v = sum(min(g.vaccines, g.nombre) for c in cases for g in c.contacts if g.nombre and g.vaccines is not None)
    sans_anneau = [c for c in cases if not c.date_debut_anneau]
    anneaux_sem = sum(1 for c in cases if c.date_debut_anneau and c.date_debut_anneau >= ref - timedelta(days=6))
    foc["anneau"] = [(c, tr("pas de date de début d'anneau")) for c in sans_anneau]
    v.vaccination = [(tr("Contacts vaccinés / contacts (groupes renseignés)"), f"{vac_v} / {vac_n}" if vac_n else "?", False),
                     (tr("Couverture"), f"{round(100 * vac_v / vac_n)} %" if vac_n else "?", bool(vac_n) and vac_v / vac_n < .8),
                     (tr("Anneaux ouverts ces 7 derniers jours"), str(anneaux_sem), False),
                     (tr("Cas sans date de début d'anneau"), str(len(sans_anneau)), bool(sans_anneau))]
    v.focus = dict(foc)
    return v


TITRES_FOCUS = {"confirmes": "Cas confirmés de la période", "deces": "Cas décédés", "delai": "Cas confirmés plus de 5 jours après les premiers signes",
                "lien": "Cas sans lien épidémiologique connu", "contacts": "Cas avec contacts à haut risque en suivi",
                "pci": "Sites PCI critiques (non faits ou statut inconnu)", "priorites": "Cas à traiter en priorité",
                "soignants": "Agents de santé parmi les cas", "anneau": "Cas sans date de début d'anneau"}
