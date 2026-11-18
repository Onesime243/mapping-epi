"""Mise en forme des rapports par pilier : graphiques (PNG), rapport détaillé Word, présentation PowerPoint."""
from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional

from config import theme
from core.langue import actuelle, tr, trf
from core.piliers import Graphique, Rapport

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
PALETTE = [theme.BLUE, theme.ORANGE, theme.TEAL, theme.PURPLE, theme.YELLOW, theme.GREEN, theme.GREY]
COULEURS_NOMMEES = {"Fait": theme.GREEN, "En cours": theme.ORANGE, "À faire": theme.BLUE, "Décontaminé": theme.GREEN,
                    "Partiel": theme.ORANGE, "Non": theme.RED, "Inconnu": theme.GREY, "Suivis": theme.BLUE,
                    "Vaccinés": theme.TEAL}
NAVY = (0x1F, 0x3A, 0x5F)


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _couleur(nom: str, i: int) -> str:
    """Couleur d'une série : les noms de série arrivent traduits dans la langue courante."""
    nommees = {tr(k): v for k, v in COULEURS_NOMMEES.items()}
    nommees.update(COULEURS_NOMMEES)
    return nommees.get(nom, PALETTE[i % len(PALETTE)])


def _police(taille: int, gras: bool = False):
    from PIL import ImageFont
    f = FONTS / ("Inter-SemiBold.otf" if gras else "Inter-Regular.otf")
    try:
        return ImageFont.truetype(str(f), taille)
    except OSError:
        return ImageFont.load_default()


def _fmt(v: float) -> str:
    if abs(v - round(v)) < 0.05:
        return f"{v:.0f}"
    return f"{v:.1f}" if actuelle() == "en" else f"{v:.1f}".replace(".", ",")


