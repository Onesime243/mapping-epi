"""Menu PCI : lieux fréquentés par chaque cas et adresse de chaque lieu (fichier Excel).

Une ligne par cas et par lieu. Les lieux viennent du parcours (lieu de chaque étape, départ et arrivée d'un
déplacement), des lieux saisis et des sites PCI. Un même lieu cité plusieurs fois dans une fiche n'a qu'une ligne.
L'adresse est celle du site PCI de même nom ; une donnée manquante est écrite « ? », jamais laissée vide.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.langue import actuelle, tr, trf
from core.models import Case

COLONNES = [("ID du cas", 22), ("Province", 14), ("Zone de santé", 16), ("Aire de santé", 16),
            ("Lieu fréquenté", 34), ("Origine", 22), ("Première date", 13), ("Étape(s) du parcours", 34),
            ("Adresse", 38), ("Statut PCI / décontamination", 18), ("Date PCI", 12), ("Équipe PCI", 18)]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _site_pci(nom: str, c: Case):
    """Site PCI qui correspond à ce lieu (même nom, ou l'un contient l'autre)."""
    k = _norm(nom)
    if not k:
        return None
    for s in c.ipc:
        ks = _norm(s.site)
        if ks and (k == ks or k in ks or ks in k):
            return s
    return None


def lignes(cases: List[Case]) -> List[dict]:
    out: List[dict] = []
    for c in sorted(cases, key=lambda c: (c.province or "", c.zs or "", c.code_cas or "")):
        lieux: Dict[str, dict] = {}

        def ajoute(nom: str, origine: str, quand: Optional[date] = None, etape: str = ""):
            nom = (nom or "").strip()
            k = _norm(nom)
            if not k or k in ("?", "inconnu"):
                return
            d = lieux.setdefault(k, {"lieu": nom, "origines": [], "date": None, "etapes": []})
            if origine not in d["origines"]:
                d["origines"].append(origine)
            if quand and (d["date"] is None or quand < d["date"]):
                d["date"] = quand
            if etape and etape not in d["etapes"]:
                d["etapes"].append(etape)

        for ev in c.sorted_events():
            etape = (f"{ev.date_debut:%d/%m} · " if ev.date_debut else "") + (ev.titre or tr(ev.type or ""))
            ajoute(ev.lieu, "Parcours", ev.date_debut, etape)
            ajoute(ev.lieu_arrivee, "Parcours", ev.date_debut, etape)
        for p in c.places:
            ajoute(p.nom, "Lieu saisi")
        for s in c.ipc:
            ajoute(s.site, "Site PCI", s.date)
        for d in lieux.values():
            s = _site_pci(d["lieu"], c)
            out.append({
                "id": c.code_cas or "?", "province": c.province or "?", "zs": c.zs or "?",
                "as": c.aire_sante or "?", "lieu": d["lieu"], "origine": " + ".join(d["origines"]),
                "date": d["date"], "etapes": ("; " if actuelle() == "en" else " ; ").join(d["etapes"]) or "?",
                "adresse": (s.adresse.strip() if s and s.adresse.strip() else "?"),
                "statut": (s.statut if s and s.statut else "?") if s else "Pas de site PCI saisi",
                "date_pci": s.date if s and s.date else None,
                "equipe": (s.equipe.strip() if s and s.equipe.strip() else "?") if s else "?",
            })
    return out


def bilan(rows: List[dict]) -> dict:
    return {"cas": len({r["id"] for r in rows}), "lieux": len(rows),
            "avec_adresse": sum(1 for r in rows if r["adresse"] != "?"),
            "sans_site": sum(1 for r in rows if r["statut"] == "Pas de site PCI saisi")}


def xlsx(cases: List[Case], path: Path | str, perimetre: str = "") -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    rows = lignes(cases)
    b = bilan(rows)
    wb = Workbook()
    ws = wb.active
    ws.title = tr("Lieux et adresses")
    ws.append([tr("PCI : lieux fréquentés et adresses") + (f" · {perimetre}" if perimetre.strip() else "") +
               trf(" · {cas} cas · {lieux} lieux ({adr} avec adresse) · extrait le {quand}", cas=b['cas'], lieux=b['lieux'],
                   adr=b['avec_adresse'], quand=f"{datetime.now():%d/%m/%Y %H:%M}")])
    ws["A1"].font = Font(bold=True, size=12, color="1F3A5F")
    ws.append([tr(n) for n, _w in COLONNES])
    for i, (_n, w) in enumerate(COLONNES, 1):
        cell = ws.cell(row=2, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[2].height = 32
    manque = PatternFill("solid", fgColor="FFF1DC")
    for r in rows:
        ws.append([r["id"], r["province"], r["zs"], r["as"], r["lieu"], tr(r["origine"]), r["date"] or "?",
                   r["etapes"], r["adresse"], tr(r["statut"]), r["date_pci"] or "?", r["equipe"]])
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if isinstance(cell.value, date):
                cell.number_format = "dd/mm/yyyy"
        if r["adresse"] == "?":
            ws.cell(row=ws.max_row, column=9).fill = manque
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(COLONNES))}{max(2, ws.max_row)}"
    # résumé par cas
    rs = wb.create_sheet(tr("Résumé par cas"))
    rs.append([tr(h) for h in ("ID du cas", "Province", "Zone de santé", "Lieux fréquentés", "Avec adresse", "Sans adresse")])
    for cell in rs[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
    par: Dict[str, list] = {}
    for r in rows:
        par.setdefault(r["id"], [r["province"], r["zs"], 0, 0])
        par[r["id"]][2] += 1
        par[r["id"]][3] += r["adresse"] != "?"
    for cid, (p, z, n, a) in par.items():
        rs.append([cid, p, z, n, a, n - a])
    for col, w in zip("ABCDEF", (22, 14, 16, 16, 14, 14)):
        rs.column_dimensions[col].width = w
    wb.save(str(path))
    return len(rows)
