"""Visuels en anglais (langue de l'utilisateur) et mise en page des chaînes de transmission sans chevauchement."""
import html
import random
import re
from datetime import date, timedelta

import pytest

from core.langue import utiliser
from core.models import Case, Event
from render import chains, common_places, dashboard, gantt, html_renderer as H, map_view, network
from render import svgkit as K


def _big(n=149, seed=7):
    """~150 cas sur 5 zones, avec liens (chaînes profondes), sources hors périmètre et un ID en double."""
    rnd = random.Random(seed)
    zones = [("Ituri", "Bunia", "Lembabo"), ("Ituri", "Mambasa", "Bandiboli"), ("Nord-Kivu", "Beni", "Ngadi"),
             ("Nord-Kivu", "Butembo", "Vulamba"), ("Tshopo", "Makiso-Kisangani", "Plateau Boyoma")]
    lieux = ["HGR Bunia", "CS Lembabo", "Église CEPAC Mambasa", "Marché central de Beni", "CS Ngadi"]
    cases = []
    for i in range(n):
        prov, zs, aire = rnd.choice(zones)
        code = f"RDC-{zs[:3].upper()}-{i + 1:03d}"
        j0 = date(2026, 8, 1) + timedelta(days=rnd.randint(0, 60))
        src = ""
        if i > 3 and rnd.random() < 0.6:
            src = rnd.choice(cases).code_cas
        elif rnd.random() < 0.08:
            src = f"RDC-ITU-HORS-PERIMETRE-{rnd.randint(100, 999)}"
        if i in (20, 21, 22):
            code = "RDC-ITU-DOUBLON-0001-VERY-LONG"
        cases.append(Case(code_cas=code, province=prov, zs=zs, aire_sante=aire, debut_symptomes=j0,
                          events=[Event(type="Hospitalisation", date_debut=j0 + timedelta(days=2), lieu=rnd.choice(lieux))],
                          id_cas_source=src, contact_connu=rnd.choice(["Contact connu suivi", "Contact connu", "Inconnu"])
                          if src else "Non contact", sexe=rnd.choice(["M", "F"]), age=rnd.randint(1, 80),
                          issue=rnd.choice(["Décès", "En traitement", "Guéri"]), date_confirmation=j0 + timedelta(days=3)))
    for k in (30, 31, 32):
        cases[k].id_cas_source = "RDC-ITU-DOUBLON-0001-VERY-LONG"
    return cases


def _all(demo, big):
    return {"mapping": H.render_mapping_html(demo), "network": network.render_svg(demo), "route": map_view.render_svg(demo),
            "gantt": gantt.render_svg(demo), "dashboard": dashboard.render_svg([demo] + big[:8], demo.zs),
            "chains": chains.render_svg(big, None, "Ituri"), "common": common_places.render_svg(big[:40], None, "Ituri")}


