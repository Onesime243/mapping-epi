"""Construction du modèle de vue et rendu HTML (Jinja2) du mapping principal.

Toutes les visualisations sont des pages HTML de 1280×720 px CSS (16:9).
L'aperçu, le PDF, le PNG et le SVG partent du même HTML : ce que l'on voit
est exactement ce qui est exporté.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import theme
from core import rules
from core.models import Case, Event
from render.icons import icon_svg

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
APP_VERSION = "1.0"
PAGE_W, PAGE_H = 1280, 720

_env = Environment(loader=FileSystemLoader(str(ROOT / "render" / "templates")),
                   autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)


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
    theme: dict = field(default_factory=dict)


def build_mapping_view(case: Case) -> MappingView:
    w = rules.windows(case)
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
            phase=rules.event_phase(ev, w), uncertain=ev.date_incertaine or not ev.date_debut,
            reason=("Saisi" if ev.risque else "Suggéré") + f" — {why}", auto=not ev.risque,
            chips=event_chips(ev)))

    n = len(cards)
    per_row = n if n <= 12 else (n + 1) // 2
    rows = [cards[i:i + per_row] for i in range(0, n, per_row)] if n else [[]]

    bands: List[List[Band]] = []
    exp_lbl = f"Fenêtre d'exposition (J-{params['incubation_max']} → J-{params['incubation_min']})"
    con_lbl = "Période contagieuse"
    for row in rows:
        rb: List[Band] = []
        i = 0
        while i < len(row):
            ph = row[i].phase
            j = i
            while j + 1 < len(row) and row[j + 1].phase == ph:
                j += 1
            if ph:
                rb.append(Band(i + 1, j - i + 1, ph, exp_lbl if ph == "exposition" else con_lbl))
            i = j + 1
        bands.append(rb)

    identity = [
        {"k": "Sexe", "v": case.sexe if case.sexe != "Inconnu" else "?"},
        {"k": "Âge", "v": f"{case.age} {case.age_unite}" if case.age is not None else "?"},
        {"k": "AS", "v": case.aire_sante or "?"},
        {"k": "ZS", "v": case.zs or "?"},
        {"k": "Début symptômes (J0)", "v": fmt_date(case.debut_symptomes)},
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
        actions = [{"t": a.texte, "color": theme.ACTION_PRIORITY.get(a.priorite, theme.BLUE),
                    "done": a.statut == "Fait"} for a in case.actions]
    else:
        actions_auto = True
        actions = [{"t": s.texte, "color": theme.ACTION_PRIORITY.get(s.priorite, theme.BLUE), "done": False}
                   for s in rules.suggest_actions(case)[:7]]

    statut = {"Confirmé": "CONFIRMÉ", "Probable": "PROBABLE", "Suspect": "SUSPECT"}.get(case.statut, case.statut.upper())
    rang = f"DU {ordinal(case.rang)} CAS" if case.rang else "DU CAS"
    title = f"MAPPING COMPLET – PARCOURS ÉPIDÉMIOLOGIQUE {rang} {statut} {case.maladie.upper()} | ZS {(case.zs or '?').upper()}"
    score, _ = rules.completeness(case)
    meta = (f"Généré le {datetime.now():%d/%m/%Y à %H:%M} • Complétude de la fiche : {score} % • "
            f"Mapping Épi v{APP_VERSION}")
    return MappingView(
        title=title, subtitle="Lecture décisionnelle : chronologie • lieux • contacts • risque • PCI • laboratoire • actions",
        identity=identity, rows=rows, bands=bands, places=places, contacts=contacts, contact_phrase=cs.phrase,
        ipc=ipc, ipc_phrase=ipc_phrase, actions=actions, actions_auto=actions_auto, footer=case.note_pied,
        meta=meta)


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
