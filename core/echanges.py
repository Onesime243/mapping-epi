"""Échanges de données : liste des cas (Excel), rapport de situation (Word), paquet de fiches (synchronisation).

Le paquet de fiches permet de rassembler les fiches saisies sur des ordinateurs sans connexion
(application installée) et sur le serveur : un fichier .zip à transmettre par clé USB, e-mail ou WhatsApp.
Seules les FICHES DE CAS voyagent : jamais les comptes, mots de passe ni réglages.

Règles d'import (aucune donnée n'est perdue) :
- fiche inconnue (nouvel identifiant) : ajoutée, sauf si son N° EPID existe déjà sous une autre fiche
  (conflit signalé, rien n'est écrasé) ;
- fiche connue au contenu identique : rien à faire ;
- fiche connue modifiée : la plus récente l'emporte ; l'ancienne version reste dans l'historique ;
- fiche que le compte n'a pas le droit de modifier : ignorée et signalée.
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from core import indicateurs as IND
from core import riposte as R
from core import rules
from core.models import Case

FORMAT = "mapping-epi-paquet"
MAX_FICHES = 20000
MAX_OCTETS = 300 * 1024 * 1024


def _d(v: Optional[date]) -> str:
    return v.strftime("%d/%m/%Y") if v else ""


# ---------------------------------------------------------------------------
# paquet de fiches
# ---------------------------------------------------------------------------
def paquet_bytes(cases: List[Case], auteur: str = "", origine: str = "") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifeste.json", json.dumps({
            "format": FORMAT, "version": 1, "cree_le": datetime.now().isoformat(timespec="seconds"),
            "auteur": auteur, "origine": origine, "fiches": len(cases),
            "note": "Fiches de cas Mapping Épi (aucun compte ni mot de passe). Importer avec le menu Données."},
            ensure_ascii=False, indent=2))
        for c in cases:
            z.writestr(f"cas/{c.id}.json", c.model_dump_json(indent=1))
    return buf.getvalue()


def lire_paquet(data: bytes) -> Tuple[List[Case], List[str]]:
    """(fiches valides, erreurs). Refuse un fichier qui n'est pas un paquet Mapping Épi."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("Ce fichier n'est pas un paquet de fiches (.zip) Mapping Épi.")
    with z:
        noms = z.namelist()
        if "manifeste.json" not in noms:
            raise ValueError("Paquet non reconnu : manifeste.json absent.")
        man = json.loads(z.read("manifeste.json").decode("utf-8"))
        if man.get("format") != FORMAT:
            raise ValueError("Paquet non reconnu (format inattendu).")
        fichiers = [i for i in z.infolist() if i.filename.startswith("cas/") and i.filename.endswith(".json")]
        if len(fichiers) > MAX_FICHES or sum(i.file_size for i in fichiers) > MAX_OCTETS:
            raise ValueError("Paquet trop volumineux.")
        out, err = [], []
        for i in fichiers:
            try:
                out.append(Case.model_validate_json(z.read(i)))
            except Exception as exc:
                err.append(f"{i.filename} : illisible ({str(exc)[:80]})")
    return out, err


@dataclass
class Bilan:
    ajoutees: List[str] = field(default_factory=list)
    mises_a_jour: List[str] = field(default_factory=list)
    identiques: int = 0
    plus_anciennes: List[str] = field(default_factory=list)
    conflits: List[str] = field(default_factory=list)
    refusees: List[str] = field(default_factory=list)
    erreurs: List[str] = field(default_factory=list)

    def texte(self) -> str:
        parts = [f"{len(self.ajoutees)} fiche(s) ajoutée(s)", f"{len(self.mises_a_jour)} mise(s) à jour",
                 f"{self.identiques} déjà à jour"]
        if self.plus_anciennes:
            parts.append(f"{len(self.plus_anciennes)} plus ancienne(s) que la version présente (ignorée(s))")
        if self.conflits:
            parts.append(f"{len(self.conflits)} conflit(s) de N° EPID non importé(s) : " + ", ".join(self.conflits[:8]))
        if self.refusees:
            parts.append(f"{len(self.refusees)} hors de vos droits (ignorée(s))")
        if self.erreurs:
            parts.append(f"{len(self.erreurs)} fichier(s) illisible(s)")
        return " ; ".join(parts) + "."


def _contenu(c: Case) -> str:
    return c.model_dump_json(exclude={"modifie_le", "modifie_par"})


