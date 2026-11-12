"""Riposte : indicateurs clés (OMS), courbe épidémique, suivi des actions.

Calculs en lecture seule sur les fiches : rien n'est modifié, aucune donnée n'est inventée.
Une information non renseignée est comptée à part (« non renseigné ») et n'entre pas dans le pourcentage.
Les cibles affichées sont indicatives (repères habituels des ripostes Ebola) : à valider par la coordination.
"""
from __future__ import annotations

import html
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median
from typing import Dict, List, Optional, Tuple

from config import theme
from core import indicateurs as IND
from core import rules
from core.models import Action, Case

CONTACTS = ("Contact connu", "Contact connu suivi")
PRIO = {"Urgent": 0, "Important": 1, "Normal": 2}


# ---------------------------------------------------------------------------
# outils
# ---------------------------------------------------------------------------
def date_debut(c: Case) -> Tuple[Optional[date], str]:
    """Date utilisée pour la courbe : J0 retenu, à défaut la date de notification."""
    try:
        j0 = rules.j0_retenu(c)
    except Exception:
        j0 = None
    if j0:
        return j0, "J0"
    d, _src = IND.date_notification(c)
    return d, "notification" if d else ""


def date_isolement(c: Case) -> Optional[date]:
    """Première hospitalisation (isolement) à partir du début des symptômes rapporté."""
    ds = [e.date_debut for e in c.events if e.type == "Hospitalisation" and e.date_debut
          and (not c.debut_symptomes or e.date_debut >= c.debut_symptomes)]
    return min(ds) if ds else None


def deces_communautaire(c: Case) -> Optional[bool]:
    """Décès hors structure : aucun passage en hospitalisation avant (ou le jour du) décès. None si pas décédé."""
    if c.issue != "Décès":
        return None
    hosp = [e.date_debut for e in c.events if e.type == "Hospitalisation"]
    if not hosp:
        return True
    if c.date_deces:
        return not any(d and d <= c.date_deces for d in hosp)
    return False


def enterrement_securise(c: Case) -> Optional[bool]:
    ent = [e for e in c.events if e.type == "Enterrement"]
    if c.issue != "Décès" or not ent:
        return None
    return any(e.securise for e in ent)


def filtrer(cases: List[Case], periode: Optional[int], ref: date, province: str = "") -> List[Case]:
    """Cas de la province (si demandée) notifiés dans les `periode` derniers jours (None : tous)."""
    from core import pyramide
    out = []
    for c in cases:
        if province and pyramide.norm(c.province) != pyramide.norm(province):
            continue
        if periode:
            d, _ = IND.date_notification(c)
            if not d or d > ref or (ref - d).days >= periode:
                continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# indicateurs clés
# ---------------------------------------------------------------------------
@dataclass
class Indic:
    groupe: str
    nom: str
    num: Optional[float] = None       # numérateur (ou valeur, pour une médiane)
    den: Optional[int] = None         # dénominateur ; None : valeur simple (médiane, nombre)
    inconnus: int = 0
    cible: str = ""
    bon: str = "haut"                 # « haut » : plus c'est haut, mieux c'est ; « bas » ; « info »
    vert: Optional[float] = None      # seuil « atteint »
    orange: Optional[float] = None    # seuil « à surveiller »
    unite: str = "%"
    note: str = ""
    cas: List[str] = field(default_factory=list)    # N° EPID des cas qui posent problème

    @property
    def valeur(self) -> Optional[float]:
        if self.den is None:
            return self.num
        return (100.0 * self.num / self.den) if self.den else None

    def texte(self) -> str:
        v = self.valeur
        if v is None:
            return "?"
        if self.den is None:
            return f"{v:g} {self.unite}".strip()
        return f"{v:.0f} % ({int(self.num)}/{self.den})"

    @property
    def statut(self) -> str:
        """ok / attention / alerte / info."""
        v = self.valeur
        if v is None or self.bon == "info" or self.vert is None:
            return "info"
        if self.bon == "haut":
            return "ok" if v >= self.vert else ("attention" if v >= self.orange else "alerte")
        return "ok" if v <= self.vert else ("attention" if v <= self.orange else "alerte")


def _code(c: Case) -> str:
    return c.code_cas or c.titre_court()


