"""Modèles Word (.docx) et PowerPoint (.pptx) du narratif, avec tous les champs du modèle Excel.

Les équipes de terrain rédigent leurs narratifs dans Word ou PowerPoint. Ces modèles reprennent exactement les
champs et les en-têtes du classeur Excel (core/excel_model.py : CASE_SECTIONS, TABLES, LISTS) sous forme de
tableaux. À l'import, ces tableaux sont lus champ par champ (comme une feuille Excel) au lieu d'être devinés dans le
récit : l'extraction est complète et exacte.

Organisation (Word et PowerPoint) :
    I à IV   tableaux « Champ | Valeur | Aide » : identification, localisation, clinique et issue, investigation
    V        chronologie en deux tableaux reliés par la colonne « N° » (1/2 : quand et où ; 2/2 : expositions)
    VI à X   lieux, contacts, PCI, laboratoire, actions (une ligne = un élément, en-têtes de l'Excel)
    XI       récit libre (facultatif, non importé : sert à la lecture humaine)

Règles de lecture : un tableau est reconnu par sa ligne d'en-têtes ; les lignes vides sont ignorées ; on peut ajouter
des lignes (Word : touche Tab dans la dernière cellule ; PowerPoint : clic droit > Insérer des lignes, ou dupliquer
la diapositive en continuant la numérotation N°). Les libellés et les en-têtes ne doivent pas être modifiés.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import theme
from core.excel_model import CASE_SECTIONS, LISTS, TABLES
from core.models import Case
from core.storage import ALIAS, ESSENTIEL, _field_type, _from_cell, _to_cell

MARQUEUR = "Modèle Mapping Épi"
VERSION = "1"
N_COL = "N°"

# chronologie : deux tableaux reliés par N° (17 colonnes ne tiennent pas lisiblement sur une page ou une diapositive)
CHRONO_1 = ["date_debut", "date_fin", "heure", "heure_approx", "date_incertaine", "lieu", "lieu_arrivee", "type", "titre"]
CHRONO_2 = ["description", "transport", "personnes", "contact_corps", "liquides", "sans_pci", "securise", "risque"]
LIGNES_VIDES = {"Chronologie": 12, "Lieux": 8, "Contacts": 10, "PCI": 6, "Laboratoire": 4, "Actions": 8}
NUMEROS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]

CONSIGNES = [
    ("Inconnu", "laisser la case VIDE (ou « ? » pour un nombre de contacts). Ne jamais écrire 0 quand on ne sait pas."),
    ("Dates", "JJ/MM/AAAA (ex. 18/08/2026). Laboratoire : JJ/MM/AAAA HH:MM (ex. 30/08/2026 21:00)."),
    ("Oui / non", "écrire « oui » ou laisser vide (Heure approx., Date incertaine, Contact corps, Liquides, Sans PCI, Sécurisé)."),
    ("Listes", "pour les colonnes à choix, recopier une des valeurs indiquées sous le tableau (ex. Hospitalisation)."),
    ("Chronologie", "une ligne = une étape, numérotée dans la colonne N° ; la même étape garde le même N° dans les deux tableaux."),
    ("Ajouter des lignes", "Word : touche Tab dans la dernière cellule. PowerPoint : clic droit > Insérer, ou dupliquer la diapositive en continuant les N°."),
    ("Ne pas modifier", "les libellés de la colonne « Champ » ni les en-têtes des tableaux : l'import s'appuie dessus."),
    ("Importer", "dans l'outil : « Importer une fiche », choisir ce fichier. Vérifier ensuite chaque onglet."),
]

NAVY = theme.NAVY
JAUNE = "FFF4D6"
BLEU_CLAIR = "E3EDF9"
GRIS = "5F6B7A"


# ---------------------------------------------------------------------------
# Description des champs (une seule source : le modèle Excel)
# ---------------------------------------------------------------------------
def _cols(sheet: str) -> List[tuple]:
    return next(cols for s, _t, _c, cols in TABLES if s == sheet)


def _table_info(sheet: str) -> Tuple[str, str]:
    t = next(x for x in TABLES if x[0] == sheet)
    return t[1], t[2]


def _col(sheet: str, key: str) -> tuple:
    return next(c for c in _cols(sheet) if c[0] == key)


@dataclass
class Bloc:
    """Un tableau du modèle : titre, consigne, en-têtes (libellés lus à l'import) et valeurs possibles."""
    sheet: str
    titre: str
    consigne: str
    cles: List[str]
    numerote: bool = False
    lignes: List[List[str]] = field(default_factory=list)

    @property
    def entetes(self) -> List[str]:
        return ([N_COL] if self.numerote else []) + [_col(self.sheet, k)[1] for k in self.cles]

    @property
    def choix(self) -> List[str]:
        out = []
        for k in self.cles:
            _k, label, _w, kind, _aide = _col(self.sheet, k)
            if kind in LISTS and kind != "bool":
                out.append(f"{label} : " + ", ".join(LISTS[kind]))
        return out


def blocs(case: Optional[Case] = None) -> List[Bloc]:
    out: List[Bloc] = []
    for sheet, titre, consigne, cols in TABLES:
        items = list(getattr(case, _attr(sheet))) if case else []
        if sheet == "Chronologie":
            for part, cles, sous in ((1, CHRONO_1, "quand et où"), (2, CHRONO_2, "expositions et risque")):
                b = Bloc(sheet, f"CHRONOLOGIE DU PARCOURS ({part}/2) : {sous.upper()}",
                         consigne if part == 1 else "Même N° que dans le tableau 1/2. Risque vide = calcul automatique.",
                         cles, numerote=True)
                b.lignes = [[str(i)] + [_txt(getattr(e, k)) for k in cles] for i, e in enumerate(items, 1)]
                out.append(b)
        else:
            cles = [c[0] for c in cols]
            b = Bloc(sheet, titre, consigne, cles)
            b.lignes = [[_txt(getattr(x, k), sheet, k) for k in cles] for x in items]
            out.append(b)
    return out


def _attr(sheet: str) -> str:
    return {"Chronologie": "events", "Lieux": "places", "Contacts": "contacts", "PCI": "ipc",
            "Laboratoire": "labs", "Actions": "actions"}[sheet]


def _txt(v, sheet: str = "", key: str = "") -> str:
    if v is None:
        return "?" if sheet == "Contacts" and key in ("nombre",) else ""
    v = _to_cell(v)
    return "" if v is None else str(v)


def champs_cas(case: Optional[Case] = None) -> List[Tuple[str, List[Tuple[str, str, str, bool, str]]]]:
    """[(section, [(clé, libellé, valeur, obligatoire, aide)])]"""
    out = []
    for section, fields in CASE_SECTIONS:
        rows = []
        for key, label, aide, req, kind in fields:
            val = ""
            if case is not None:
                v = getattr(case, key)
                if key == "note_pied":
                    v = v if v and v != Case().note_pied else ""
                val = "" if v in (None, "Inconnu") and key not in ("sexe", "issue", "contact_connu") else _txt(v)
            if kind in LISTS and kind != "bool" and not any(x in aide for x in LISTS[kind][:2]):
                aide = (aide + " : " if aide else "") + " / ".join(LISTS[kind])
            rows.append((key, label, val, req, aide))
        out.append((section, rows))
    return out


# ---------------------------------------------------------------------------
# Génération Word
# ---------------------------------------------------------------------------
def generer_docx(path: Path | str, case: Optional[Case] = None) -> None:
    import docx
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10)
    sec = d.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for m in ("left_margin", "right_margin"):
        setattr(sec, m, Cm(1.6))
    sec.top_margin = sec.bottom_margin = Cm(1.4)
    navy = RGBColor.from_string(NAVY[1:])
    gris = RGBColor.from_string(GRIS)

    def shade(cell, hex_fill):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_fill)
        tcPr.append(shd)

    def write(cell, text, bold=False, color=None, size=None, italic=False):
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(text)
        r.bold, r.italic = bold, italic
        if color is not None:
            r.font.color.rgb = color
        if size:
            r.font.size = Pt(size)
        p.paragraph_format.space_after = Pt(0)

    def repeat_header(row):
        trPr = row._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        trPr.append(el)

    def heading(text):
        p = d.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = navy

    def note(text, size=8.5):
        p = d.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.italic = True
        r.font.size = Pt(size)
        r.font.color.rgb = gris

    # --- titre et consignes
    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("NARRATIF DU CAS : MAPPING DU PARCOURS ÉPIDÉMIOLOGIQUE")
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = navy
    s = d.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run(f"{MARQUEUR} (Word) v{VERSION} : à remplir puis importer dans l'outil (« Importer une fiche »)")
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = gris
    box = d.add_table(rows=len(CONSIGNES) + 1, cols=2)
    box.style = "Table Grid"
    box.alignment = WD_TABLE_ALIGNMENT.CENTER
    write(box.rows[0].cells[0], "COMMENT REMPLIR", bold=True, color=RGBColor(255, 255, 255), size=9)
    box.rows[0].cells[0].merge(box.rows[0].cells[1])
    shade(box.rows[0].cells[0], NAVY[1:])
    for i, (k, v) in enumerate(CONSIGNES, 1):
        write(box.rows[i].cells[0], k, bold=True, size=8.5)
        write(box.rows[i].cells[1], v, size=8.5)
        shade(box.rows[i].cells[0], BLEU_CLAIR)
    for row in box.rows:
        row.cells[0].width, row.cells[1].width = Cm(3.6), Cm(14.2)

    # --- I à IV : champs du cas
    for n, (section, rows) in enumerate(champs_cas(case)):
        heading(f"{NUMEROS[n]}. {section}")
        tb = d.add_table(rows=1 + len(rows), cols=3)
        tb.style = "Table Grid"
        tb.autofit = False
        for j, h in enumerate(("Champ", "Valeur", "Aide (valeurs possibles)")):
            write(tb.rows[0].cells[j], h, bold=True, color=RGBColor(255, 255, 255), size=9)
            shade(tb.rows[0].cells[j], NAVY[1:])
        for i, (_k, label, val, req, aide) in enumerate(rows, 1):
            c0, c1, c2 = tb.rows[i].cells
            write(c0, label, bold=True, size=9.5)
            write(c1, val, size=10)
            write(c2, aide, italic=True, color=gris, size=8)
            if req:
                shade(c1, JAUNE)
        for j, w in enumerate((Cm(4.6), Cm(6.6), Cm(6.6))):
            tb.columns[j].width = w
            for row in tb.rows:
                row.cells[j].width = w
    note("Cases jaunes : indispensables au mapping. Une information inconnue reste vide (affichée « ? »).")

    # --- V à X : tableaux (pages paysage)
    land = d.add_section()
    land.orientation = WD_ORIENT.LANDSCAPE
    land.page_width, land.page_height = Cm(29.7), Cm(21)
    for m in ("left_margin", "right_margin"):
        setattr(land, m, Cm(1.3))
    usable = 29.7 - 2.6
    num = 4
    for b in blocs(case):
        if b.sheet == "Chronologie" and b.titre.startswith("CHRONOLOGIE DU PARCOURS (2/2)"):
            heading(f"{NUMEROS[num - 1]}. {b.titre}")
        else:
            heading(f"{NUMEROS[num]}. {b.titre}")
            num += 1
        note(b.consigne, 8.5)
        n_rows = max(len(b.lignes) + 2, LIGNES_VIDES[b.sheet]) if case else LIGNES_VIDES[b.sheet]
        tb = d.add_table(rows=1 + n_rows, cols=len(b.entetes))
        tb.style = "Table Grid"
        tb.autofit = False
        hdr = tb.rows[0]
        repeat_header(hdr)
        widths = ([1.0] if b.numerote else []) + [_col(b.sheet, k)[2] for k in b.cles]
        scale = usable / sum(widths)
        for j, h in enumerate(b.entetes):
            write(hdr.cells[j], h, bold=True, color=RGBColor(255, 255, 255), size=8)
            shade(hdr.cells[j], NAVY[1:])
        for i in range(n_rows):
            row = tb.rows[i + 1]
            vals = b.lignes[i] if i < len(b.lignes) else ([str(i + 1)] + [""] * len(b.cles) if b.numerote else [""] * len(b.cles))
            for j, v in enumerate(vals):
                write(row.cells[j], v, size=8.5)
        for j, w in enumerate(widths):
            tb.columns[j].width = Cm(max(1.0, w * scale))
            for row in tb.rows:
                row.cells[j].width = Cm(max(1.0, w * scale))
        for ch in b.choix:
            note("Valeurs possibles : " + ch, 7.5)

    heading(f"{NUMEROS[num]}. RÉCIT LIBRE, DÉFIS ET DIFFICULTÉS (facultatif, non importé)")
    note("Texte libre pour la lecture humaine du narratif. Les informations utiles au mapping doivent être "
         "reportées dans les tableaux ci-dessus.")
    d.add_paragraph("")
    d.save(str(path))


