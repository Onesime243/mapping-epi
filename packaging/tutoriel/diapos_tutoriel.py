"""Diapositives du tutoriel (mêmes images que la vidéo, zones en rouge) + texte de la voix off à lire mot à mot.

Usage : .venv/bin/python packaging/tutoriel/diapos_tutoriel.py "<dossier de sortie>"
Écrit : Tutoriel_Mapping_Epi_diapositives.pptx (texte à lire dans les notes de chaque diapositive)
        Tutoriel_Mapping_Epi_texte_voix_off.docx (le même texte, numéroté par diapositive, avec une durée indicative)
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_tutoriel as V  # noqa: E402


def scenes_sans_voix():
    s = (V.TUTO / "index.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r"const DATA = (\{.*?\});\n", s, re.S).group(1))
    out = [("Introduction", V.image_titre("Remplir une fiche Mapping Épi, étape par étape",
                                         "Tutoriel vidéo · cas fictif d'exercice · aucune donnée réelle"), V.INTRO)]
    for ch in ("web", "fiche", "narr"):
        t, txt = V.CHAPITRES[ch]
        out.append((t, V.image_titre(t, ""), txt))
        etapes = data[ch]
        for k, e in enumerate(etapes, 1):
            cle = Path(e["img"]).stem
            img = V.image_etape(V.TUTO / e["img"], e.get("box"), e["title"], e.get("value") or "", t.split(" : ")[-1],
                                f"étape {k} / {len(etapes)}")
            out.append((f"{t.split(' : ')[-1].capitalize()} · étape {k} : {e['title']}", img,
                        V.NARRATION.get(cle, e["title"] + ". " + e["text"])))
    out.append(("Conclusion", V.image_titre("Merci", "Mapping Épi · Système de Gestion de l'Incident MVE 17\n"
                                                     "SGI-RDC avec l'appui de UMIE-INRB"), V.OUTRO))
    return out


def duree(texte: str) -> int:
    """Durée de lecture indicative (environ 2,6 mots par seconde, à voix posée)."""
    return max(4, round(len(texte.split()) / 2.6))


def pptx(scenes, dossier_img: Path, sortie: Path):
    from pptx import Presentation
    from pptx.util import Emu
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)          # 16:9
    vide = prs.slide_layouts[6]
    for i, (titre, _img, texte) in enumerate(scenes, 1):
        sl = prs.slides.add_slide(vide)
        pic = sl.shapes.add_picture(str(dossier_img / f"diapo_{i:02d}.jpg"), 0, 0, prs.slide_width, prs.slide_height)
        pic.name = f"Diapositive {i} : {titre}"
        sl.notes_slide.notes_text_frame.text = f"[Diapositive {i} · environ {duree(texte)} s]\n{texte}"
    prs.core_properties.title = "Tutoriel Mapping Épi : remplir une fiche étape par étape"
    prs.save(str(sortie))


def docx(scenes, dossier_img: Path, sortie: Path):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    d = Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2)
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(12)
    d.add_heading("Tutoriel Mapping Épi : texte de la voix off", 0)
    total = sum(duree(t) for _a, _b, t in scenes)
    p = d.add_paragraph(f"{len(scenes)} diapositives · durée de lecture totale indicative : environ {total // 60} min "
                        f"{total % 60:02d} s. Lisez le texte de chaque diapositive mot à mot, puis passez à la suivante. "
                        "Le même texte se trouve dans les notes du PowerPoint (mode Présentateur).")
    p.runs[0].italic = True
    for i, (titre, _img, texte) in enumerate(scenes, 1):
        h = d.add_heading(f"Diapositive {i} · {titre}", 2)
        for r in h.runs:
            r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
        d.add_picture(str(dossier_img / f"mini_{i:02d}.jpg"), width=Cm(8))
        t = d.add_paragraph(texte)
        t.runs[0].font.size = Pt(13)
        m = d.add_paragraph(f"Durée indicative : {duree(texte)} secondes")
        m.runs[0].italic = True
        m.runs[0].font.size = Pt(9.5)
        m.runs[0].font.color.rgb = RGBColor(0x5F, 0x6B, 0x7A)
    d.save(str(sortie))


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])
    out = Path(sys.argv[1])
    sc = scenes_sans_voix()
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        for i, (_t, img, _x) in enumerate(sc, 1):
            img.save(str(dd / f"diapo_{i:02d}.jpg"), "JPG", 90)
            img.scaledToWidth(640, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.TransformationMode.SmoothTransformation).save(
                str(dd / f"mini_{i:02d}.jpg"), "JPG", 80)
        pptx(sc, dd, out / "Tutoriel_Mapping_Epi_diapositives.pptx")
        docx(sc, dd, out / "Tutoriel_Mapping_Epi_texte_voix_off.docx")
    print(len(sc), "diapositives")
