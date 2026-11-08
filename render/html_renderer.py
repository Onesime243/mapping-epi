"""Construction du modèle de vue et rendu HTML (Jinja2) du mapping principal.

Toutes les visualisations sont des pages HTML de 1280×720 px CSS (16:9).
L'aperçu, le PDF, le PNG et le SVG partent du même HTML : ce que l'on voit
est exactement ce qui est exporté.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import theme
from core import rules
from core.models import Case, Event
from render.icons import icon_svg

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
APP_VERSION = "1.1"
PAGE_W, PAGE_H = 1280, 720

_env = Environment(loader=FileSystemLoader(str(ROOT / "render" / "templates")),
                   autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)
_env.filters["soft"] = theme.soft
_env.filters["ink"] = theme.ink_on


def assets_uri() -> str:
    return ASSETS.resolve().as_uri() + "/"


# ---------------------------------------------------------------------------
# Libellés
# ---------------------------------------------------------------------------
def ordinal(n: Optional[int]) -> str:
    if not n:
        return ""
    return "1er" if n == 1 else f"{n}e"


def date_label(ev: Event) -> str:
    d1, d2 = ev.date_debut, ev.date_fin
    if not d1:
        txt = "?"
    elif d2 and d2 != d1:
        txt = f"{d1:%d}–{d2:%d/%m}" if (d1.month, d1.year) == (d2.month, d2.year) else f"{d1:%d/%m}–{d2:%d/%m}"
    else:
        txt = f"{d1:%d/%m}"
    if ev.heure.strip():
        txt += f" {'~' if ev.heure_approx else ''}{ev.heure.strip()}"
    return txt


def place_label(ev: Event) -> str:
    if ev.lieu and ev.lieu_arrivee:
        return f"{ev.lieu} → {ev.lieu_arrivee}"
    return ev.lieu or ev.lieu_arrivee or "?"


def fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "?"


def _dm(d) -> str:
    return d.strftime("%d/%m") if d else "?"


def build_phase_strip(case: Case, ph: "rules.Phases") -> List[dict]:
    """Les phases de la maladie, datées pour ce cas (bandeau sous « Chronologie du parcours »)."""
    P = theme.PHASES
    out: List[dict] = []

    def add(key, dates, detail):
        c = P[key]["color"]
        out.append({"key": key, "label": P[key]["label"], "contag": P[key]["contag"], "dates": dates,
                    "detail": detail, "color": c, "fill": theme.soft(c)})

    j0, inc = ph.j0, ph.incubation
    typ = f" (souvent {ph.incubation_typique[0]}–{ph.incubation_typique[1]} j)" if ph.incubation_typique else ""
    if ph.exposition:
        add("infection", f"{_dm(ph.exposition[0])} → {_dm(ph.exposition[1])} (estimé)",
            f"exposition à un malade ou un corps, J-{inc[1]} → J-{inc[0]}")
        add("incubation", f"jusqu'au {_dm(j0 - timedelta(days=1))}",
            f"{inc[0]}–{inc[1]} j{typ} • aucun symptôme, pas de transmission")
    else:
        add("infection", "? (début des symptômes manquant)", f"J-{inc[1]} → J-{inc[0]}")
        add("incubation", "?", f"{inc[0]}–{inc[1]} j{typ}")
    fin = ph.deces

    def signes(groupe: set, defaut: str) -> str:
        vus = [x for x in case.symptomes if x in groupe]
        if not vus:
            return f"signes habituels : {defaut}"
        return "signes rapportés : " + ", ".join(x[0].lower() + x[1:] if not x[:2].isupper() else x for x in vus)
    dry = signes(theme.SYMPTOMES_SECS, theme.SIGNES_SECS)
    wet = signes(theme.SYMPTOMES_HUMIDES, theme.SIGNES_HUMIDES)
    if ph.deux_phases:
        if j0:
            sec_end = (ph.humide - timedelta(days=1)) if ph.humide and ph.humide > j0 else None
            add("seche", f"J0 {_dm(j0)} (rapporté)" + (f" → {_dm(sec_end)}" if sec_end else ""), dry)
            rel = rules.relative_day(ph.humide, j0)
            add("humide", f"dès le {_dm(ph.humide)} ({rel}, {ph.humide_source})" if ph.humide else "?", wet)
        else:
            add("seche", "J0 ?", dry)
            add("humide", "?", wet)
    else:
        add("symptomes", f"J0 {_dm(j0)} (rapporté)" if j0 else "J0 ?", "période contagieuse")
    if fin:
        add("deces", f"{_dm(fin)}" + (f" ({rules.relative_day(fin, j0)})" if j0 else ""),
            "charge virale maximale : corps très contagieux")
    return out


def event_chips(ev: Event) -> list:
    out = []
    if ev.transport and ev.transport.lower() not in ev.description.lower():
        icon = "moto" if ev.transport.lower() == "moto" else "arrow"
        out.append({"t": ev.transport, "icon": icon_svg(icon, 10, theme.NAVY, 2.2), "warn": False})
    if ev.contact_corps:
        out.append({"t": "Contact corps", "icon": icon_svg("cross", 10, theme.RED, 2.2), "warn": True})
    if ev.liquides and not any(k in ev.description.lower() for k in ("méléna", "hématémèse", "saign", "vomi")):
        out.append({"t": "Liquides biol.", "icon": icon_svg("alert", 10, theme.RED, 2.2), "warn": True})
    if ev.sans_pci:
        out.append({"t": "Sans PCI", "icon": icon_svg("alert", 10, theme.RED, 2.2), "warn": True})
    if ev.personnes:
        out.append({"t": ev.personnes, "icon": icon_svg("people", 10, theme.NAVY, 2.2), "warn": False})
    return out[:3]


# ---------------------------------------------------------------------------
# Modèle de vue
# ---------------------------------------------------------------------------
@dataclass
class Card:
    date: str
    place: str
    title: str
    desc: str
    risk: str
    risk_color: str
    type_color: str
    icon: str
    rel: str
    phase: str
    uncertain: bool
    reason: str
    auto: bool
    chips: list = field(default_factory=list)


@dataclass
class Band:
    col: int
    span: int
    phase: str
    label: str


@dataclass
class MappingView:
    title: str
    subtitle: str
    identity: List[dict]
    rows: List[List[Card]]
    bands: List[List[Band]]
    places: List[dict]
    contacts: List[dict]
    contact_phrase: str
    ipc: List[dict]
    ipc_phrase: str
    actions: List[dict]
    actions_auto: bool
    footer: str
    meta: str
    phase_strip: List[dict] = field(default_factory=list)
    contact: Optional[dict] = None
    theme: dict = field(default_factory=dict)


def build_mapping_view(case: Case) -> MappingView:
    w = rules.windows(case)
    ph = rules.phases(case)
    params = rules.disease_params(case.maladie)
    grisk, grisk_why = rules.global_risk(case)

    cards: List[Card] = []
    for ev in case.events:
        sug, why = rules.suggest_event_risk(ev, case, w)
        risk = ev.risque or sug
        et = theme.EVENT_TYPES.get(ev.type, theme.EVENT_TYPES["Autre"])
        cards.append(Card(
            date=date_label(ev), place=place_label(ev), title=ev.titre or ev.type,
            desc=ev.description, risk=risk, risk_color=theme.risk_color(risk), type_color=et["color"],
            icon=icon_svg(et["icon"], 13, "#fff", 2.2), rel=rules.relative_day(ev.date_debut, w.j0),
            phase=rules.event_stage(ev, ph), uncertain=ev.date_incertaine or not ev.date_debut,
            reason=("Saisi" if ev.risque else "Suggéré") + f" : {why}", auto=not ev.risque,
            chips=event_chips(ev)))

    n = len(cards)
    per_row = n if n <= 12 else (n + 1) // 2
    rows = [cards[i:i + per_row] for i in range(0, n, per_row)] if n else [[]]

    bands: List[List[Band]] = []

    def band_label(stage: str, span: int) -> str:
        d = theme.PHASES[stage]
        if span == 1 and len(rows[0]) > 5:
            return d["label"]
        if stage == "infection":
            return f"{d['label']} · exposition J-{params['incubation_max']} → J-{params['incubation_min']}"
        return f"{d['label']} · {d['contag']}"
    for row in rows:
        rb: List[Band] = []
        i = 0
        while i < len(row):
            st = row[i].phase
            j = i
            while j + 1 < len(row) and row[j + 1].phase == st:
                j += 1
            if st:
                rb.append(Band(i + 1, j - i + 1, st, band_label(st, j - i + 1)))
            i = j + 1
        bands.append(rb)

    identity = [
        {"k": "Sexe", "v": case.sexe if case.sexe != "Inconnu" else "?"},
        {"k": "Âge", "v": f"{case.age} {case.age_unite}" if case.age is not None else "?"},
        {"k": "AS", "v": case.aire_sante or "?"},
        {"k": "ZS", "v": case.zs or "?"},
        {"k": "Exposition estimée", "v": f"{_dm(ph.exposition[0])} → {_dm(ph.exposition[1])}" if ph.exposition else "?",
         "tip": "Calculée depuis le début des symptômes rapporté (J-21 → J-2 pour la MVE)"},
        {"k": "Début symptômes (J0)", "v": fmt_date(case.debut_symptomes), "tip": "Date rapportée par l'équipe d'investigation"},
        {"k": case.statut if case.statut != "Confirmé" else "Confirmation", "v": fmt_date(case.date_confirmation)},
        {"k": "Issue", "v": case.issue, "color": theme.ISSUE_COLORS.get(case.issue)},
        {"k": "Risque", "v": grisk.upper(), "color": theme.risk_color(grisk), "tip": grisk_why},
    ]

    places = []
    for i, p in enumerate(case.places, 1):
        r = rules.suggest_place_risk(p, case)
        places.append({"n": i, "name": p.nom, "popu": p.population or "?", "risk": r.upper(),
                       "color": theme.risk_color(r), "count": p.nombre})

    contacts = [{"name": g.categorie, "n": "?" if g.nombre is None else str(g.nombre),
                 "suffix": g.libelle_nombre, "risk": g.risque,
                 "color": theme.CONTACT_RISKS.get(g.risque, theme.BLUE), "unknown": g.nombre is None}
                for g in case.contacts]
    cs = rules.contact_summary(case)

    ipc = [{"site": x.site, "status": "DÉCONTAMINÉ" if x.statut == "Décontaminé" else x.statut.upper(),
            "color": theme.IPC_STATUS.get(x.statut, theme.BLUE)} for x in case.ipc]
    if any(x.statut != "Décontaminé" for x in case.ipc):
        ipc_phrase = "Priorité : fermer les sites non décontaminés et documenter la date / équipe / produit."
    elif case.ipc:
        ipc_phrase = "Tous les sites sont décontaminés : vérifier la traçabilité (date / équipe / produit)."
    else:
        ipc_phrase = "Aucun site renseigné."

    actions_auto = False
    if case.actions:
        prio = {k: i for i, k in enumerate(theme.ACTION_PRIORITY_CHOICES)}
        actions = [{"t": a.texte + (" (en cours)" if a.statut == "En cours" else ""),
                    "color": theme.ACTION_PRIORITY.get(a.priorite, theme.BLUE), "done": a.statut == "Fait",
                    "k": (a.statut == "Fait", prio.get(a.priorite, 9), i)}
                   for i, a in enumerate(case.actions) if a.texte.strip()]
        actions.sort(key=lambda d: d["k"])
    else:
        actions_auto = True
        actions = [{"t": s.texte, "color": theme.ACTION_PRIORITY.get(s.priorite, theme.BLUE), "done": False}
                   for s in rules.suggest_actions(case)[:7]]

    statut = {"Confirmé": "CONFIRMÉ", "Probable": "PROBABLE", "Suspect": "SUSPECT"}.get(case.statut, case.statut.upper())
    rang = f"DU {ordinal(case.rang)} CAS" if case.rang else "DU CAS"
    title = f"MAPPING COMPLET – PARCOURS ÉPIDÉMIOLOGIQUE {rang} {statut} {case.maladie.upper()} | ZS {(case.zs or '?').upper()}"
    contact = None
    if case.contact_connu and case.contact_connu != "Inconnu":
        cc = theme.soft(theme.CONTACT_STATUS_COLORS.get(case.contact_connu, theme.RED))
        contact = {"t": case.contact_connu.replace(" suivi", " · suivi").upper(), "fill": cc, "ink": theme.ink_on(cc)}
    score, _ = rules.completeness(case)
    meta = (f"Généré le {datetime.now():%d/%m/%Y à %H:%M} • Complétude de la fiche : {score} % • "
            f"Mapping Épi v{APP_VERSION}")
    return MappingView(
        title=title, subtitle=(f"ID {case.code_cas.strip()} • " if case.code_cas.strip() else "")
        + "Lecture décisionnelle : chronologie • lieux • contacts • risque • PCI • laboratoire • actions",
        identity=identity, rows=rows, bands=bands, places=places, contacts=contacts, contact_phrase=cs.phrase,
        ipc=ipc, ipc_phrase=ipc_phrase, actions=actions, actions_auto=actions_auto, footer=case.note_pied,
        meta=meta, phase_strip=build_phase_strip(case, ph), contact=contact)


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------
def theme_ctx() -> dict:
    return {k: getattr(theme, k) for k in dir(theme) if k.isupper()}


def page(body: str, title: str = "Mapping", extra_css: str = "", assets: Optional[str] = None) -> str:
    """assets : adresse du dossier assets/ (fichier local par défaut, « /assets/ » pour la version web)."""
    tpl = _env.get_template("base.html.j2")
    return tpl.render(body=body, title=title, extra_css=extra_css, assets=assets or assets_uri(), t=theme_ctx(),
                      W=PAGE_W, H=PAGE_H)


def render_mapping_body(case: Case) -> str:
    view = build_mapping_view(case)
    return _env.get_template("mapping.html.j2").render(v=view, t=theme_ctx())


def render_mapping_html(case: Case, assets: Optional[str] = None) -> str:
    return page(render_mapping_body(case), title=build_mapping_view(case).title, assets=assets)


def render_report_html(case: Case, svgs: List[str]) -> str:
    """Rapport multi-pages : mapping + visuels complémentaires (une page 16:9 chacun)."""
    body = render_mapping_body(case) + "".join(f'<div class="page"><div class="svgpage">{s}</div></div>' for s in svgs)
    return page(body, title="Rapport complet").replace(
        "html, body { width: 1280px; height: 720px; overflow: hidden; }", "html, body { width: 1280px; }")


A4_CSS = ("@page { size: 297mm 210mm; margin: 0; } "
          "html, body { height: auto !important; overflow: visible !important; } "
          "body { zoom: 0.8766; } .page { margin-top: 92px; margin-bottom: 92px; }")


def with_css(html: str, css: str) -> str:
    return html.replace("</style>", css + "\n</style>", 1)


def render_svg_page(svg: str, title: str, assets: Optional[str] = None) -> str:
    return page(f'<div class="svgpage">{svg}</div>', title=title, assets=assets)


def html_to_svg_wrapper(html: str) -> str:
    """SVG autonome embarquant la page HTML (foreignObject) : vectoriel, lisible dans les navigateurs."""
    import re
    head_css = "\n".join(re.findall(r"<style>(.*?)</style>", html, flags=re.S))
    body = re.search(r"<body[^>]*>(.*)</body>", html, flags=re.S).group(1)
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" '
            f'viewBox="0 0 {PAGE_W} {PAGE_H}"><foreignObject x="0" y="0" width="{PAGE_W}" height="{PAGE_H}">'
            f'<div xmlns="http://www.w3.org/1999/xhtml"><style>{head_css}</style>{_xhtml(body)}</div>'
            f'</foreignObject></svg>')


def _xhtml(s: str) -> str:
    import re
    s = re.sub(r"<(br|hr|img|meta|link|input)([^>]*?)(?<!/)>", r"<\1\2/>", s)
    return s.replace("&nbsp;", "&#160;")