# ---------------------------------------------------------------------------
# graphique PNG (Pillow, sans connexion ni bibliothèque de graphiques)
# ---------------------------------------------------------------------------
def graphique_png(g: Graphique, w: int = 1600, h: int = 800) -> bytes:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    ft, fl, fs = _police(34, True), _police(24), _police(21)
    d.text((40, 24), g.titre, font=ft, fill=NAVY)
    noms = list(g.series)
    ncat = len(g.categories)
    if not ncat:
        d.text((40, 120), tr("Aucune donnée sur la période."), font=fl, fill=(100, 110, 120))
        return _png(im)
    # légende
    x, y = 40, 76
    if len(noms) > 1:
        for i, n in enumerate(noms):
            d.rectangle([x, y + 4, x + 22, y + 26], fill=_rgb(_couleur(n, i)))
            d.text((x + 30, y), n, font=fl, fill=(60, 70, 80))
            x += 50 + int(d.textlength(n, font=fl))
        y0 = 130
    else:
        y0 = 100
    totaux = [sum(g.series[n][k] for n in noms) for k in range(ncat)] if g.empile else \
        [max(g.series[n][k] for n in noms) for k in range(ncat)]
    vmax = max(totaux) or 1
    pas_axe = _pas_rond(vmax / 4)
    vmax = pas_axe * -(-vmax // pas_axe) if not g.horizontal else vmax     # sommet de l'axe arrondi
    if g.unite == "%" and not g.horizontal:
        vmax, pas_axe = 100, 20
    if g.horizontal:
        lab_w = min(420, max(int(d.textlength(c, font=fl)) for c in g.categories) + 24)
        x0, x1, yb = 40 + lab_w, w - 120, h - 40
        bande = (yb - y0) / ncat
        for k, cat in enumerate(g.categories):
            yc = y0 + k * bande
            d.text((40, yc + bande / 2 - 14), cat[:40], font=fl, fill=(40, 50, 60))
            off = 0.0
            for i, n in enumerate(noms):
                v = g.series[n][k]
                if g.empile:
                    lx0 = x0 + (x1 - x0) * off / vmax
                    lx1 = x0 + (x1 - x0) * (off + v) / vmax
                    hb = bande * 0.62
                    d.rectangle([lx0, yc + (bande - hb) / 2, max(lx0, lx1), yc + (bande + hb) / 2], fill=_rgb(_couleur(n, i)))
                    off += v
                else:
                    hb = bande * 0.7 / len(noms)
                    by = yc + bande * 0.15 + i * hb
                    lx1 = x0 + (x1 - x0) * v / vmax
                    d.rectangle([x0, by, max(x0 + 1, lx1), by + hb - 4], fill=_rgb(_couleur(n, i)))
                    d.text((lx1 + 8, by + hb / 2 - 14), _fmt(v), font=fs, fill=(60, 70, 80))
            if g.empile:
                tx = x0 + (x1 - x0) * off / vmax
                d.text((tx + 8, yc + bande / 2 - 13), _fmt(off), font=fs, fill=(60, 70, 80))
        d.line([x0, y0, x0, yb], fill=(150, 160, 170), width=2)
    else:
        x0, x1, yb = 90, w - 40, h - 110
        nt = int(round(vmax / pas_axe))
        for t in range(nt + 1):                  # quadrillage aux valeurs rondes
            v = pas_axe * t
            yy = yb - (yb - y0) * v / vmax
            d.line([x0, yy, x1, yy], fill=(225, 230, 236), width=1)
            d.text((20, yy - 13), _fmt(v), font=fs, fill=(110, 120, 130))
        bande = (x1 - x0) / ncat
        pas = max(1, ncat // 16)
        for k, cat in enumerate(g.categories):
            xc = x0 + k * bande
            base = 0.0
            for i, n in enumerate(noms):
                v = g.series[n][k]
                if g.empile:
                    t0 = yb - (yb - y0) * base / vmax
                    t1 = yb - (yb - y0) * (base + v) / vmax
                    d.rectangle([xc + bande * 0.18, t1, xc + bande * 0.82, t0], fill=_rgb(_couleur(n, i)))
                    base += v
                else:
                    bw = bande * 0.7 / len(noms)
                    bx = xc + bande * 0.15 + i * bw
                    t1 = yb - (yb - y0) * v / vmax
                    d.rectangle([bx, t1, bx + bw - 3, yb], fill=_rgb(_couleur(n, i)))
                    if v and ncat <= 20:
                        lab = _fmt(v)
                        d.text((bx + (bw - 3) / 2 - d.textlength(lab, font=fs) / 2, t1 - 28), lab, font=fs, fill=(60, 70, 80))
            if g.empile and base and ncat <= 20:
                lab = _fmt(base)
                d.text((xc + bande / 2 - d.textlength(lab, font=fs) / 2, yb - (yb - y0) * base / vmax - 28), lab,
                       font=fs, fill=(60, 70, 80))
            if k % pas == 0:
                c = cat[:14]
                d.text((xc + bande / 2 - d.textlength(c, font=fs) / 2, yb + 12), c, font=fs, fill=(70, 80, 90))
        d.line([x0, yb, x1, yb], fill=(150, 160, 170), width=2)
    if g.note:
        d.text((40, h - 34), g.note, font=_police(19), fill=(120, 130, 140))
    return _png(im)


def _pas_rond(x: float) -> float:
    """Pas d'axe « rond » (1, 2, 5 × 10^n), au moins 1 pour des effectifs."""
    import math
    if x <= 1:
        return 1
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 2, 5, 10):
        if m * e >= x:
            return m * e
    return 10 * e


def _png(im) -> bytes:
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


# ---------------------------------------------------------------------------
# rapport détaillé Word
# ---------------------------------------------------------------------------
def rapport_docx(r: Rapport, path) -> None:
    from docx import Document
    from docx.enum.section import WD_ORIENT  # noqa: F401
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    NAV = RGBColor(*NAVY)
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.8)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)
    for name, size in (("Heading 1", 15), ("Heading 2", 12), ("Heading 3", 11)):
        s = doc.styles[name]
        s.font.name, s.font.size, s.font.bold, s.font.color.rgb = "Calibri", Pt(size), True, NAV
        rf = s.element.rPr.find(qn("w:rFonts"))
        if rf is not None:
            for k in list(rf.attrib):
                if "heme" in k:
                    del rf.attrib[k]

    def shade(cell, fill):
        tcPr = cell._tc.get_or_add_tcPr()
        e = OxmlElement("w:shd")
        e.set(qn("w:val"), "clear"); e.set(qn("w:color"), "auto"); e.set(qn("w:fill"), fill)
        tcPr.append(e)

    def cell(c, txt, bold=False, size=9.5, color=None, align=None):
        c.text = ""
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        if align is not None:
            p.alignment = align
        run = p.add_run(str(txt))
        run.bold, run.font.size = bold, Pt(size)
        if color is not None:
            run.font.color.rgb = color

    def table(headers, rows, widths):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for i, h in enumerate(headers):
            cell(t.rows[0].cells[i], h, True, 9.5, RGBColor(255, 255, 255))
            shade(t.rows[0].cells[i], "1F3A5F")
        for k, row in enumerate(rows):
            cs = t.add_row().cells
            for i, v in enumerate(row):
                cell(cs[i], v)
                if k % 2:
                    shade(cs[i], "F3F6F9")
        for row in t.rows:
            for i, wd in enumerate(widths):
                row.cells[i].width = Cm(wd)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # pied de page numéroté
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run(tr("Mapping Épi · rapport par pilier · page "))
    run.font.size = Pt(8.5)
    for kind, txt in (("begin", None), (None, " PAGE "), ("end", None)):
        r_ = fp.add_run()
        r_.font.size = Pt(8.5)
        if kind:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), kind); r_._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; r_._r.append(e)

    # page de garde
    for txt, size, bold in ((tr("RÉPUBLIQUE DÉMOCRATIQUE DU CONGO"), 12, True),
                            (tr("Système de gestion de l'incident (SGI) : riposte à la Maladie à Virus Ebola"), 11, False)):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ru = p.add_run(txt); ru.bold = bold; ru.font.size = Pt(size); ru.font.color.rgb = NAV
    doc.add_paragraph().paragraph_format.space_after = Pt(70)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ru = p.add_run(tr("RAPPORT D'ANALYSE PAR PILIER")); ru.bold = True; ru.font.size = Pt(24); ru.font.color.rgb = NAV
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ru = p.add_run(tr("Suivi des mappings épidémiologiques des cas de MVE")); ru.font.size = Pt(13)
    doc.add_paragraph().paragraph_format.space_after = Pt(30)
    info = [(tr("Période"), trf("du {debut} au {fin}", debut=f"{r.debut:%d/%m/%Y}", fin=f"{r.fin:%d/%m/%Y}")),
            (tr("Périmètre"), r.perimetre + (f" · {r.province}" if r.province else "")),
            (tr("Cas analysés"), trf("{n} cas notifiés sur la période ({total} au total)", n=r.n_cas, total=r.n_total)),
            (tr("Piliers"), ", ".join(s.titre for s in r.sections)),
            (tr("Généré le"), trf("{date} à {heure}", date=f"{r.genere_le:%d/%m/%Y}", heure=f"{r.genere_le:%H:%M}"))]
    table(["", ""], [[k, v] for k, v in info], [4, 13])
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ru = p.add_run(tr("Généré automatiquement par Mapping Épi à partir des fiches de cas enregistrées. "
                      "À valider par les responsables des piliers avant diffusion."))
    ru.italic = True; ru.font.size = Pt(9); ru.font.color.rgb = RGBColor(0x6B, 0x77, 0x85)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # résumé exécutif et méthode
    doc.add_heading(tr("Résumé exécutif"), level=1)
    for m in r.resume:
        doc.add_paragraph(m, style="List Bullet")
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    for i, h in enumerate([tr("Pilier"), tr("Indicateur clé"), tr("Valeur"), tr("Points d'attention")]):
        cell(t.rows[0].cells[i], h, True, 9.5, RGBColor(255, 255, 255)); shade(t.rows[0].cells[i], "1F3A5F")
    for s in r.sections:
        cs = t.add_row().cells
        cell(cs[0], s.titre, True); cell(cs[1], s.kpis[0][0] if s.kpis else ""); cell(cs[2], s.kpis[0][1] if s.kpis else "")
        cell(cs[3], str(len(s.attention)))
    for row in t.rows:
        for i, wd in enumerate([5.5, 5.5, 3, 3]):
            row.cells[i].width = Cm(wd)
    doc.add_heading(tr("Méthode"), level=2)
    for m in ("Période : cas dont la date de notification (à défaut de confirmation, puis de début des symptômes) tombe "
              "entre les deux dates choisies. Les exemples fictifs et les brouillons sont exclus.",
              "Source : fiches de cas enregistrées dans Mapping Épi, dans le périmètre du compte.",
              "Règle : une information non renseignée n'est jamais remplacée par zéro ; elle est exclue du calcul et "
              "le dénominateur est indiqué entre parenthèses.",
              "Questions : sélection du cadre d'analyse des mappings MVE (UMIE-INRB) ; celles qui demandent des données "
              "absentes de l'outil sont listées en annexe."):
        doc.add_paragraph(tr(m), style="List Bullet")

    fig = 0
    for n, s in enumerate(r.sections, 1):
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        doc.add_heading(f"{n}. {s.titre}", level=1)
        p = doc.add_paragraph(); ru = p.add_run(s.objectif); ru.italic = True
        # indicateurs clés : une ligne de tuiles
        t = doc.add_table(rows=2, cols=len(s.kpis))
        for i, (lib, val) in enumerate(s.kpis):
            cell(t.rows[0].cells[i], val, True, 16, NAV, WD_ALIGN_PARAGRAPH.CENTER)
            cell(t.rows[1].cells[i], lib, False, 8.5, RGBColor(0x55, 0x5F, 0x6B), WD_ALIGN_PARAGRAPH.CENTER)
            shade(t.rows[0].cells[i], "EEF2F6"); shade(t.rows[1].cells[i], "EEF2F6")
        doc.add_paragraph()
        for g in s.graphiques:
            fig += 1
            doc.add_picture(io.BytesIO(graphique_png(g)), width=Cm(16.5))
            cap = doc.add_paragraph(f"{tr('Figure')} {fig}. {g.titre}")
            cap.runs[0].italic = True; cap.runs[0].font.size = Pt(9)
        doc.add_heading(tr("Questions d'analyse"), level=2)
        table([tr("Question"), tr("Réponse")], s.questions, [7.5, 9.5])
        for titre, headers, rows in s.tableaux:
            doc.add_heading(titre, level=3)
            table(headers, rows, [17 / len(headers)] * len(headers))
        doc.add_heading(tr("Points d'attention"), level=2)
        for a in s.attention or [tr("Aucun point d'attention majeur sur la période.")]:
            doc.add_paragraph(a, style="List Bullet")

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading(tr("Annexe : questions non couvertes faute de données"), level=1)
    doc.add_paragraph(tr("Ces questions du cadre d'analyse demandent des informations que l'outil ne recueille pas encore. "
                         "Les ajouter permettrait d'y répondre dans les prochains rapports."))
    table([tr("Axe"), tr("Question"), tr("Donnée nécessaire")], [list(x) for x in r.non_couverts], [3, 8, 6])
    doc.save(str(path))