# ---------------------------------------------------------------------------
# Génération PowerPoint
# ---------------------------------------------------------------------------
def generer_pptx(path: Path | str, case: Optional[Case] = None) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    navy = RGBColor.from_string(NAVY[1:])
    blanc = RGBColor(255, 255, 255)
    gris = RGBColor.from_string(GRIS)
    W = 13.333
    M = 0.35

    def slide(title: str, sub: str = ""):
        s = prs.slides.add_slide(blank)
        bar = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(0.72))
        bar.fill.solid()
        bar.fill.fore_color.rgb = navy
        bar.line.fill.background()
        tf = bar.text_frame
        tf.margin_left = Inches(M)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = title
        r.font.size, r.font.bold, r.font.color.rgb = Pt(20), True, blanc
        if sub:
            tb = s.shapes.add_textbox(Inches(M), Inches(0.78), Inches(W - 2 * M), Inches(0.35))
            tb.text_frame.word_wrap = True
            r = tb.text_frame.paragraphs[0].add_run()
            r.text = sub
            r.font.size, r.font.italic, r.font.color.rgb = Pt(10.5), True, gris
        foot = s.shapes.add_textbox(Inches(M), Inches(7.12), Inches(W - 2 * M), Inches(0.3))
        r = foot.text_frame.paragraphs[0].add_run()
        r.text = f"{MARQUEUR} (PowerPoint) v{VERSION} : ne pas modifier les libellés ni les en-têtes des tableaux"
        r.font.size, r.font.color.rgb = Pt(8), gris
        return s

    def cell(c, text, size, bold=False, color=None, fill=None, italic=False):
        c.text = ""
        tf = c.text_frame
        tf.word_wrap = True
        c.margin_left = c.margin_right = Emu(45720)
        c.margin_top = c.margin_bottom = Emu(18288)
        r = tf.paragraphs[0].add_run()
        r.text = text
        r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
        r.font.color.rgb = color or RGBColor(0x1B, 0x24, 0x30)
        c.fill.solid()
        c.fill.fore_color.rgb = fill or blanc

    def table(s, top, n_rows, widths, height_row=0.27):
        shp = s.shapes.add_table(n_rows, len(widths), Inches(M), Inches(top), Inches(W - 2 * M),
                                 Inches(height_row * n_rows))
        t = shp.table
        tot = sum(widths)
        for j, w in enumerate(widths):
            t.columns[j].width = Inches((W - 2 * M) * w / tot)
        for r in t.rows:
            r.height = Inches(height_row)
        return t

    # --- couverture + consignes
    s = slide("NARRATIF DU CAS : MAPPING DU PARCOURS ÉPIDÉMIOLOGIQUE",
              "Modèle PowerPoint : remplir les tableaux puis importer le fichier dans l'outil (« Importer une fiche »)")
    t = table(s, 1.3, len(CONSIGNES) + 1, [2.2, 9.0], 0.5)
    cell(t.cell(0, 0), "COMMENT REMPLIR", 12, True, blanc, navy)
    cell(t.cell(0, 1), "", 12, fill=navy)
    for i, (k, v) in enumerate(CONSIGNES, 1):
        cell(t.cell(i, 0), k, 11.5, True, fill=RGBColor.from_string(BLEU_CLAIR))
        cell(t.cell(i, 1), v, 11.5)

    # --- I à IV : champs du cas (sections regroupées, 12 lignes au plus par diapositive)
    sections = [(NUMEROS[i], sec, rows) for i, (sec, rows) in enumerate(champs_cas(case))]
    groupes: List[list] = []
    for item in sections:
        if groupes and sum(len(r) + 1 for _n, _s, r in groupes[-1]) + len(item[2]) + 1 <= 12:
            groupes[-1].append(item)
        else:
            groupes.append([item])
    for grp in groupes:
        part = [(sec, rows) for _n, sec, rows in grp]
        titre = " • ".join(f"{n}. {sec}" for n, sec, _r in grp)
        s = slide(titre, "Cases jaunes : indispensables. Inconnu : laisser vide.")
        rows = []
        for sec, rr in part:
            rows.append(("§", sec, "", False, ""))
            rows += rr
        hrow = min(0.29, 5.85 / (len(rows) + 1))
        size = 10 if hrow >= 0.27 else 9
        t = table(s, 1.2, len(rows) + 1, [3.0, 4.2, 5.4], hrow)
        for j, h in enumerate(("Champ", "Valeur", "Aide (valeurs possibles)")):
            cell(t.cell(0, j), h, size, True, blanc, navy)
        for i, (k, label, val, req, aide) in enumerate(rows, 1):
            if k == "§":
                for j in range(3):
                    cell(t.cell(i, j), label if j == 0 else "", size - 0.5, True, navy, RGBColor.from_string(BLEU_CLAIR))
                continue
            cell(t.cell(i, 0), label, size, True)
            cell(t.cell(i, 1), val, size, fill=RGBColor.from_string(JAUNE) if req else None)
            cell(t.cell(i, 2), aide, size - 1.5, italic=True, color=gris)

    # --- V à X : tableaux
    num = 4
    for b in blocs(case):
        if b.titre.startswith("CHRONOLOGIE DU PARCOURS (2/2)"):
            label = f"{NUMEROS[num - 1]}. {b.titre}"
        else:
            label = f"{NUMEROS[num]}. {b.titre}"
            num += 1
        n_rows = max(len(b.lignes), LIGNES_VIDES[b.sheet])
        s = slide(label, "")
        tb = s.shapes.add_textbox(Inches(M), Inches(0.76), Inches(W - 2 * M), Inches(0.6))
        tb.text_frame.word_wrap = True
        r = tb.text_frame.paragraphs[0].add_run()
        r.text = b.consigne
        r.font.size, r.font.italic, r.font.color.rgb = Pt(10), True, gris
        for ch in b.choix:
            p = tb.text_frame.add_paragraph()
            r = p.add_run()
            r.text = "Valeurs possibles : " + ch
            r.font.size, r.font.color.rgb = Pt(8.5), gris
        top = 1.0 + 0.2 * (len(b.choix) + 1)
        hrow = min(0.36, (6.95 - top) / (n_rows + 1))
        size = 9 if len(b.entetes) > 8 else 10
        widths = ([1.0] if b.numerote else []) + [_col(b.sheet, k)[2] for k in b.cles]
        t = table(s, top, n_rows + 1, widths, hrow)
        for j, h in enumerate(b.entetes):
            cell(t.cell(0, j), h, size - 0.5, True, blanc, navy)
        for i in range(n_rows):
            vals = b.lignes[i] if i < len(b.lignes) else ([str(i + 1)] + [""] * len(b.cles) if b.numerote else [""] * len(b.cles))
            for j, v in enumerate(vals):
                cell(t.cell(i + 1, j), v, size, fill=RGBColor.from_string("F3F5F8") if i % 2 else None)

    s = slide(f"{NUMEROS[num]}. RÉCIT LIBRE, DÉFIS ET DIFFICULTÉS (facultatif, non importé)",
              "Texte libre pour la lecture humaine. Les informations utiles au mapping vont dans les tableaux.")
    tb = s.shapes.add_textbox(Inches(M), Inches(1.3), Inches(W - 2 * M), Inches(5.6))
    tb.text_frame.word_wrap = True
    tb.text_frame.paragraphs[0].add_run().text = ""
    prs.save(str(path))