def indicateurs(cases: List[Case]) -> List[Indic]:
    out: List[Indic] = []
    n = len(cases)

    # -- détection et lien épidémiologique
    connus = [c for c in cases if c.contact_connu != "Inconnu"]
    cc = [c for c in connus if c.contact_connu in CONTACTS]
    out.append(Indic("Détection", "Nouveaux cas déjà connus comme contacts", len(cc), len(connus),
                     n - len(connus), "100 %", "haut", 80, 50,
                     note="part des cas qui figuraient sur une liste de contacts : mesure si la riposte devance l'épidémie",
                     cas=[_code(c) for c in connus if c.contact_connu not in CONTACTS]))
    suivis = [c for c in cc if c.contact_connu == "Contact connu suivi"]
    out.append(Indic("Détection", "Parmi eux, contacts suivis au moment de la maladie", len(suivis), len(cc), 0,
                     "100 %", "haut", 80, 50, note="contact connu ET suivi quotidiennement avant le début des signes",
                     cas=[_code(c) for c in cc if c.contact_connu != "Contact connu suivi"]))
    nc = [c for c in connus if c.contact_connu == "Non contact"]
    out.append(Indic("Détection", "Cas sans lien épidémiologique connu", len(nc), len(connus), n - len(connus),
                     "0 %", "bas", 10, 25,
                     note="chaînes de transmission invisibles : investigation approfondie de la source",
                     cas=[_code(c) for c in nc]))

    # -- délais
    iso, sans_iso = [], []
    for c in cases:
        d = date_isolement(c)
        if c.debut_symptomes and d:
            iso.append((d - c.debut_symptomes).days)
        else:
            sans_iso.append(c)
    out.append(Indic("Délais", "Délai médian début des symptômes → isolement", median(iso) if iso else None, None,
                     len(sans_iso), "≤ 3 j", "bas", 3, 5, unite="j",
                     note=f"{len(iso)} cas avec une hospitalisation datée dans la chronologie"))
    rapides = [x for x in iso if x <= 3]
    out.append(Indic("Délais", "Cas isolés dans les 3 jours suivant le début des symptômes", len(rapides), len(iso),
                     len(sans_iso), "≥ 80 %", "haut", 80, 50,
                     note="plus l'isolement est tardif, plus le cas a eu de contacts dans la communauté"))
    notif = [(c.date_notification - c.debut_symptomes).days for c in cases if c.date_notification and c.debut_symptomes]
    out.append(Indic("Délais", "Délai médian début des symptômes → notification", median(notif) if notif else None,
                     None, n - len(notif), "≤ 3 j", "bas", 3, 5, unite="j"))

    # -- décès et enterrements
    dc = [c for c in cases if c.issue == "Décès"]
    com = [c for c in dc if deces_communautaire(c)]
    out.append(Indic("Décès", "Décès survenus dans la communauté", len(com), len(dc), 0, "0 %", "bas", 10, 25,
                     note="décès sans hospitalisation : cas non détectés à temps, risque élevé aux funérailles",
                     cas=[_code(c) for c in com]))
    ent = [(c, enterrement_securise(c)) for c in dc]
    connus_ent = [(c, s) for c, s in ent if s is not None]
    out.append(Indic("Décès", "Enterrements dignes et sécurisés", sum(1 for _c, s in connus_ent if s),
                     len(connus_ent), len(dc) - len(connus_ent), "100 %", "haut", 95, 80,
                     note="étape « Enterrement » de la chronologie, case « sécurisé » cochée",
                     cas=[_code(c) for c, s in connus_ent if not s]))

    # -- contacts
    listes = sum(g.nombre for c in cases for g in c.contacts if g.nombre is not None and g.suivis is not None)
    suiv = sum(g.suivis for c in cases for g in c.contacts if g.nombre is not None and g.suivis is not None)
    sans = sum(1 for c in cases for g in c.contacts if g.nombre is None or g.suivis is None)
    out.append(Indic("Contacts", "Contacts suivis parmi les contacts listés", suiv, listes, sans, "≥ 90 %", "haut",
                     90, 70, note="groupes de contacts dont le nombre listé et le nombre suivi sont renseignés"))
    dn = [c for c in cases if c.contacts]
    out.append(Indic("Contacts", "Cas avec au moins un groupe de contacts listé", len(dn), n, 0, "100 %", "haut",
                     95, 80, cas=[_code(c) for c in cases if not c.contacts]))

    # -- vaccination en anneau
    lv = sum(g.nombre for c in cases for g in c.contacts if g.nombre is not None and g.vaccines is not None)
    vv = sum(g.vaccines for c in cases for g in c.contacts if g.nombre is not None and g.vaccines is not None)
    sans_v = sum(1 for c in cases for g in c.contacts if g.vaccines is None)
    out.append(Indic("Vaccination en anneau", "Contacts vaccinés parmi les contacts listés", vv, lv, sans_v,
                     "≥ 90 %", "haut", 90, 70, note="colonne « Vaccinés » des groupes de contacts"))
    dl = [(c.date_debut_anneau - c.date_confirmation).days for c in cases
          if c.date_debut_anneau and c.date_confirmation and c.date_debut_anneau >= c.date_confirmation]
    out.append(Indic("Vaccination en anneau", "Délai médian confirmation → début de l'anneau",
                     median(dl) if dl else None, None, n - len(dl), "≤ 3 j", "bas", 3, 7, unite="j",
                     note="date « Début de la vaccination de l'anneau » de la fiche"))
    out.append(Indic("Vaccination en anneau", "Cas avec un anneau vacciné", len(dl), n, 0, "100 %", "haut", 90, 70,
                     cas=[_code(c) for c in cases if not c.date_debut_anneau]))

    # -- populations particulières
    ppl = [c for c in cases if c.agent_sante != "Inconnu"]
    out.append(Indic("Populations", "Cas parmi les agents de santé (PPL)", sum(1 for c in ppl if c.agent_sante == "Oui"),
                     len(ppl), n - len(ppl), "", "info",
                     note="infection d'un agent de santé : signal d'alerte sur la PCI dans la structure",
                     cas=[_code(c) for c in ppl if c.agent_sante == "Oui"]))
    vac = [c for c in cases if c.vaccine != "Inconnu"]
    out.append(Indic("Populations", "Cas vaccinés", sum(1 for c in vac if c.vaccine == "Oui"), len(vac),
                     n - len(vac), "", "info", note="statut vaccinal renseigné dans la fiche"))

    # -- séquençage
    sq = [c for c in cases if c.date_confirmation]
    out.append(Indic("Laboratoire", "Cas confirmés avec un résultat de séquençage", sum(1 for c in sq if c.sequencage.strip()),
                     len(sq), 0, "", "info", note="confirme ou corrige les chaînes de transmission"))

    # -- qualité des données
    comp = [rules.completeness(c)[0] for c in cases]
    out.append(Indic("Qualité des données", "Fiches complètes à 80 % ou plus", sum(1 for x in comp if x >= 80), n, 0,
                     "≥ 90 %", "haut", 90, 70,
                     cas=[_code(c) for c, x in zip(cases, comp) if x < 80]))
    return out