def _visible(markup: str) -> str:
    markup = re.sub(r"<(style|script)\b.*?</\1>", " ", markup, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", markup))


EN_ATTENDU = {
    "mapping": ["Care pathway · 3rd confirmed EVD case · HZ Tumba", "Pathway chronology", "Contacts to identify / follow up",
                "IPC / decontamination", "To do immediately", "Reported D0", "Estimated exposure", "NOT VACCINATED",
                "Dry phase", "Wet phase", "highly contagious", "contagious from fever onset", "Point of infection",
                "to be counted", "Signs → confirmation", "11 days", "Record completeness", "Mapping Épi v" + H.APP_VERSION,
                "D±n: days since the retained D0"],
    "network": ["TRANSMISSION AND CONTACT NETWORK", "SUMMARY", "Contacts listed", "LEGEND", "Unknown number"],
    "route": ["PATHWAY MAP", "PATHWAY STEPS", "Movement of the case", "Colour = risk level"],
    "gantt": ["TIMELINE", "Retained D0", "POINT OF INFECTION (ESTIMATED EXPOSURE)", "End of follow-up", "D+"],
    "dashboard": ["MULTI-CASE DASHBOARD", "MOST VISITED PLACES", "contacts counted"],
    "chains": ["TRANSMISSION CHAINS", "SUMMARY", "CASES WITHOUT AN ENTERED LINK", "LEADS: SHARED PLACES",
               "Known contact under follow-up", "Known contact (not followed up)", "Contact status not specified",
               "Source outside scope", "cases in scope", "GENERATION 2"],
    "common": ["SHARED PLACES VISITED BY THE CASES", "PLACE", "READING", "Case contagious during the visit"],
}
FR_INTERDIT = ["Parcours thérapeutique", "Chronologie du parcours", "Contacts à identifier", "PCI / décontamination",
               "À réaliser immédiatement", "Déjà réalisées", "J0 rapporté", "J0 retenu", "Généré le", "Complétude de la fiche",
               "NON VACCINÉ", "Phase sèche", "Phase humide", "très contagieux", "Point d'infection", "à dénombrer",
               "RÉSEAU DE TRANSMISSION", "Synthèse", "SYNTHÈSE", "Contacts listés", "CARTE DU PARCOURS", "Étapes du parcours",
               "FRISE TEMPORELLE", "TABLEAU DE BORD", "CHAÎNES DE TRANSMISSION", "Cas sans lien saisi", "Pistes : lieux communs",
               "Statut de contact non précisé", "Source hors périmètre", "Aucune piste", "LIEUX COMMUNS", "Génération",
               "GÉNÉRATION", "Lieu commun à vérifier", "personnes présentes", "suggérées, à valider"]


def test_visuals_in_english(demo):
    with utiliser("en"):
        outs = _all(demo, _big())
    for key, markup in outs.items():
        txt = _visible(markup)
        for s in EN_ATTENDU[key]:
            assert s in txt, (key, s)
        for s in FR_INTERDIT:
            assert s not in txt, (key, s)
        assert "—" not in txt, key
        assert not re.search(r"\bJ[+\-−]?\d", txt), (key, re.findall(r".{20}\bJ[+\-−]?\d.{10}", txt)[:3])


def test_visuals_unchanged_in_french(demo):
    with utiliser("fr"):
        outs = _all(demo, _big())
    txt = {k: _visible(v) for k, v in outs.items()}
    for s in ["Parcours thérapeutique · 3e cas confirmé MVE · ZS Tumba", "Chronologie du parcours", "Contacts à identifier / suivre",
              "PCI / décontamination", "J0 rapporté", "NON VACCINÉ", "Généré le", "Mapping Épi v" + H.APP_VERSION]:
        assert s in txt["mapping"], s
    assert "RÉSEAU DE TRANSMISSION ET DE CONTACTS" in txt["network"] and "CARTE DU PARCOURS" in txt["route"]
    assert "FRISE TEMPORELLE" in txt["gantt"] and "TABLEAU DE BORD MULTI-CAS" in txt["dashboard"]
    assert "CHAÎNES DE TRANSMISSION" in txt["chains"] and "Statut de contact non précisé" in txt["chains"]
    assert "LIEUX COMMUNS FRÉQUENTÉS PAR LES CAS" in txt["common"]
    for t in txt.values():
        assert "Care pathway" not in t and "TRANSMISSION CHAINS" not in t and "—" not in t


def test_entered_values_are_not_translated(demo):
    with utiliser("en"):
        out = _visible(H.render_mapping_html(demo))
    for s in ("Marché de Nzala", "HGR Tumba", "FICTIF-TUM-26-003", "Famille & voisins", "Reconstituer source d’exposition"):
        assert s in out, s


# ---------------------------------------------------------------------------
# Chaînes : légende et panneau sans chevauchement
# ---------------------------------------------------------------------------
_TEXT = re.compile(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*?font-size="([\d.]+)"(?:[^>]*?font-weight="(\d+)")?[^>]*>(.*?)</text>', re.S)


def _texts(fragment):
    return [(float(x), float(y), float(s), int(w or 400), html.unescape(re.sub(r"<[^>]+>", "", t)))
            for x, y, s, w, t in _TEXT.findall(fragment)]


def _group(svg, cls):
    m = re.search(rf'<g class="{cls}">(.*?)</g>(?!</g>)', svg, flags=re.S)
    assert m, cls
    return m.group(1)


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_chains_legend_does_not_overlap(lang):
    with utiliser(lang):
        svg = chains.render_svg(_big(), None, "RDC")
    leg = _texts(_group(svg, "legende"))
    assert len(leg) == 5
    x0, _y0, aw, ah = chains.AREA
    by_line = {}
    for x, y, s, w, t in leg:
        by_line.setdefault(y, []).append((x, x + K.text_width(t, s, w)))
    for spans in by_line.values():
        spans.sort()
        assert spans[-1][1] <= x0 + aw - 8                     # dans le cadre
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            assert a1 + 20 < b0                                 # place pour le symbole suivant
    ys = sorted(by_line)
    assert all(b - a >= 14 for a, b in zip(ys, ys[1:]))
    # la note « + n autre(s) chaîne(s) » est dans le panneau de synthèse, plus sur la légende
    assert not any("chaîne" in t or "chain" in t for *_x, t in leg)
    note = "autre(s) chaîne(s) non affichée(s)" if lang == "fr" else "other chain(s) not shown"
    assert note in _visible(_group(svg, "panneau"))


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_chains_panel_lines_never_overlap(lang):
    with utiliser(lang):
        svg = chains.render_svg(_big(), None, "RDC")
    panel = _group(svg, "panneau")
    lines = [t for t in _texts(panel) if t[0] == chains.PANEL_X + 16]
    assert len(lines) > 10
    ys = [y for _x, y, *_r in lines]
    assert ys == sorted(ys)
    for (x, y, s, w, t), (_x2, y2, s2, *_r) in zip(lines, lines[1:]):
        assert y2 - y >= s2 * 1.1, (t, y, y2)                    # deux lignes jamais l'une sur l'autre
    for x, y, s, w, t in lines:
        assert y <= chains.PANEL_YMAX
        assert K.text_width(t, s, w) <= chains.PANEL_TW + 1, t     # coupé ou abrégé dans la largeur du panneau
    texte = _visible(panel)
    vide = "Aucune piste non reliée détectée." if lang == "fr" else "No unlinked lead detected."
    assert vide in texte and "RDC-ITU-DOUBLON-0001-VERY-LONG" in texte    # message des liens écartés, sous la ligne


def test_chains_source_outside_scope_shows_id():
    a = Case(code_cas="BU-001", zs="Bunia", aire_sante="Lembabo", debut_symptomes=date(2026, 8, 2),
             id_cas_source="NK-BEN-099-EXTERNE")
    b = Case(code_cas="BU-002", zs="Bunia", aire_sante="Lembabo", debut_symptomes=date(2026, 8, 12),
             id_cas_source="BU-001", contact_connu="Contact connu suivi")
    for lang, head in (("fr", "Source hors périmètre"), ("en", "Source outside scope")):
        with utiliser(lang):
            svg = chains.render_svg([a, b])
        texts = [t for *_r, t in _texts(svg)]
        assert head in texts and "NK-BEN-099-EXTERNE" in texts          # l'ID sur sa propre ligne, entier
        assert ("Generation 2".upper() if lang == "en" else "GÉNÉRATION 2") in texts