# ---------------------------------------------------------------------------
# présentation PowerPoint (graphiques natifs, modifiables)
# ---------------------------------------------------------------------------
def rapport_pptx(r: Rapport, path) -> None:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    vide = prs.slide_layouts[6]
    NAV = RGBColor(*NAVY)
    GRIS = RGBColor(0x5F, 0x6B, 0x7A)

    def texte(sl, x, y, w, h, txt, size=14, bold=False, color=None, align=None):
        tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        lignes = txt if isinstance(txt, list) else [txt]
        for i, l in enumerate(lignes):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = l
            p.font.size, p.font.bold = Pt(size), bold
            p.font.color.rgb = color or RGBColor(0x1B, 0x24, 0x30)
            if align is not None:
                p.alignment = align
            p.space_after = Pt(6)
        return tb

    def bandeau(sl, titre, sous=""):
        bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.95))
        bar.fill.solid(); bar.fill.fore_color.rgb = NAV; bar.line.fill.background()
        texte(sl, 0.5, 0.18, 12.3, 0.6, titre, 26, True, RGBColor(255, 255, 255))
        if sous:
            texte(sl, 0.5, 1.02, 12.3, 0.4, sous, 12, False, GRIS)
        pied = "Mapping Épi · " + trf("{debut} au {fin}", debut=f"{r.debut:%d/%m/%Y}", fin=f"{r.fin:%d/%m/%Y}") \
            + (f" · {r.province}" if r.province else "")
        texte(sl, 0.5, 7.05, 12.3, 0.3, pied, 9, False, GRIS)

    # 1. titre
    sl = prs.slides.add_slide(vide)
    fond = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    fond.fill.solid(); fond.fill.fore_color.rgb = NAV; fond.line.fill.background()
    texte(sl, 0.8, 2.2, 11.7, 1, tr("Rapport d'analyse par pilier"), 40, True, RGBColor(255, 255, 255))
    texte(sl, 0.8, 3.3, 11.7, 0.6, tr("Riposte à la Maladie à Virus Ebola · suivi des mappings épidémiologiques"), 18, False,
          RGBColor(0xDD, 0xE6, 0xEF))
    texte(sl, 0.8, 4.4, 11.7, 1.2, [trf("Période : du {debut} au {fin}", debut=f"{r.debut:%d/%m/%Y}", fin=f"{r.fin:%d/%m/%Y}"),
                                     trf("Périmètre : {p}", p=r.perimetre) + (f" · {r.province}" if r.province else ""),
                                     trf("{n} cas analysés", n=r.n_cas)], 16, False, RGBColor(255, 255, 255))
    # 2. résumé exécutif
    sl = prs.slides.add_slide(vide)
    bandeau(sl, tr("Messages clés"), tr("Généré à partir des fiches enregistrées ; à valider en réunion"))
    texte(sl, 0.7, 1.6, 12, 5.2, [f"•  {m}" for m in r.resume], 18)

    for s in r.sections:
        sl = prs.slides.add_slide(vide)
        bandeau(sl, s.titre, s.objectif)
        k = s.kpis[:4]
        tw = 12.3 / max(1, len(k))
        for i, (lib, val) in enumerate(k):
            x = 0.5 + i * tw
            box = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.05), Inches(1.55), Inches(tw - 0.15), Inches(1.15))
            box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xEE, 0xF2, 0xF6); box.line.fill.background()
            texte(sl, x + 0.1, 1.6, tw - 0.25, 0.6, val, 22, True, NAV, PP_ALIGN.CENTER)
            texte(sl, x + 0.1, 2.2, tw - 0.25, 0.45, lib, 11, False, GRIS, PP_ALIGN.CENTER)
        if s.graphiques:
            g = s.graphiques[0]
            cd = CategoryChartData()
            cd.categories = g.categories
            for n, v in g.series.items():
                cd.add_series(n, v)
            if g.horizontal:
                ct = XL_CHART_TYPE.BAR_STACKED if g.empile else XL_CHART_TYPE.BAR_CLUSTERED
            else:
                ct = XL_CHART_TYPE.COLUMN_STACKED if g.empile else XL_CHART_TYPE.COLUMN_CLUSTERED
            gf = sl.shapes.add_chart(ct, Inches(0.5), Inches(2.95), Inches(7.6), Inches(4.0), cd)
            ch = gf.chart
            ch.has_title = True
            ch.chart_title.text_frame.text = g.titre
            ch.chart_title.text_frame.paragraphs[0].font.size = Pt(13)
            ch.chart_title.text_frame.paragraphs[0].font.bold = True
            ch.has_legend = len(g.series) > 1
            if ch.has_legend:
                ch.legend.position = XL_LEGEND_POSITION.BOTTOM
                ch.legend.include_in_layout = False
                ch.legend.font.size = Pt(10)
            ch.category_axis.tick_labels.font.size = Pt(10)
            ch.value_axis.tick_labels.font.size = Pt(10)
            ch.value_axis.has_major_gridlines = True
            for i, ser in enumerate(ch.series):
                ser.format.fill.solid()
                ser.format.fill.fore_color.rgb = RGBColor(*_rgb(_couleur(ser.name, i)))
            if g.horizontal:
                ch.category_axis.reverse_order = True
            pl = ch.plots[0]
            pl.has_data_labels = True
            pl.data_labels.font.size = Pt(10)
            pl.data_labels.number_format = '0'
            pl.data_labels.number_format_is_linked = False
        msgs = s.attention[:3] or [tr("Aucun point d'attention majeur sur la période.")]
        texte(sl, 8.4, 3.0, 4.5, 0.4, tr("Points d'attention"), 15, True, NAV)
        texte(sl, 8.4, 3.45, 4.5, 3.5, [f"•  {m}" for m in msgs], 13)

    sl = prs.slides.add_slide(vide)
    bandeau(sl, tr("Questions non couvertes et prochaines étapes"), tr("Données à ajouter dans l'outil pour répondre au cadre complet"))
    texte(sl, 0.7, 1.6, 12, 5.3, [f"•  {a} : {q} ({dn})" for a, q, dn in r.non_couverts[:9]], 13)
    prs.save(str(path))