# ---------------------------------------------------------------------------
# nombre de reproduction observé (à partir des chaînes reliées dans l'outil)
# ---------------------------------------------------------------------------
@dataclass
class Reproduction:
    r: Optional[float]
    cas_utilises: int
    secondaires: int
    note: str


def reproduction(cases: List[Case], ref: Optional[date] = None, recul: int = 42) -> Reproduction:
    """Nombre moyen de cas secondaires reliés par cas, pour les cas assez anciens (début > `recul` jours)
    pour que leurs cas secondaires aient pu apparaître. Sous-estime si des liens ne sont pas saisis."""
    from core.links import _id
    ref = ref or date.today()
    enfants = Counter(_id(c.id_cas_source) for c in cases if c.id_cas_source.strip())
    anciens = []
    for c in cases:
        d, _src = date_debut(c)
        if d and (ref - d).days > recul and c.code_cas.strip():
            anciens.append(c)
    if not anciens:
        return Reproduction(None, 0, 0, f"aucun cas avec un début de maladie de plus de {recul} jours")
    sec = sum(enfants.get(_id(c.code_cas), 0) for c in anciens)
    return Reproduction(sec / len(anciens), len(anciens), sec,
                        f"{sec} cas secondaires reliés à {len(anciens)} cas de plus de {recul} jours ; sous-estimé si "
                        "des liens (ID du cas source) ne sont pas saisis")


