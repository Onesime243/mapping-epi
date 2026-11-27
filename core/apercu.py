"""Aperçu d'un fichier avant téléchargement (Excel, Word, PowerPoint) : contenu affiché dans la page, sans rien
installer. Excel : une feuille par onglet (premières lignes) ; Word : titres, paragraphes, tableaux et images dans
l'ordre ; PowerPoint : une carte par diapositive (titre, textes, images)."""
from __future__ import annotations

import base64
from datetime import date, datetime
from pathlib import Path
from typing import List

MAX_LIGNES = 300
MAX_IMAGE = 4 * 1024 * 1024


def _txt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return f"{v:%d/%m/%Y %H:%M}" if (v.hour or v.minute) else f"{v:%d/%m/%Y}"
    if isinstance(v, date):
        return f"{v:%d/%m/%Y}"
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    return str(v)


def _img(blob: bytes, ctype: str) -> str:
    if not blob or len(blob) > MAX_IMAGE:
        return ""
    return f"data:{ctype or 'image/png'};base64," + base64.b64encode(blob).decode()


def xlsx(path: Path) -> dict:
    from openpyxl import load_workbook
    wb = load_workbook(str(path), read_only=True, data_only=True)
    feuilles = []
    for ws in wb.worksheets:
        lignes: List[List[str]] = []
        total = 0
        for r in ws.iter_rows(values_only=True):
            if not any(v not in (None, "") for v in r):
                continue
            total += 1
            if len(lignes) < MAX_LIGNES:
                lignes.append([_txt(v) for v in r])
        if lignes:
            n = max(len(l) for l in lignes)
            while n > 1 and all((len(l) < n or l[n - 1] == "") for l in lignes):
                n -= 1                                          # colonnes vides à droite
            lignes = [(l + [""] * n)[:n] for l in lignes]
        titre = ""
        if len(lignes) > 1 and sum(1 for v in lignes[0] if v) == 1 and sum(1 for v in lignes[1] if v) > 1:
            titre, lignes, total = next(v for v in lignes[0] if v), lignes[1:], total - 1     # ligne de titre fusionnée
        feuilles.append({"nom": ws.title, "titre": titre, "lignes": lignes, "total": total,
                         "n": max(total - 1, 0)})                              # lignes de données (sans l'en-tête)
    wb.close()
    return {"type": "xlsx", "feuilles": feuilles}


def docx(path: Path) -> dict:
    from docx import Document
    from docx.oxml.ns import qn
    d = Document(str(path))
    blocs = []
    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            p = Paragraph(el, d)
            for blip in el.iter(qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                part = d.part.related_parts.get(rid) if rid else None
                if part is not None:
                    src = _img(part.blob, part.content_type)
                    if src:
                        blocs.append({"t": "img", "src": src})
            texte = p.text.strip()
            if not texte:
                continue
            style = (p.style.name or "").lower() if p.style is not None else ""
            if style.startswith("title") or style.startswith("titre"):
                blocs.append({"t": "h", "n": 1, "txt": texte})
            elif style.startswith("heading") or style.startswith("titre"):
                try:
                    niv = int("".join(ch for ch in style if ch.isdigit()) or 2)
                except ValueError:
                    niv = 2
                blocs.append({"t": "h", "n": min(niv + 1, 4), "txt": texte})
            else:
                blocs.append({"t": "p", "txt": texte, "liste": "list" in style or "liste" in style})
        elif el.tag == qn("w:tbl"):
            from docx.table import Table
            t = Table(el, d)
            lignes = []
            for row in t.rows[:MAX_LIGNES]:
                cells, prec = [], None
                for c in row.cells:
                    if c._tc is prec:                       # cellules fusionnées : une seule fois
                        continue
                    prec = c._tc
                    cells.append(c.text.strip())
                lignes.append(cells)
            if lignes:
                blocs.append({"t": "table", "lignes": lignes})
    return {"type": "docx", "blocs": blocs}


def pptx(path: Path) -> dict:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = Presentation(str(path))
    diapos = []

    def parcourir(shapes, d):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                parcourir(sh.shapes, d)
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    src = _img(sh.image.blob, sh.image.content_type)
                except Exception:
                    src = ""
                if src:
                    d["images"].append(src)
            elif getattr(sh, "has_table", False) and sh.has_table:
                d["tables"].append([[c.text.strip() for c in r.cells] for r in sh.table.rows])
            elif getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                t = sh.text_frame.text.strip()
                if t:
                    d["textes"].append(t)
    for i, s in enumerate(prs.slides, 1):
        d = {"n": i, "titre": "", "textes": [], "images": [], "tables": []}
        if s.shapes.title is not None and s.shapes.title.has_text_frame:
            d["titre"] = s.shapes.title.text_frame.text.strip()
        parcourir(s.shapes, d)
        if d["titre"] and d["textes"] and d["textes"][0] == d["titre"]:
            d["textes"] = d["textes"][1:]
        diapos.append(d)
    return {"type": "pptx", "diapos": diapos}


def lire(path: Path) -> dict:
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return xlsx(path)
    if ext == ".docx":
        return docx(path)
    if ext == ".pptx":
        return pptx(path)
    raise ValueError(ext)