def importer_paquet(store, data: bytes, auteur: str, owner: str = "",
                    peut_modifier: Optional[Callable[[Case, str], bool]] = None) -> Bilan:
    from core.links import _id
    cases, err = lire_paquet(data)
    b = Bilan(erreurs=err)
    rows = store.rows_full(None)
    par_id = {cid: (own or "", c) for cid, _u, own, c in rows}
    par_code = {}
    for cid, _u, _own, c in rows:
        if c.code_cas.strip():
            par_code.setdefault(_id(c.code_cas), cid)
    for c in cases:
        if c.exemple():             # exemple fictif : jamais mélangé aux vrais cas
            continue
        code = c.code_cas or c.id[:8]
        if c.id in par_id:
            own, old = par_id[c.id]
            if _contenu(old) == _contenu(c):
                b.identiques += 1
                continue
            if peut_modifier and not peut_modifier(old, own):
                b.refusees.append(code)
                continue
            if (c.modifie_le or datetime.min) <= (old.modifie_le or datetime.min):
                b.plus_anciennes.append(code)
                continue
            store.archive_version(old, auteur, "Avant import d'un paquet de fiches")
            store.save(c, version=True, auteur=auteur, garder_date=True,
                       commentaire=f"Import paquet (modifiée par {c.modifie_par or '?'} le "
                                   f"{c.modifie_le:%d/%m/%Y %H:%M})" if c.modifie_le else "Import paquet")
            b.mises_a_jour.append(code)
            continue
        k = _id(c.code_cas) if c.code_cas.strip() else ""
        if k and k in par_code:
            b.conflits.append(code)
            continue
        store.save(c, version=True, auteur=auteur, garder_date=True, commentaire=f"Import paquet (saisie par {c.modifie_par or '?'})",
                   owner=owner)
        par_id[c.id] = (owner, c)
        if k:
            par_code[k] = c.id
        b.ajoutees.append(code)
    return b


# ---------------------------------------------------------------------------
# liste des cas (Excel)
# ---------------------------------------------------------------------------
COLONNES = [
    ("N° EPID", 24), ("Province", 13), ("Zone de santé", 15), ("Aire de santé", 15), ("Sexe", 7), ("Âge", 7),
    ("Profession", 16), ("Agent de santé (PPL)", 11), ("Vacciné", 9), ("Date de vaccination", 12),
    ("Contact connu", 18), ("ID du cas source", 22), ("Dernier contact avec la source", 13),
    ("Début des symptômes (rapporté)", 13), ("Phase des premiers signes", 14), ("J0 retenu", 12),
    ("Notification", 12), ("Confirmation", 12), ("Isolement (1re hospitalisation)", 13),
    ("Début → isolement (j)", 10), ("État", 12), ("Date de décès", 12), ("Décès communautaire", 11),
    ("Enterrement sécurisé", 11), ("Contacts listés", 9), ("Contacts suivis", 9), ("Risque global", 13),
    ("Complétude (%)", 10), ("Actions ouvertes", 9), ("Modifiée le", 15), ("Modifiée par", 14),
]


def _ligne(c: Case) -> list:
    iso = R.date_isolement(c)
    dc, es = R.deces_communautaire(c), R.enterrement_securise(c)
    yn = {True: "Oui", False: "Non", None: ""}
    lst = [g.nombre for g in c.contacts if g.nombre is not None]
    sv = [g.suivis for g in c.contacts if g.suivis is not None]
    try:
        j0 = rules.j0_retenu(c)
    except Exception:
        j0 = None
    try:
        risque = c.risque_global or rules.global_risk(c)[0]
    except Exception:
        risque = c.risque_global
    return [c.code_cas, c.province, c.zs, c.aire_sante, c.sexe, f"{c.age} {c.age_unite}" if c.age is not None else "",
            c.profession, c.agent_sante, c.vaccine, c.date_vaccination, c.contact_connu, c.id_cas_source,
            c.date_contact_source, c.debut_symptomes, c.phase_dds, j0, c.date_notification, c.date_confirmation, iso,
            (iso - c.debut_symptomes).days if iso and c.debut_symptomes else None, c.issue, c.date_deces, yn[dc],
            yn[es], sum(lst) if lst else None, sum(sv) if sv else None, risque, rules.completeness(c)[0],
            sum(1 for a in c.actions if a.texte.strip() and a.statut != "Fait"),
            c.modifie_le.strftime("%d/%m/%Y %H:%M") if c.modifie_le else "", c.modifie_par]