# ---------------------------------------------------------------------------
# courbe épidémique
# ---------------------------------------------------------------------------
@dataclass
class Courbe:
    semaines: List[date]                       # lundi de chaque semaine
    series: "OrderedDict[str, List[int]]"     # ZS → nombre de cas par semaine
    deces: List[int]
    sans_date: int
    par_notification: int                      # cas placés par la date de notification (début inconnu)


def courbe(cases: List[Case], max_zs: int = 6) -> Courbe:
    dated = []
    sans, notif = 0, 0
    for c in cases:
        d, src = date_debut(c)
        if not d:
            sans += 1
            continue
        notif += src == "notification"
        dated.append((d - timedelta(days=d.weekday()), c))
    if not dated:
        return Courbe([], OrderedDict(), [], sans, notif)
    first, last = min(w for w, _ in dated), max(w for w, _ in dated)
    weeks = []
    w = first
    while w <= last:
        weeks.append(w)
        w += timedelta(days=7)
    idx = {w: i for i, w in enumerate(weeks)}
    tot = Counter(c.zs or "ZS ?" for _w, c in dated)
    top = [z for z, _n in tot.most_common(max_zs)]
    series: "OrderedDict[str, List[int]]" = OrderedDict((z, [0] * len(weeks)) for z in top)
    deces = [0] * len(weeks)
    for wk, c in dated:
        z = c.zs or "ZS ?"
        key = z if z in series else "Autres ZS"
        series.setdefault(key, [0] * len(weeks))[idx[wk]] += 1
        deces[idx[wk]] += c.issue == "Décès"
    return Courbe(weeks, series, deces, sans, notif)


PALETTE = [theme.BLUE, theme.ORANGE, theme.TEAL, theme.PURPLE, theme.YELLOW, theme.GREEN, theme.GREY]