# ---------------------------------------------------------------------------
# Lecture (import)
# ---------------------------------------------------------------------------
def _n(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("\n", " ").replace("*", " ")
    return " ".join(re.sub(r"[^a-z0-9?' ]+", " ", s).split())


def _txt_cell(s: str) -> str:
    return (s or "").replace("\x0b", "\n").replace("\xa0", " ").replace("’", "'").strip()


def tables_brutes(path: Path | str) -> List[List[List[str]]]:
    """Tableaux du fichier, cellules non dédoublonnées (les colonnes restent alignées)."""
    path = Path(path)
    out: List[List[List[str]]] = []
    if path.suffix.lower() == ".docx":
        import docx
        for t in docx.Document(str(path)).tables:
            out.append([[_txt_cell(c.text) for c in r.cells] for r in t.rows])
    elif path.suffix.lower() == ".pptx":
        from pptx import Presentation

        def shapes(ss):
            for s in ss:
                if s.shape_type == 6:
                    yield from shapes(s.shapes)
                else:
                    yield s
        for sl in Presentation(str(path)).slides:
            for s in shapes(sl.shapes):
                if getattr(s, "has_table", False) and s.has_table:
                    out.append([[_txt_cell(c.text) for c in r.cells] for r in s.table.rows])
    return out


_CAS = {_n(label): (key, kind) for _sec, fields in CASE_SECTIONS for key, label, _a, _r, kind in fields}
_COLS = {sheet: {_n(lab): key for key, label, *_ in cols for lab in (label,) + ALIAS.get(label, ())}
         for sheet, _t, _c, cols in TABLES}
_KIND = {(sheet, key): kind for sheet, _t, _c, cols in TABLES for key, _l, _w, kind, _a in cols}


def _choix(kind: str, v: str) -> str:
    """Valeur d'une liste écrite à la main → orthographe de la liste (casse et accents ignorés)."""
    if kind in LISTS and v:
        for x in LISTS[kind]:
            if _n(x) == _n(v):
                return x
    return v


def _reconnaitre(header: List[str]) -> Optional[Tuple[str, Dict[int, str], Optional[int]]]:
    """(feuille, {colonne: clé}, colonne N°) si l'en-tête est celui d'un tableau du modèle."""
    hn = [_n(h) for h in header]
    best = None
    for sheet, cols in _COLS.items():
        idx = {j: cols[h] for j, h in enumerate(hn) if h in cols}
        score = len(idx)
        if score >= 2 and score >= 0.6 * len([h for h in hn if h and h not in ("n", "n°", "no")]):
            if not best or score > len(best[1]):
                nj = next((j for j, h in enumerate(hn) if h in ("n", "no", "numero")), None)
                best = (sheet, idx, nj)
    return best


@dataclass
class Lecture:
    case: Case
    champs: int
    tableaux: Dict[str, int]
    erreurs: List[str]


def lire_modele(path: Path | str) -> Optional[Lecture]:
    """Lit un narratif rempli à partir du modèle. None si le fichier n'est pas un modèle Mapping Épi."""
    tables = tables_brutes(path)
    c = Case()
    erreurs: List[str] = []
    n_champs = 0
    vus_cas = 0
    chrono: Dict[str, dict] = {}
    ordre: List[str] = []
    lignes: Dict[str, List[dict]] = {}
    for t in tables:
        if not t:
            continue
        head = [_n(x) for x in t[0]]
        if len(head) >= 2 and head[0] == "champ" and head[1] == "valeur":
            for r in t[1:]:
                if len(r) < 2 or _n(r[0]) not in _CAS:
                    continue
                key, kind = _CAS[_n(r[0])]
                vus_cas += 1
                v = r[1].strip()
                if not v:
                    continue
                try:
                    if key == "note_pied":
                        c.note_pied = v
                    elif key == "symptomes":
                        c.symptomes = [x.strip() for x in re.split(r"[;,•\n]", v) if x.strip()]
                    else:
                        setattr(c, key, _from_cell(Case, key, _choix(kind, v)))
                    n_champs += 1
                except ValueError as exc:
                    erreurs.append(f"{r[0]} : {exc}")
            continue
        rec = _reconnaitre(t[0])
        if not rec:
            continue
        sheet, idx, nj = rec
        for i, r in enumerate(t[1:], 1):
            vals = {key: (r[j].strip() if j < len(r) else "") for j, key in idx.items()}
            if not any(vals.get(k) for k in ESSENTIEL[sheet] + (("description", "personnes", "transport")
                                                                 if sheet == "Chronologie" else ())):
                continue
            if sheet == "Chronologie":
                no = (r[nj].strip() if nj is not None and nj < len(r) else "") or f"#{i}"
                if no not in chrono:
                    chrono[no] = {}
                    ordre.append(no)
                chrono[no].update({k: v for k, v in vals.items() if v})
            else:
                lignes.setdefault(sheet, []).append(vals)
    if vus_cas < 5 and not chrono and not lignes:
        return None
    if chrono:
        lignes["Chronologie"] = [chrono[k] for k in sorted(ordre, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0, ordre.index(x)))]
    from core.storage import SHEETS
    counts: Dict[str, int] = {}
    for sheet, rows in lignes.items():
        model = SHEETS[sheet][0]
        items = []
        for n, vals in enumerate(rows, 1):
            if not any(vals.get(k) for k in ESSENTIEL[sheet]):
                continue
            kw = {}
            for key, v in vals.items():
                try:
                    kw[key] = _from_cell(model, key, _choix(_KIND.get((sheet, key), ""), v) if v else None)
                except ValueError as exc:
                    erreurs.append(f"{sheet} ligne {n} : {exc}")
            kw = {k: v for k, v in kw.items() if v is not None or _field_type(model, k)[1]}
            items.append(model(**kw))
        setattr(c, _attr(sheet), items)
        counts[sheet] = len(items)
    return Lecture(c, n_champs, counts, erreurs)


def manquants(c: Case) -> List[str]:
    out = []
    for _sec, fields in CASE_SECTIONS:
        for key, label, _a, req, _k in fields:
            v = getattr(c, key)
            if req and v in (None, "", "Inconnu", []):
                out.append(label)
    return out
