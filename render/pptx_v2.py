"""Export PowerPoint NATIF du mapping repensé (v1.8) : mêmes zones que render/templates/mapping.html.j2.

Tout est en formes PowerPoint modifiables (aucune image) : en-tête à trois chiffres, ligne des dates, frise à
l'échelle du temps, cartes des étapes, blocs Contacts / PCI / Actions, pied de page. Géométrie en pixels CSS
de la page 1280 × 720 (1 px = 0,75 pt).
"""
from __future__ import annotations

from typing import Optional

from pptx import Presentation
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from core.models import Case
from render.html_renderer import MappingView, build_mapping_view
from render.pptx_exporter import Slide, fit_pt

NAVY, FOND, PAPIER, BORD = "#12213B", "#FFFFFF", "#FFFFFF", "#B8C0CC"
ENCRE, GRIS, BLEU, ORANGE_T = "#000000", "#000000", "#3E6FA8", "#8A4B00"
W, H = 1280, 720


def _pt(px: float) -> float:
    return round(px * 0.75, 2)


def add_mapping_slide_v2(prs: Presentation, case: Case, view: Optional[MappingView] = None) -> None:
    v = view or build_mapping_view(case)
    x = v.v2
    S = Slide(prs.slides.add_slide(prs.slide_layouts[6]))
    S.rect(0, 0, W, H, FOND, name="Fond")

    # -- en-tête -----------------------------------------------------------------------------------------------
    S.rect(0, 0, W, 70, NAVY, name="En-tête")
    hero_w, gap = 168, 8
    hx = W - 22 - 3 * hero_w - 2 * gap
    tw = hx - 22 - 16
    S.text(22, 10, tw, 30, [x["titre"]], size=fit_pt([(x["titre"], 1)], tw, 30, _pt(20), 9), color="#F7F5F0",
           bold=True, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, name="Titre")
    S.text(22, 42, tw, 18, [x["sous"]], size=fit_pt([(x["sous"], 1)], tw, 18, _pt(11.5), 6), color="#C9D3E2",
           align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, name="Sous-titre")
    for i, k in enumerate(x["hero"]):
        bx = hx + i * (hero_w + gap)
        S.rect(bx, 9, hero_w, 52, k["bg"], radius=9, name=f"Chiffre {k['k']}")
        S.text(bx + 10, 12, hero_w - 20, 12, [k["k"].upper()], size=6.4, color=k["fg"], bold=True, align=PP_ALIGN.LEFT)
        S.text(bx + 10, 23, hero_w - 20, 22, [k["v"]], size=fit_pt([(k["v"], 1)], hero_w - 20, 22, _pt(19), 8),
               color=k["fg"], bold=True, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
        S.text(bx + 10, 45, hero_w - 20, 13, [k["s"]], size=6.6, color=k["fg"], align=PP_ALIGN.LEFT)
    for i, c in enumerate(("#1D5FAF", "#C8202A", "#F2B705")):
        S.rect(i * W / 3, 70, W / 3 + 1, 4, c, name="Bande tricolore")

    # -- ligne des dates et de ce qui manque ---------------------------------------------------------------------
    S.rect(0, 74, W, 28, PAPIER, name="Dates")
    S.line(0, 102, W, 102, BORD, 0.75)
    manque = ("? " + " · ".join(x["manque"])) if x["manque"] else ""
    mw = min(520, 24 + len(manque) * 5.3) if manque else 0
    runs = []
    for d in x["dates"]:
        runs += [(d["k"] + " ", {"color": GRIS}), (d["v"], {"bold": True, "color": ENCRE}),
                 ((" " + d["x"]) if d.get("x") else "", {"color": GRIS}), ("    ", {})]
    S.text(22, 76, W - 44 - mw - 10, 24, [runs], size=7.9, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, name="Dates clés")
    if manque:
        sh = S.rect(W - 22 - mw, 79, mw, 18, "#FFF1DC", "#F0C78A", radius=9, name="À compléter")
        S.text(0, 0, 0, 0, [manque], size=fit_pt([(manque, 1)], mw - 12, 16, 7.9, 5.5), color=ORANGE_T, bold=True,
               anchor=MSO_ANCHOR.MIDDLE, shape=sh)

    # -- frise à l'échelle du temps -------------------------------------------------------------------------------
    sh = S.rect(22, 106, 232, 17, "#1F3A5F", radius=4, name="Étiquette chronologie")
    S.text(0, 0, 0, 0, ["CHRONOLOGIE À L’ÉCHELLE DU TEMPS"], size=7.1, color="#FFFFFF", bold=True, anchor=MSO_ANCHOR.MIDDLE,
           shape=sh)
    if x["frise"] and x["frise"]["adapte"]:
        S.text(262, 106, 500, 17, ["les jours où plusieurs étapes se suivent sont agrandis"], size=6.6, color="#000000",
               align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
    fx, fw, ft = 26, W - 52, 126
    f = x["frise"]
    if f:
        X = lambda pct: fx + fw * pct / 100.0                                                    # noqa: E731
        for b in f["bandes"]:
            bw = max(4, fw * b["w"] / 100.0 - 2)
            sh = S.rect(X(b["l"]), ft + 4, bw, 20, b["bg"], radius=4, name="Phase")
            S.text(0, 0, 0, 0, [b["t"]], size=fit_pt([(b["t"], 1)], bw - 8, 18, 7.1, 5), color=b["fg"], bold=True,
                   align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        if f["trou"]:
            t = f["trou"]
            gw = max(30, fw * t["w"] / 100.0 - 2)
            sh = S.rect(X(t["l"]), ft + 28, gw, 14, "#FFF6E8", "#C76A00", radius=4, line_w=1.0, name="Trou de chronologie")
            sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            S.text(0, 0, 0, 0, [t["t"]], size=fit_pt([(t["t"], 1)], gw - 6, 13, 6.4, 4.5), color=ORANGE_T, bold=True,
                   anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        S.rect(fx, ft + 49, fw, 2, "#C9C2B3", name="Axe du temps")
        for r in f["reperes"]:
            S.line(X(r["x"]), ft, X(r["x"]), ft + 52, NAVY, 1.1)
            S.text(X(r["x"]) + 2, ft - 2, 80, 11, [r["t"]], size=6, color=NAVY, bold=True, align=PP_ALIGN.LEFT)
        for p in f["points"]:
            S.oval(X(p["x"]), ft + 50, 5.5, p["c"], FOND, 1.5)
        for t in f["ticks"]:
            S.text(X(t["x"]) - 24, ft + 55, 48, 11, [t["t"]], size=6.4, color="#000000")
    else:
        S.text(22, ft + 8, 700, 18, ["Aucune date dans la chronologie : renseigner les dates des étapes pour afficher la frise."],
               size=8.2, color=GRIS, align=PP_ALIGN.LEFT)

    # -- zones du bas : calculées depuis le pied de page -------------------------------------------------------------
    two = len(v.rows) > 1
    foot_y = H - 6 - 16
    bas_h = 168 if two else 214
    bas_y = foot_y - 7 - bas_h
    cy0, cy1 = ft + 66 + 7, bas_y - 7

    # -- cartes des étapes -------------------------------------------------------------------------------------------
    cartes = x["cartes"]
    per = len(v.rows[0]) if v.rows and v.rows[0] else 1
    nrows = max(1, len(v.rows))
    cw = (W - 44 - (per - 1) * 6) / per
    ch = (cy1 - cy0 - (nrows - 1) * 6) / nrows
    pill_h = 16 if two else 18

    def lignes(c):
        out = [(c["date"] + (f"  {c['rel']}" if c["rel"] else ""), 0.92), (c["lieu"], 1.0), (c["titre"], 1.05)]
        if c["desc"] and not two:
            out.append((c["desc"], 0.82))
        out += [(("⚠ " if ch_.get("warn") else "") + ch_["t"], 0.78) for ch_ in c["chips"]]
        if c["personnes"]:
            out.append(("? personnes présentes", 0.8))
        return out
    taille = min([fit_pt(lignes(c), cw - 14, ch - pill_h - 16, _pt(10 if two else 11.5), 4.5) for c in cartes] or [8])
    for i, c in enumerate(cartes):
        r_, col = divmod(i, per)
        bx, by = 22 + col * (cw + 6), cy0 + r_ * (ch + 6)
        card = S.rect(bx, by, cw, ch, PAPIER, BORD, radius=8, name=f"Étape {i + 1}")
        if c["incertain"]:
            card.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        pars = [[(c["date"], {"bold": True, "color": BLEU, "size": taille * 0.92}),
                 (("  " + c["rel"]) if c["rel"] else "", {"bold": True, "color": "#000000", "size": taille * 0.75})],
                [(c["lieu"], {"bold": True, "color": ENCRE})],
                [(c["titre"], {"color": ENCRE, "bold": True, "size": taille * 1.02})]]
        if c["desc"] and not two:
            pars.append([(c["desc"], {"color": "#000000", "size": taille * 0.82})])
        for ch_ in c["chips"]:
            pars.append([(("⚠ " if ch_.get("warn") else "") + ch_["t"],
                          {"color": "#8E1F24" if ch_.get("warn") else GRIS, "bold": bool(ch_.get("warn")), "size": taille * 0.78})])
        if c["personnes"]:
            pars.append([("? personnes présentes", {"color": ORANGE_T, "bold": True, "size": taille * 0.8})])
        S.text(bx + 6, by + 5, cw - 12, ch - pill_h - 12, pars, size=taille, color=ENCRE, align=PP_ALIGN.LEFT)
        S.oval(bx + cw - 13, by + 13, 7, c["tc"], "#FFFFFF", 1.0)          # couleur du type d'étape
        sh = S.rect(bx + 6, by + ch - pill_h - 6, cw - 12, pill_h, c["r"]["c"], radius=5, name="Risque")
        S.text(0, 0, 0, 0, [f"{c['r']['s']} {c['r']['t']}"], size=_pt(8.5 if two else 9.5), color="#FFFFFF", bold=True,
               anchor=MSO_ANCHOR.MIDDLE, shape=sh)
    if not cartes:
        S.text(22, cy0, 600, 20, ["Aucune étape dans la chronologie."], size=8.2, color=GRIS, align=PP_ALIGN.LEFT)

    # -- blocs Contacts / PCI / Actions ------------------------------------------------------------------------------
    tot = W - 44 - 18
    largeurs = [tot * 1.25 / 3.5, tot * 1.0 / 3.5, tot * 1.25 / 3.5]
    xs = [22, 22 + largeurs[0] + 9, 22 + largeurs[0] + largeurs[1] + 18]

    def boite(i, titre, resume):
        bx, bw = xs[i], largeurs[i]
        S.rect(bx, bas_y, bw, bas_h, PAPIER, BORD, radius=9, name=titre)
        lw = 22 + len(titre) * 6.4
        sh = S.rect(bx + 10, bas_y + 7, lw, 17, "#1F3A5F", radius=4, name="Étiquette " + titre)
        S.text(0, 0, 0, 0, [titre.upper()], size=7.1, color="#FFFFFF", bold=True, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        S.text(bx + bw * 0.4, bas_y + 7, bw * 0.6 - 12, 14, [resume], size=6.6, color="#000000", align=PP_ALIGN.RIGHT)
        return bx + 12, bas_y + 30, bw - 24, bas_h - 38

    # Contacts
    cx, cyb, cwb, chb = boite(0, "Contacts à identifier / suivre", x["contacts"]["resume"])
    lig = x["contacts"]["lignes"]
    if lig:
        rh = min(18, chb / max(1, len(lig)))
        fs = min(_pt(11.5), rh * 0.62)
        for j, g in enumerate(lig):
            yy = cyb + j * rh
            S.text(cx, yy, cwb * 0.4, rh, [g["t"]], size=fs, color=ENCRE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
            bx2, bw2 = cx + cwb * 0.42, cwb * 0.33
            S.rect(bx2, yy + rh * 0.3, bw2, rh * 0.4, "#EEE9DE", radius=4, name="Barre")
            if g["w"]:
                S.rect(bx2, yy + rh * 0.3, max(3, bw2 * g["w"] / 100.0), rh * 0.4, g["c"], radius=4, name="Barre remplie")
            if g["n"] is None:
                S.text(cx + cwb * 0.76, yy, cwb * 0.24, rh, ["? à dénombrer"], size=fs, color=ORANGE_T, bold=True,
                       align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
            else:
                val = str(g["n"]) + (f" · {g['s']} suivis" if g["s"] is not None else "")
                S.text(cx + cwb * 0.76, yy, cwb * 0.24, rh, [val], size=fs, color=ENCRE, bold=True,
                       align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    else:
        S.text(cx, cyb, cwb, 16, ["Aucun groupe de contacts renseigné."], size=8, color=GRIS, align=PP_ALIGN.LEFT)

    # PCI
    px_, pyb, pwb, phb = boite(1, "PCI / décontamination", x["pci"]["resume"])
    sites = x["pci"]["sites"]
    extra = (2 if x["pci"]["sans"] else 0) + (1 if any(s["st"] != "Décontaminé" for s in sites) else 0)
    rh = min(20, phb / max(1, len(sites) + extra))
    fs = min(_pt(11.5), rh * 0.6)
    yy = pyb
    for s in sites:
        S.text(px_, yy, pwb * 0.62, rh, [s["t"]], size=fs, color=ENCRE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
        sh = S.rect(px_ + pwb * 0.64, yy + rh * 0.12, pwb * 0.36, rh * 0.76, s["bg"], radius=4, name="Statut PCI")
        S.text(0, 0, 0, 0, [s["lib"]], size=fs * 0.9, color=s["fg"], bold=True, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        yy += rh
    if x["pci"]["sans"]:
        n = len(x["pci"]["sans"])
        S.text(px_, yy, pwb, rh, [f"? {n} lieu{'x' if n > 1 else ''} d’exposition sans statut PCI :"], size=fs,
               color=ORANGE_T, bold=True, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
        S.text(px_, yy + rh, pwb, rh, [" · ".join(x["pci"]["sans"])], size=fs * 0.92, color=GRIS, align=PP_ALIGN.LEFT,
               anchor=MSO_ANCHOR.MIDDLE)
        yy += 2 * rh
    if any(s["st"] != "Décontaminé" for s in sites):
        S.text(px_, yy, pwb, rh * 1.6, ["Priorité : fermer les sites non décontaminés ; noter date, équipe et produit."],
               size=fs * 0.9, color=GRIS, align=PP_ALIGN.LEFT)
    if not sites and not x["pci"]["sans"]:
        S.text(px_, pyb, pwb, 16, ["Aucun site renseigné."], size=8, color=GRIS, align=PP_ALIGN.LEFT)

    # Actions
    ax, ayb, awb, ahb = boite(2, "Actions", "suggérées, à valider" if x["actions"]["auto"] else "responsable · échéance")
    acts = x["actions"]["lignes"]
    afaire = [a for a in acts if not a["fait"]]
    faites = [a for a in acts if a["fait"]]
    titres = (1 if afaire and not x["actions"]["auto"] else 0) + (1 if faites else 0)
    rh = min(20, ahb / max(1, len(acts) + titres))
    fs = min(_pt(11.5), rh * 0.6)
    yy = ayb
    if afaire and not x["actions"]["auto"]:
        sh = S.rect(ax, yy + 1, awb, rh - 3, "#FFFFFF", "#B3262C", radius=4, line_w=1.2, name="À réaliser immédiatement")
        S.text(0, 0, 0, 0, ["À RÉALISER IMMÉDIATEMENT"], size=fs * 0.8, color="#B3262C", bold=True,
               align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        yy += rh
    for a in afaire:
        sh = S.rect(ax, yy + rh * 0.12, 62, rh * 0.76, a["c"], radius=4, name="Priorité")
        S.text(0, 0, 0, 0, [a["p"]], size=fs * 0.85, color="#FFFFFF", bold=True, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        resp = "" if x["actions"]["auto"] else f"{a['resp'] or 'à désigner'} · {a['ech'] or '—'}"
        tw_ = awb - 70 - (110 if resp else 0)
        S.text(ax + 68, yy, tw_, rh, [a["t"] + (" (en cours)" if a["cours"] else "")], size=fs, color=ENCRE,
               align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
        if resp:
            S.text(ax + awb - 110, yy, 110, rh, [resp], size=fs * 0.88, color=ENCRE if a["resp"] else ORANGE_T,
                   bold=not a["resp"], align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        yy += rh
    if faites:
        S.line(ax, yy + 2, ax + awb, yy + 2, "#B8C0CC", 0.75)
        S.text(ax, yy + 2, awb, rh - 2, ["DÉJÀ RÉALISÉES"], size=fs * 0.8, color="#2E7D4F", bold=True,
               align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
        yy += rh
        for a in faites:
            S.oval(ax + 8, yy + rh / 2, min(7, rh * 0.32), "#2E7D4F", "#FFFFFF", 0.5)
            S.text(ax + 1, yy, 14, rh, ["✓"], size=fs * 0.75, color="#FFFFFF", bold=True, anchor=MSO_ANCHOR.MIDDLE)
            S.text(ax + 22, yy, awb - 22, rh, [a["t"]], size=fs, color=ENCRE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
            yy += rh
    if not acts:
        S.text(ax, ayb, awb, 16, ["Aucune action."], size=8, color=GRIS, align=PP_ALIGN.LEFT)

    # -- pied de page -------------------------------------------------------------------------------------------------
    S.text(22, foot_y, W * 0.6, 16, [[(v.org, {"bold": True, "color": NAVY}),
                                      ((" · " + v.footer) if v.footer else "", {"color": "#000000"})]],
           size=6.4, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, name="Pied de page")
    S.text(W * 0.6, foot_y, W * 0.4 - 22, 16, [v.meta], size=6.4, color="#000000", align=PP_ALIGN.RIGHT,
           anchor=MSO_ANCHOR.MIDDLE)
