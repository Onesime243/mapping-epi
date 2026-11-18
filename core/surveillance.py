"""Menu Surveillance : contacts de chaque cas, lieu par lieu.

Une ligne par cas. Pour chaque lieu (lieu des groupes de contacts de la fiche) :
- « à lister / total » : contacts encore à lister (total moins contacts suivis) sur le nombre de contacts du lieu,
  par exemple 2/8 ;
- fin du suivi : date du dernier contact du lieu + 21 jours (un contact est suivi 21 jours).
Rien n'est inventé : un nombre ou une date manquants sont écrits « ? ».
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from core.models import Case

DUREE_SUIVI = 21
SANS_LIEU = "Lieu non précisé"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


class Nombre(int):
    """Somme des valeurs connues ; `partiel` si une partie manque (affichée « 12+? »)."""
    partiel = False


def _somme(vals: List[Optional[int]]) -> Optional[int]:
    """Somme des valeurs connues (« 12+? » si une partie manque) ; None si aucune n'est connue (jamais 0 inventé)."""
    connus = [v for v in vals if v is not None]
    if not connus:
        return None
    n = Nombre(sum(connus))
    n.partiel = len(connus) < len(vals) or any(getattr(v, "partiel", False) for v in connus)
    return n


def texte(v: Optional[int]) -> str:
    if v is None:
        return "?"
    return f"{int(v)}+?" if getattr(v, "partiel", False) else str(int(v))


def lieux_du_cas(c: Case) -> List[dict]:
    par: Dict[str, dict] = {}
    for g in c.contacts:
        nom = (g.lieu or "").strip() or SANS_LIEU
        d = par.setdefault(_norm(nom) or "-", {"lieu": nom, "totaux": [], "a_lister": [], "derniers": [], "manque_date": False})
        d["totaux"].append(g.nombre)
        if g.nombre is not None and g.suivis is not None:
            d["a_lister"].append(max(0, g.nombre - g.suivis))
        else:
            d["a_lister"].append(None)
        if g.dernier_contact:
            d["derniers"].append(g.dernier_contact)
        else:
            d["manque_date"] = True
    out = []
    for d in par.values():
        dernier = max(d["derniers"]) if d["derniers"] else None
        out.append({"lieu": d["lieu"], "total": _somme(d["totaux"]), "a_lister": _somme(d["a_lister"]),
                    "dernier_contact": dernier,
                    "fin_suivi": dernier + timedelta(days=DUREE_SUIVI) if dernier else None,
                    "date_incomplete": d["manque_date"] and bool(dernier)})
    return out


def lignes(cases: List[Case], ref: Optional[date] = None) -> List[dict]:
    ref = ref or date.today()
    out = []
    for c in sorted(cases, key=lambda c: (c.province or "", c.zs or "", c.code_cas or "")):
        lx = lieux_du_cas(c)
        fins = [x["fin_suivi"] for x in lx if x["fin_suivi"]]
        fin = max(fins) if fins else None
        out.append({"id": c.code_cas, "cid": c.id, "province": c.province or "?", "zs": c.zs or "?",
                    "lieux": lx, "total": _somme([x["total"] for x in lx]) if lx else None,
                    "a_lister": _somme([x["a_lister"] for x in lx]) if lx else None,
                    "fin_suivi": fin, "en_cours": bool(fin and fin >= ref),
                    "jours_restants": (fin - ref).days if fin and fin >= ref else None})
    return out


def bilan(rows: List[dict]) -> dict:
    tot = _somme([r["total"] for r in rows])
    al = _somme([r["a_lister"] for r in rows])
    return {"cas": len(rows), "contacts": texte(tot), "a_lister": texte(al), "a_lister_n": int(al or 0),
            "sans_contacts": sum(1 for r in rows if not r["lieux"]),
            "en_cours": sum(1 for r in rows if r["en_cours"])}


def fraction(a_lister: Optional[int], total: Optional[int]) -> str:
    return f"{texte(a_lister)}/{texte(total)}"


def _xl(v):
    """Nombre pour Excel : entier si complet, sinon texte (« 12+? », « ? »)."""
    return int(v) if v is not None and not getattr(v, "partiel", False) else texte(v)


def xlsx(cases: List[Case], path: Path | str, perimetre: str = "", ref: Optional[date] = None) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from core.langue import tr, trf
    rows = lignes(cases, ref)
    b = bilan(rows)
    n_lieux = max([len(r["lieux"]) for r in rows] + [1])
    wb = Workbook()
    ws = wb.active
    ws.title = tr("Contacts par lieu")[:31]
    ws.append([trf("Surveillance des contacts · {p} · {n} cas · {c} contacts, {a} à lister · extrait le {d}",
                   p=perimetre, n=b["cas"], c=b["contacts"], a=b["a_lister"], d=f"{datetime.now():%d/%m/%Y %H:%M}")])
    ws["A1"].font = Font(bold=True, size=12, color="1F3A5F")
    tete = [tr("ID du cas"), tr("Province"), tr("Zone de santé")]
    for i in range(1, n_lieux + 1):
        tete += [trf("Lieu {i}", i=i), trf("Lieu {i} : à lister / contacts", i=i), trf("Lieu {i} : fin du suivi", i=i)]
    tete += [tr("Contacts listés"), tr("Contacts à lister"), tr("Fin du suivi (tous lieux)")]
    ws.append(tete)
    for i, _t in enumerate(tete, 1):
        cell = ws.cell(row=2, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = 22 if i <= 3 else 16
    ws.row_dimensions[2].height = 44
    for r in rows:
        ligne = [r["id"], r["province"], r["zs"]]
        for i in range(n_lieux):
            if i < len(r["lieux"]):
                x = r["lieux"][i]
                ligne += [tr(x["lieu"]) if x["lieu"] == SANS_LIEU else x["lieu"], fraction(x["a_lister"], x["total"]),
                          x["fin_suivi"] or "?"]
            else:
                ligne += ["", "", ""]
        ligne += [_xl(r["total"]), _xl(r["a_lister"]), r["fin_suivi"] or "?"]
        ws.append(ligne)
        for cell in ws[ws.max_row]:
            if isinstance(cell.value, date):
                cell.number_format = "dd/mm/yyyy"
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(tete))}{max(2, ws.max_row)}"
    # une ligne par lieu, pour les tris et tableaux croisés
    ls = wb.create_sheet(tr("Un lieu par ligne")[:31])
    ls.append([tr("ID du cas"), tr("Province"), tr("Zone de santé"), tr("Lieu"), tr("Contacts"), tr("À lister"),
               tr("Dernier contact"), tr("Fin du suivi")])
    for cell in ls[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
    for r in rows:
        for x in r["lieux"]:
            ls.append([r["id"], r["province"], r["zs"], tr(x["lieu"]) if x["lieu"] == SANS_LIEU else x["lieu"],
                       _xl(x["total"]), _xl(x["a_lister"]),
                       x["dernier_contact"] or "?", x["fin_suivi"] or "?"])
            for cell in ls[ls.max_row]:
                if isinstance(cell.value, date):
                    cell.number_format = "dd/mm/yyyy"
    for col, w in zip("ABCDEFGH", (26, 14, 16, 30, 11, 11, 15, 15)):
        ls.column_dimensions[col].width = w
    wb.save(str(path))
    return len(rows)