def liste_cas_xlsx(cases: List[Case], path: Path | str, perimetre: str = "") -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = "Liste des cas"
    ws.append([f"Liste des cas Mapping Épi : {perimetre}".strip(" :") +
               f" · {len(cases)} cas · extraite le {datetime.now():%d/%m/%Y %H:%M}"])
    ws["A1"].font = Font(bold=True, size=12, color="1F3A5F")
    ws.append([n for n, _w in COLONNES])
    for i, (_n, w) in enumerate(COLONNES, 1):
        cell = ws.cell(row=2, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[2].height = 44
    tri = sorted(cases, key=lambda c: (IND.date_notification(c)[0] or date.min, c.code_cas))
    for c in tri:
        ws.append(_ligne(c))
        for cell in ws[ws.max_row]:
            if isinstance(cell.value, date):
                cell.number_format = "DD/MM/YYYY"
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(COLONNES))}{max(2, ws.max_row)}"
    wb.save(str(path))


# ---------------------------------------------------------------------------
# rapport de situation (Word)
# ---------------------------------------------------------------------------
def rapport_docx(cases_perimetre: List[Case], path: Path | str, perimetre: str = "", periode: Optional[int] = 21,
                 ref: Optional[date] = None, province: str = "") -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    ref = ref or date.today()
    tous = R.filtrer(cases_perimetre, None, ref, province)
    recents = R.filtrer(cases_perimetre, periode, ref, province) if periode else tous
    NAVY = RGBColor(0x1F, 0x3A, 0x5F)

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.6)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10)
    for name, size in (("Heading 1", 13), ("Heading 2", 11)):
        s = doc.styles[name]
        s.font.name, s.font.size, s.font.color.rgb, s.font.bold = "Calibri", Pt(size), NAVY, True
        rf = s.element.rPr.find(qn("w:rFonts"))
        if rf is not None:
            for k in list(rf.attrib):
                if "Theme" in k or "theme" in k:
                    del rf.attrib[k]

    def shade(cell, fill):
        tcPr = cell._tc.get_or_add_tcPr()
        e = OxmlElement("w:shd")
        e.set(qn("w:val"), "clear"); e.set(qn("w:color"), "auto"); e.set(qn("w:fill"), fill)
        tcPr.append(e)

    def table(headers, rows, widths=None, fills=None):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            c.text = ""
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
            r = c.paragraphs[0].add_run(str(h)); r.bold = True; r.font.size = Pt(9); r.font.color.rgb = RGBColor(255, 255, 255)
            shade(c, "1F3A5F")
        for k, row in enumerate(rows):
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
                r = cells[i].paragraphs[0].add_run("" if v is None else str(v)); r.font.size = Pt(9)
                if fills and fills[k] and fills[k][i]:
                    shade(cells[i], fills[k][i])
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        doc.add_paragraph()
        return t

    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("RAPPORT DE SITUATION : MALADIE À VIRUS EBOLA"); r.bold = True; r.font.size = Pt(16); r.font.color.rgb = NAVY
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    lib = f"{periode} derniers jours" if periode else "depuis le début"
    p.add_run(f"Périmètre : {perimetre or 'tous les cas'}{' · province ' + province if province else ''} · "
              f"situation au {ref:%d/%m/%Y} · indicateurs : {lib}").italic = True
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Généré automatiquement par Mapping Épi à partir des fiches de cas. À valider avant diffusion.")
    r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(0x6B, 0x77, 0x85)

    # 1. situation générale
    doc.add_heading("1. Situation générale", level=1)
    zs_all = {(c.province, c.zs) for c in tous if c.zs}
    dc = [c for c in tous if c.issue == "Décès"]
    lignes = [
        ["Cas confirmés", len(tous), len(recents)],
        ["Décès", len(dc), sum(1 for c in recents if c.issue == "Décès")],
        ["Létalité (décès / cas)", f"{100 * len(dc) / len(tous):.0f} %" if tous else "?", ""],
        ["Zones de santé touchées", len(zs_all), len({(c.province, c.zs) for c in recents if c.zs})],
        ["Agents de santé (PPL) parmi les cas", sum(1 for c in tous if c.agent_sante == "Oui"),
         sum(1 for c in recents if c.agent_sante == "Oui")],
    ]
    if periode:
        table(["", "Depuis le début", lib.capitalize()], lignes, [7.5, 4.5, 4.5])
    else:
        table(["", "Depuis le début"], [x[:2] for x in lignes], [7.5, 4.5])

    # 2. courbe épidémique (tableau semaines × ZS)
    doc.add_heading("2. Courbe épidémique (cas par semaine de début de la maladie)", level=1)
    cb = R.courbe(tous)
    if cb.semaines:
        sem = cb.semaines[-12:]
        off = len(cb.semaines) - len(sem)
        rows, fills = [], []
        mx = max([v for s in cb.series.values() for v in s] or [1]) or 1
        for z, vals in cb.series.items():
            v = vals[off:]
            rows.append([z] + [x or "" for x in v] + [sum(vals)])
            fills.append([None] + [_heat(x, mx) for x in v] + [None])
        tot = [sum(s[i] for s in cb.series.values()) for i in range(len(cb.semaines))][off:]
        rows.append(["Total"] + tot + [sum(sum(s) for s in cb.series.values())])
        fills.append(None)
        rows.append(["dont décès"] + [x or "" for x in cb.deces[off:]] + [sum(cb.deces)])
        fills.append(None)
        table(["ZS"] + [f"{w:%d/%m}" for w in sem] + ["Total"], rows)
        note = f"Semaines commençant le lundi indiqué ; {len(sem)} dernières semaines affichées."
        if cb.par_notification:
            note += f" {cb.par_notification} cas sans date de début placé(s) à la date de notification."
        if cb.sans_date:
            note += f" {cb.sans_date} cas sans aucune date non représenté(s)."
        doc.add_paragraph(note).runs[0].font.size = Pt(8.5)
    else:
        doc.add_paragraph("Aucun cas daté.")

    # 3. catégories des ZS
    doc.add_heading("3. Catégories des zones de santé", level=1)
    zones = IND.zones(tous, ref)
    table(["Cat.", "Province", "Zone de santé", "Cas", "7 derniers j", "21 derniers j", "Dernier cas", "Jours sans cas"],
          [[z.cat.get("num") or "?", z.province, z.zs, z.n, z.n7, z.n21, _d(z.dernier),
            z.jours if z.jours is not None else "?"] for z in zones],
          [1.2, 2.6, 3.2, 1.4, 1.8, 1.9, 2.2, 2.0],
          [[_cat_fill(z.cat)] + [None] * 7 for z in zones])

    # 4. indicateurs clés
    doc.add_heading(f"4. Indicateurs clés de la riposte ({lib})", level=1)
    ind = R.indicateurs(recents)
    fill = {"ok": "DCEFDF", "attention": "FBEBD5", "alerte": "F6D9D6", "info": None}
    table(["Domaine", "Indicateur", "Résultat", "Cible", "Non renseigné"],
          [[i.groupe, i.nom, i.texte(), i.cible, i.inconnus or ""] for i in ind],
          [2.8, 7.0, 3.4, 1.8, 2.4],
          [[None, None, fill[i.statut], None, None] for i in ind])
    doc.add_paragraph("Cibles indicatives, à valider par la coordination. Les informations non renseignées sont "
                      "exclues du pourcentage et comptées à part.").runs[0].font.size = Pt(8.5)

    # 5. alertes
    doc.add_heading("5. Alertes : nouveau foyer possible (21 derniers jours)", level=1)
    al = [a for a in IND.alertes_foyers(tous) if 0 <= (ref - a.quand).days <= 21]
    if al:
        table(["Notifié le", "Cas", "Lieu", "Lecture"], [[_d(a.quand), a.case.code_cas, f"{a.niveau} {a.lieu}", a.texte]
                                                         for a in al], [2.3, 4.2, 3.5, 7.4])
    else:
        doc.add_paragraph("Aucune alerte sur la période.")

    # 6. actions
    doc.add_heading("6. Actions ouvertes sur les fiches de cas", level=1)
    acts = R.actions_ouvertes(tous, ref)
    bil = R.bilan_actions(acts)
    doc.add_paragraph(f"{bil['ouvertes']} action(s) ouverte(s), dont {bil['retard']} en retard et {bil['urgentes']} "
                      f"urgente(s) ; {bil['sans_responsable']} sans responsable.")
    if acts:
        table(["Cas", "ZS", "Action", "Priorité", "Responsable", "Échéance", "Retard"],
              [[a.case.code_cas, a.case.zs, a.action.texte, a.action.priorite, a.action.responsable,
                _d(a.action.echeance), f"{a.retard} j" if a.retard else ""] for a in acts[:40]],
              [3.2, 2.0, 5.6, 1.7, 2.4, 1.9, 1.3])

    # 7. points d'attention
    doc.add_heading("7. Points d'attention", level=1)
    for t in R.points_attention(ind, zones, al, acts):
        doc.add_paragraph(t, style="List Bullet")
    doc.save(str(path))


def _heat(v: int, mx: int) -> Optional[str]:
    if not v:
        return None
    k = v / mx
    return "DCE6F0" if k < 0.34 else "A9C1D9" if k < 0.67 else "7A9CC0"


def _cat_fill(cat: dict) -> Optional[str]:
    return {1: "F6D9D6", 2: "FBEBD5", 3: "F6EFD2", 4: "DCEFDF"}.get(cat.get("num"))