def courbe_svg(cb: Courbe, width: int = 980, height: int = 330) -> str:
    if not cb.semaines:
        return '<p class="muted">Aucun cas daté : la courbe ne peut pas être tracée.</p>'
    ml, mr, mt, mb = 44, 16, 16, 64
    pw, ph = width - ml - mr, height - mt - mb
    n = len(cb.semaines)
    totals = [sum(s[i] for s in cb.series.values()) for i in range(n)]
    ymax = max(totals) or 1
    step = 1 if ymax <= 8 else 2 if ymax <= 16 else 5 if ymax <= 40 else 10
    ytop = ((ymax + step - 1) // step) * step
    bw = pw / n
    e = html.escape
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Courbe épidémique" '
           f'style="font-family:{e(theme.FONT_STACK)}; max-width:{width}px">']
    for v in range(0, ytop + 1, step):
        y = mt + ph - ph * v / ytop
        out.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{y:.1f}" y2="{y:.1f}" stroke="currentColor" '
                   f'stroke-opacity=".12"/><text x="{ml - 6}" y="{y + 4:.1f}" font-size="11" text-anchor="end" '
                   f'fill="currentColor" fill-opacity=".7">{v}</text>')
    colors = dict(zip(cb.series.keys(), PALETTE))
    for i in range(n):
        x = ml + i * bw + bw * 0.12
        w = bw * 0.76
        y = mt + ph
        for z, vals in cb.series.items():
            if vals[i]:
                h = ph * vals[i] / ytop
                y -= h
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{colors[z]}">'
                           f'<title>{e(z)} : {vals[i]} cas (semaine du {cb.semaines[i]:%d/%m/%Y})</title></rect>')
        if cb.deces[i]:
            out.append(f'<text x="{x + w / 2:.1f}" y="{y - 4:.1f}" font-size="10.5" text-anchor="middle" '
                       f'fill="{theme.RED}" font-weight="700">†{cb.deces[i]}</text>')
        if n <= 26 or i % max(1, n // 20) == 0:
            lx = x + w / 2
            out.append(f'<text x="{lx:.1f}" y="{mt + ph + 14}" font-size="10.5" text-anchor="end" fill="currentColor" '
                       f'fill-opacity=".75" transform="rotate(-40 {lx:.1f} {mt + ph + 14})">'
                       f'{cb.semaines[i]:%d/%m}</text>')
    out.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{mt + ph}" y2="{mt + ph}" stroke="currentColor" stroke-opacity=".4"/>')
    out.append("</svg>")
    leg = "".join(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px">'
                  f'<span style="width:12px;height:12px;border-radius:3px;background:{colors[z]}"></span>{e(z)} '
                  f'({sum(v)})</span>' for z, v in cb.series.items())
    leg += f'<span style="color:{theme.RED};font-weight:700">† décès</span>'
    return "".join(out) + f'<div style="font-size:12.5px;margin-top:6px">{leg}</div>'


# ---------------------------------------------------------------------------
# suivi des actions
# ---------------------------------------------------------------------------
@dataclass
class ActionSuivi:
    case: Case
    action: Action
    retard: Optional[int]       # jours de retard (None : pas d'échéance ou pas en retard)


def actions_ouvertes(cases: List[Case], ref: Optional[date] = None, toutes: bool = False) -> List[ActionSuivi]:
    ref = ref or date.today()
    out = []
    for c in cases:
        for a in c.actions:
            if not a.texte.strip() or (a.statut == "Fait" and not toutes):
                continue
            r = (ref - a.echeance).days if a.echeance and a.statut != "Fait" and a.echeance < ref else None
            out.append(ActionSuivi(c, a, r))
    return sorted(out, key=lambda x: (x.action.statut == "Fait", x.retard is None, -(x.retard or 0),
                                      PRIO.get(x.action.priorite, 3), x.action.echeance or date.max))


def bilan_actions(items: List[ActionSuivi]) -> Dict[str, int]:
    return {"ouvertes": sum(1 for x in items if x.action.statut != "Fait"),
            "retard": sum(1 for x in items if x.retard),
            "urgentes": sum(1 for x in items if x.action.priorite == "Urgent" and x.action.statut != "Fait"),
            "sans_responsable": sum(1 for x in items if not x.action.responsable.strip() and x.action.statut != "Fait"),
            "sans_echeance": sum(1 for x in items if not x.action.echeance and x.action.statut != "Fait")}


# ---------------------------------------------------------------------------
# points d'attention (texte du rapport)
# ---------------------------------------------------------------------------
def points_attention(ind: List[Indic], zones, alertes, actions: List[ActionSuivi]) -> List[str]:
    pts = []
    for i in ind:
        if i.statut == "alerte":
            pts.append(f"{i.nom} : {i.texte()} (cible {i.cible}).")
    c1 = [z.zs for z in zones if z.cat.get("num") == 1]
    if c1:
        pts.append("Transmission active (catégorie 1) : ZS " + ", ".join(c1) + ".")
    if alertes:
        pts.append(f"{len(alertes)} alerte(s) de nouveau foyer possible à investiguer.")
    r = sum(1 for a in actions if a.retard)
    if r:
        pts.append(f"{r} action(s) en retard sur les fiches de cas.")
    return pts or ["Aucun indicateur en alerte sur la période."]


# ---------------------------------------------------------------------------
# vues HTML (communes à la version web et à l'application de bureau)
# ---------------------------------------------------------------------------
STATUT_COULEUR = {"ok": theme.GREEN, "attention": theme.ORANGE, "alerte": theme.RED, "info": theme.BLUE}
STATUT_LIBELLE = {"ok": "atteint", "attention": "à surveiller", "alerte": "alerte", "info": "information"}

CSS = """
.rip-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap:10px; margin:6px 0 4px; }
.rip-k { border:1px solid rgba(127,127,127,.28); border-left:5px solid var(--c); border-radius:10px; padding:10px 12px; }
.rip-k .g { font-size:11px; text-transform:uppercase; letter-spacing:.04em; opacity:.65; }
.rip-k .n { font-weight:650; font-size:13.5px; margin:2px 0 6px; line-height:1.3; }
.rip-k .v { font-size:22px; font-weight:750; color:var(--c); }
.rip-k .s { font-size:12px; opacity:.75; margin-top:2px; }
.rip-k .s b { color:var(--c); }
.rip-k details { font-size:12px; margin-top:4px; } .rip-k summary { cursor:pointer; opacity:.8; }
.rip-pill { display:inline-block; padding:1px 8px; border-radius:20px; font-size:12px; font-weight:650;
  background: color-mix(in srgb, var(--c) 16%, transparent); color: var(--c); white-space:nowrap; }
"""


def html_indicateurs(ind: List[Indic]) -> str:
    e = html.escape
    out = [f"<style>{CSS}</style>"]
    groupe = None
    for i in ind:
        if i.groupe != groupe:
            if groupe is not None:
                out.append("</div>")
            groupe = i.groupe
            out.append(f'<h3 style="margin:14px 0 4px">{e(groupe)}</h3><div class="rip-grid">')
        c = STATUT_COULEUR[i.statut]
        info = []
        if i.cible:
            info.append(f"cible {e(i.cible)} · <b>{STATUT_LIBELLE[i.statut]}</b>")
        if i.inconnus:
            info.append(f"{i.inconnus} non renseigné(s)")
        det = ""
        if i.cas and i.statut != "ok":
            det = (f"<details><summary>{len(i.cas)} cas concerné(s)</summary>{e(', '.join(i.cas[:60]))}"
                   f"{' …' if len(i.cas) > 60 else ''}</details>")
        note = f'<div class="s">{e(i.note)}</div>' if i.note else ""
        out.append(f'<div class="rip-k" style="--c:{c}"><div class="n">{e(i.nom)}</div>'
                   f'<div class="v">{e(i.texte())}</div><div class="s">{" · ".join(info)}</div>{note}{det}</div>')
    if groupe is not None:
        out.append("</div>")
    return "".join(out)


def html_actions(items: List[ActionSuivi], lien=None) -> str:
    """Tableau des actions ; `lien(case)` renvoie l'adresse de la fiche (version web) ou None."""
    e = html.escape
    if not items:
        return '<p class="muted">Aucune action ouverte dans ce périmètre.</p>'
    pc = {"Urgent": theme.RED, "Important": theme.ORANGE, "Normal": theme.BLUE}
    rows = []
    for x in items:
        a, c = x.action, x.case
        nom = e(c.code_cas or c.titre_court())
        if lien:
            nom = f'<a href="{e(lien(c))}">{nom}</a>'
        ret = (f'<span class="rip-pill" style="--c:{theme.RED}">{x.retard} j de retard</span>' if x.retard else "")
        st = a.statut if a.statut != "Fait" else "Fait ✓"
        rows.append(f"<tr><td style='white-space:nowrap'>{nom}</td><td>{e(c.zs)}</td><td>{e(a.texte)}</td>"
                    f'<td><span class="rip-pill" style="--c:{pc.get(a.priorite, theme.GREY)}">{e(a.priorite)}</span></td>'
                    f"<td>{e(a.responsable) or '<span class=muted>à désigner</span>'}</td>"
                    f"<td>{a.echeance.strftime('%d/%m/%Y') if a.echeance else '<span class=muted>?</span>'}</td>"
                    f"<td style='white-space:nowrap'>{e(st)}</td><td>{ret}</td></tr>")
    return (f"<style>{CSS}</style><div style='overflow-x:auto'><table class='list'><tr><th>Cas</th><th>ZS</th>"
            "<th>Action</th><th>Priorité</th><th>Responsable</th><th>Échéance</th><th>Statut</th><th></th></tr>"
            + "".join(rows) + "</table></div>")


def page_bureau(titre: str, corps: str) -> str:
    """Page complète pour l'application de bureau (même contenu que la version web)."""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>
body {{ font-family:{theme.FONT_STACK}; color:#1B2430; background:#F3F5F8; margin:18px; font-size:14px; }}
h1 {{ font-size:20px; color:{theme.NAVY}; margin:0 0 4px; }} h2 {{ font-size:16px; color:{theme.NAVY}; }}
.card {{ background:#fff; border:1px solid #D3DAE3; border-radius:12px; padding:16px; margin-top:12px; }}
.muted, .hint {{ color:#5F6B7A; }} .hint {{ font-size:13px; }}
table.list {{ border-collapse:collapse; width:100%; font-size:13px; }}
table.list th {{ text-align:left; background:#F8FAFC; border-bottom:1px solid #D3DAE3; padding:6px 8px; }}
table.list td {{ border-bottom:1px solid #EEF1F5; padding:6px 8px; vertical-align:top; }}
</style></head><body><h1>{html.escape(titre)}</h1>{corps}</body></html>"""
