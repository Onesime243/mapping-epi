"""Export PowerPoint NATIF du mapping repensé (v1.8) : mêmes zones que render/templates/mapping.html.j2.

Tout est en formes PowerPoint modifiables (aucune image) : en-tête à trois chiffres, ligne des dates, frise à
l'échelle du temps, cartes des étapes, blocs Contacts / PCI / Actions, pied de page. Géométrie en pixels CSS
de la page 1280 × 720 (1 px = 0,75 pt).
"""
from __future__ import annotations

from typing import Optional

from pptx import Presentation
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
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

    # -- bandeau d'identité (11 cases) ------------------------------------------------------------------------------
    from config import theme as TH
    import math
    ids = v.identity
    iw = (W - 44) / max(1, len(ids))
    S.rect(22, 80, W - 44, 46, PAPIER, BORD, radius=9, name="Identité")
    for i, cid in enumerate(ids):
        cx_ = 22 + i * iw
        if i:
            S.line(cx_, 80, cx_, 126, BORD, 0.75)
        S.text(cx_ + 3, 85, iw - 6, 12, [cid["k"].upper()], size=6, color="#000000", bold=True)
        S.text(cx_ + 3, 97, iw - 6, 24, [cid["v"]], size=fit_pt([(cid["v"], 1)], iw - 8, 22, _pt(14), 6),
               color=cid.get("color") or "#000000", bold=True, anchor=MSO_ANCHOR.MIDDLE)

    # -- ligne « Chronologie du parcours » : badges, ce qui manque, légende -------------------------------------------
    ry = 136
    sh = S.rect(22, ry, 190, 20, "#1F3A5F", radius=4, name="Étiquette chronologie")
    S.text(0, 0, 0, 0, ["CHRONOLOGIE DU PARCOURS"], size=7.1, color="#FFFFFF", bold=True, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
    bx_ = 218
    badges = []
    if v.contact:
        badges.append((v.contact["t"] + ((" " + v.contact["src"]) if v.contact.get("src") else ""), v.contact["fill"], v.contact["ink"]))
        if v.contact.get("todo"):
            badges.append(("ID DU CAS SOURCE : À COMPLÉTER", "#FFFFFF", "#B3262C"))
    for b in v.badges:
        badges.append((b["t"].upper(), "#FFFFFF", "#B3262C") if b.get("todo") else (b["t"], b["fill"], b["ink"]))
    for t_, fill, ink in badges:
        bw_ = 20 + len(t_) * 6.0
        sh = S.rect(bx_, ry, bw_, 20, fill, "#B3262C" if fill == "#FFFFFF" else None, radius=4, name="Badge")
        S.text(0, 0, 0, 0, [t_], size=7, color=ink, bold=True, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        bx_ += bw_ + 6
    if x["manque"]:
        manque = "? " + " · ".join(x["manque"])
        mw = min(W - 22 - 330 - bx_, 22 + len(manque) * 5.0)
        if mw > 60:
            sh = S.rect(bx_, ry, mw, 20, "#FFF1DC", "#F0C78A", radius=9, name="À compléter")
            S.text(0, 0, 0, 0, [manque], size=fit_pt([(manque, 1)], mw - 12, 18, 7.1, 5), color=ORANGE_T, bold=True,
                   anchor=MSO_ANCHOR.MIDDLE, shape=sh)
    leg = "J±n : jours depuis le J0 " + (f"retenu (date rapportée − {v.recul} j)" if v.recul else "retenu ou estimé")
    if x["frise"] and x["frise"]["adapte"]:
        leg += " · jours chargés agrandis"
    S.text(W - 22 - 330, ry, 330, 20, [leg], size=6.6, color="#000000", align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

    # -- bande des 5 phases (chevrons) --------------------------------------------------------------------------------
    py_, ph_h = 163, 44
    strip = v.phase_strip
    if strip:
        pw_ = (W - 44) / len(strip)
        for i, pz in enumerate(strip):
            px0 = 22 + i * pw_
            forme = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
            sh = S.rect(px0, py_, pw_ + 6, ph_h, pz["fill"], shape=forme, name="Phase " + pz["label"])
            try:
                sh.adjustments[0] = 0.25
            except Exception:
                pass
            ink = TH.ink_on(pz["fill"])
            S.text(px0 + (10 if i == 0 else 16), py_ + 2, pw_ - 26, ph_h - 4,
                   [[(f"{i + 1}. {pz['label'].upper()}", {"bold": True}), (" · " + pz["contag"], {})],
                    [(pz["dates"], {"bold": True})], [(pz["detail"], {"size": 5.6})]],
                   size=6.3, color=ink, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, line_spacing=0.95)

    # -- frise à l'échelle du temps (axe, points, trou, repère) --------------------------------------------------------
    fx, fw, ft = 26, W - 52, 214
    f = x["frise"]
    if f:
        X = lambda pct: fx + fw * pct / 100.0                                                    # noqa: E731
        if f["trou"]:
            t = f["trou"]
            gw = max(30, fw * t["w"] / 100.0 - 2)
            sh = S.rect(X(t["l"]), ft, gw, 14, "#FFF6E8", "#C76A00", radius=4, line_w=1.0, name="Trou de chronologie")
            sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            S.text(0, 0, 0, 0, [t["t"]], size=fit_pt([(t["t"], 1)], gw - 6, 13, 6.4, 4.5), color=ORANGE_T, bold=True,
                   anchor=MSO_ANCHOR.MIDDLE, shape=sh)
        S.rect(fx, ft + 23, fw, 2, "#C9C2B3", name="Axe du temps")
        for r in f["reperes"]:
            S.line(X(r["x"]), ft, X(r["x"]), ft + 27, NAVY, 1.1)
            S.text(X(r["x"]) + 3, ft - 1, 80, 11, [r["t"]], size=6, color=NAVY, bold=True, align=PP_ALIGN.LEFT)
        for p in f["points"]:
            S.oval(X(p["x"]), ft + 24, 5.5, p["c"], FOND, 1.5)
        for t in f["ticks"]:
            S.text(X(t["x"]) - 24, ft + 29, 48, 11, [t["t"]], size=6.4, color="#000000")
    else:
        S.text(22, ft + 8, 700, 18, ["Aucune date dans la chronologie : renseigner les dates des étapes pour afficher la frise."],
               size=8.2, color=GRIS, align=PP_ALIGN.LEFT)

    # -- zones du bas : calculées depuis le pied de page -------------------------------------------------------------
    two = len(v.rows) > 1
    foot_y = H - 6 - 16
    bas_h = 150 if two else 190
    bas_y = foot_y - 7 - bas_h
    cy0, cy1 = ft + 44 + 7, bas_y - 7

    # -- cartes des étapes : ligne des phases au-dessus, barre de couleur, contenu centré ------------------------------
    cartes = x["cartes"]
    per = len(v.rows[0]) if v.rows and v.rows[0] else 1
    nrows = max(1, len(v.rows))
    cw = (W - 44 - (per - 1) * 6) / per
    rang_h = (cy1 - cy0 - (nrows - 1) * 6) / nrows
    ch = rang_h - 18                                   # 15 px de ligne des phases + 3 px
    pill_h = 16 if two else 18

    def lignes(c):
        out = [(c["date"] + (f"  {c['rel']}" if c["rel"] else ""), 0.92), (c["lieu"], 1.0), ("●", 1.6), (c["titre"], 1.05)]
        if c["desc"] and not two:
            out.append((c["desc"], 0.82))
        out += [(("⚠ " if ch_.get("warn") else "") + ch_["t"], 0.78) for ch_ in c["chips"]]
        if c["personnes"]:
            out.append(("? personnes présentes", 0.8))
        return out
    taille = min([fit_pt(lignes(c), cw - 14, ch - pill_h - 20, _pt(10 if two else 11.5), 4.5) for c in cartes] or [8])
    for r_ in range(nrows):
        ry0 = cy0 + r_ * (rang_h + 6)
        for b in (v.bands[r_] if r_ < len(v.bands) else []):
            bc = TH.soft(TH.PHASES[b.phase]["color"])
            sh = S.rect(22 + (b.col - 1) * (cw + 6), ry0, b.span * cw + (b.span - 1) * 6, 15, bc, radius=4, name="Phase")
            S.text(0, 0, 0, 0, [b.label.upper()], size=6.4, color=TH.ink_on(bc), bold=True, anchor=MSO_ANCHOR.MIDDLE, shape=sh)
    for i, c in enumerate(cartes):
        r_, col = divmod(i, per)
        bx, by = 22 + col * (cw + 6), cy0 + r_ * (rang_h + 6) + 18
        card = S.rect(bx, by, cw, ch, PAPIER, BORD, radius=8, name=f"Étape {i + 1}")
        if c["incertain"]:
            card.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        S.rect(bx + 1, by + 1, cw - 2, 4, c["tc"], name="Barre du type")
        # haut : date et lieu ; puis le rond du type ; puis le type, la description et les pastilles
        px_t = taille / 0.75
        cpl = max(4, int((cw - 14) / (px_t * 0.55)))
        n_lieu = max(1, math.ceil(len(c["lieu"]) / cpl))
        h_haut = (1 + n_lieu) * px_t * 1.25 + 4
        S.text(bx + 6, by + 7, cw - 12, h_haut, [[(c["date"], {"bold": True, "color": c["tc"], "size": taille * 0.92}),
                                                   (("  " + c["rel"]) if c["rel"] else "", {"bold": True, "color": "#000000", "size": taille * 0.75})],
                                                  [(c["lieu"], {"bold": True, "color": ENCRE})]], size=taille, color=ENCRE)
        r_ic = max(5, px_t * 0.85)
        yic = by + 7 + h_haut + r_ic
        S.oval(bx + cw / 2, yic, r_ic, c["tc"], "#FFFFFF", 1.0)
        pars = [[(c["titre"], {"color": ENCRE, "bold": True, "size": taille * 1.02})]]
        if c["desc"] and not two:
            pars.append([(c["desc"], {"color": "#000000", "size": taille * 0.82})])
        for ch_ in c["chips"]:
            pars.append([(("⚠ " if ch_.get("warn") else "") + ch_["t"],
                          {"color": "#8E1F24" if ch_.get("warn") else "#1F3A5F", "bold": True, "size": taille * 0.78})])
        if c["personnes"]:
            pars.append([("? personnes présentes", {"color": ORANGE_T, "bold": True, "size": taille * 0.8})])
        y_bas = yic + r_ic + 3
        S.text(bx + 6, y_bas, cw - 12, max(10, by + ch - pill_h - 8 - y_bas), pars, size=taille, color=ENCRE)
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
    extra = (3 if x["pci"]["sans"] else 0) + (1 if any(s["st"] != "Décontaminé" for s in sites) else 0)
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
        noms = " · ".join(x["pci"]["sans"])
        S.text(px_, yy + rh, pwb, 2 * rh, [noms], size=fit_pt([(noms, 1)], pwb, 2 * rh, fs * 0.92, 4.5), color=GRIS,
               align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP)
        yy += 3 * rh
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
