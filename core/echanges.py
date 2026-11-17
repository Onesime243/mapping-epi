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
                cell.number_format = "dd/mm/yyyy"          # minuscules : seul format reconnu par tous les Excel
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(COLONNES))}{max(2, ws.max_row)}"
    _feuille_modelisation(wb, tri)
    wb.save(str(path))


# ---------------------------------------------------------------------------
# feuille « Modélisation » : une ligne par cas, variables pour l'analyse et la modélisation
# ---------------------------------------------------------------------------
VARIABLES_MODELISATION = [
    ("id_cas", "N° EPID du cas"), ("province", "Province"), ("zone_sante", "Zone de santé"), ("aire_sante", "Aire de santé"),
    ("sexe", "Sexe"), ("age_ans", "Âge en années (mois convertis)"), ("profession", "Profession"),
    ("agent_sante", "Agent de santé / prestataire (PPL)"), ("vaccine", "Vacciné (Oui / Non / Inconnu)"),
    ("date_vaccination", "Date de vaccination"), ("contact_connu", "Statut de contact (connu, connu suivi, non contact)"),
    ("id_cas_source", "ID du cas source"), ("date_dernier_contact_source", "Dernier contact avec le cas source"),
    ("exposition_debut", "Début de la fenêtre d'exposition"), ("exposition_fin", "Fin de la fenêtre d'exposition"),
    ("exposition_source", "Origine de la fenêtre (estimée, dernier contact, cas source)"),
    ("j0_rapporte", "Début des symptômes rapporté par l'équipe"), ("phase_premiers_signes", "Phase des premiers signes rapportés"),
    ("recul_j0_jours", "Jours retirés pour obtenir le J0 retenu"), ("j0_retenu", "J0 retenu (début réel estimé)"),
    ("phase_seche_debut", "Début de la phase sèche (= J0 retenu)"),
    ("phase_seche_symptomes", "Symptômes de la phase sèche rapportés"),
    ("phase_humide_debut", "Début de la phase humide"), ("phase_humide_origine", "Origine de la date (saisie, rapportée, estimée)"),
    ("phase_humide_symptomes", "Symptômes de la phase humide rapportés"),
    ("phase_critique_debut", "Début de la phase critique"), ("phase_critique_origine", "Origine de la date"),
    ("phase_critique_symptomes", "Signes de la phase critique (hémorragiques) rapportés"),
    ("autres_symptomes", "Autres symptômes"),
    ("duree_phase_seche_j", "Durée de la phase sèche (jours)"), ("duree_phase_humide_j", "Durée de la phase humide (jours)"),
    ("duree_phase_critique_j", "Durée de la phase critique jusqu'au décès (jours)"),
    ("date_notification", "Date de notification"), ("date_confirmation", "Date de confirmation"),
    ("delai_j0_notification_j", "J0 rapporté → notification (jours)"), ("delai_j0_confirmation_j", "J0 rapporté → confirmation (jours)"),
    ("delai_notification_confirmation_j", "Notification → confirmation (jours)"),
    ("date_isolement", "Isolement (1re hospitalisation)"), ("delai_j0_isolement_j", "J0 rapporté → isolement (jours)"),
    ("date_prelevement", "Premier prélèvement"), ("date_resultat", "Premier résultat"),
    ("delai_prelevement_resultat_h", "Prélèvement → résultat (heures)"), ("resultat_labo", "Résultat du laboratoire"),
    ("debut_anneau_vaccinal", "Début de la vaccination en anneau"), ("delai_confirmation_anneau_j", "Confirmation → anneau (jours)"),
    ("issue", "État du cas"), ("date_deces", "Date de décès"), ("delai_j0_deces_j", "J0 retenu → décès (jours)"),
    ("deces_communautaire", "Décès hors structure de soins"), ("enterrement_securise", "Enterrement digne et sécurisé"),
    ("date_enterrement", "Date de l'enterrement"),
    ("contacts_listes", "Contacts listés (catégories dénombrées)"), ("contacts_haut_risque", "Contacts à haut ou très haut risque"),
    ("contacts_suivis", "Contacts suivis"), ("contacts_vaccines", "Contacts vaccinés"),
    ("categories_contacts_inconnues", "Catégories de contacts non dénombrées"),
    ("nb_etapes", "Nombre d'étapes de la chronologie"), ("nb_lieux", "Nombre de lieux d'exposition"),
    ("nb_deplacements", "Nombre de déplacements"), ("transports", "Moyens de transport utilisés"),
    ("nb_contact_corps", "Étapes avec contact avec le corps"), ("nb_liquides", "Étapes avec liquides biologiques"),
    ("nb_sans_pci", "Étapes de soins sans PCI"), ("nb_funerailles", "Funérailles ou enterrements"),
    ("nb_sites_pci", "Sites PCI renseignés"), ("nb_sites_decontamines", "Sites décontaminés"),
    ("nb_sites_pci_non_inconnu", "Sites PCI « Non » ou inconnu"), ("sequencage", "Résultat du séquençage"),
    ("risque_global", "Risque global"), ("completude_pct", "Complétude de la fiche (%)"),
]


def _jours(a, b):
    return (b - a).days if a and b else None


def _ligne_modelisation(c: Case) -> list:
    from config import theme
    try:
        ph = rules.phases(c)
    except Exception:
        ph = None
    sy = list(c.symptomes)
    secs = [x for x in sy if x in theme.SYMPTOMES_SECS]
    crit = [x for x in sy if x in theme.HEMORRHAGIC]
    hum = [x for x in sy if x in theme.SYMPTOMES_HUMIDES and x not in crit]
    autres = [x for x in sy if x not in secs and x not in hum and x not in crit] + ([c.symptomes_autres] if c.symptomes_autres else [])
    j0 = ph.j0 if ph else None
    hu = ph.humide if ph else None
    cr = ph.critique if ph else None
    iso = R.date_isolement(c)
    labs = sorted([l for l in c.labs if l.prelevement], key=lambda l: l.prelevement)
    l0 = labs[0] if labs else None
    ent = [e.date_debut for e in c.events if e.type == "Enterrement" and e.date_debut]
    hr = [g for g in c.contacts if g.risque in ("Haut", "Très haut") and g.nombre is not None]
    yn = {True: "Oui", False: "Non", None: ""}
    age = None
    if c.age is not None:
        age = round(c.age / 12, 2) if (c.age_unite or "").startswith("mois") else c.age
    try:
        risque = c.risque_global or rules.global_risk(c)[0]
    except Exception:
        risque = c.risque_global
    dc = ph.deces if ph else c.date_deces
    return [
        c.code_cas, c.province, c.zs, c.aire_sante, c.sexe, age, c.profession, c.agent_sante, c.vaccine, c.date_vaccination,
        c.contact_connu, c.id_cas_source, c.date_contact_source,
        ph.exposition[0] if ph and ph.exposition else None, ph.exposition[1] if ph and ph.exposition else None,
        ph.exposition_source if ph else "",
        c.debut_symptomes, c.phase_dds, ph.recul if ph else None, j0,
        j0, "; ".join(secs), hu, ph.humide_source if ph and hu else "", "; ".join(hum),
        cr, ph.critique_source if ph and cr else "", "; ".join(crit), "; ".join(autres),
        _jours(j0, hu), _jours(hu, cr) if cr else _jours(hu, dc), _jours(cr, dc),
        c.date_notification, c.date_confirmation, _jours(c.debut_symptomes, c.date_notification),
        _jours(c.debut_symptomes, c.date_confirmation), _jours(c.date_notification, c.date_confirmation),
        iso, _jours(c.debut_symptomes, iso),
        l0.prelevement.date() if l0 else None, l0.resultat_le.date() if l0 and l0.resultat_le else None,
        round((l0.resultat_le - l0.prelevement).total_seconds() / 3600, 1) if l0 and l0.resultat_le else None,
        l0.resultat if l0 else "",
        c.date_debut_anneau, _jours(c.date_confirmation, c.date_debut_anneau),
        c.issue, c.date_deces, _jours(j0, c.date_deces), yn[R.deces_communautaire(c)], yn[R.enterrement_securise(c)],
        min(ent) if ent else None,
        sum(g.nombre for g in c.contacts if g.nombre is not None) if any(g.nombre is not None for g in c.contacts) else None,
        sum(g.nombre for g in hr) if hr else None,
        sum(g.suivis for g in c.contacts if g.suivis is not None) if any(g.suivis is not None for g in c.contacts) else None,
        sum(g.vaccines for g in c.contacts if g.vaccines is not None) if any(g.vaccines is not None for g in c.contacts) else None,
        sum(1 for g in c.contacts if g.nombre is None),
        len(c.events), len(c.places), sum(1 for e in c.events if e.lieu_arrivee.strip()),
        "; ".join(sorted({e.transport for e in c.events if e.transport})),
        sum(1 for e in c.events if e.contact_corps), sum(1 for e in c.events if e.liquides), sum(1 for e in c.events if e.sans_pci),
        sum(1 for e in c.events if e.type in ("Funérailles", "Enterrement")),
        len(c.ipc), sum(1 for x in c.ipc if x.statut == "Décontaminé"), sum(1 for x in c.ipc if x.statut in ("Non", "Inconnu")),
        c.sequencage, risque, rules.completeness(c)[0],
    ]


def _feuille_modelisation(wb, cases: List[Case]) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    ws = wb.create_sheet("Modélisation")
    ws.append([n for n, _d in VARIABLES_MODELISATION])
    for i in range(1, len(VARIABLES_MODELISATION) + 1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = 16
    for c in cases:
        ws.append(_ligne_modelisation(c))
        for cell in ws[ws.max_row]:
            if isinstance(cell.value, date):
                cell.number_format = "dd/mm/yyyy"
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(VARIABLES_MODELISATION))}{max(1, ws.max_row)}"
    dico = wb.create_sheet("Variables")
    dico.append(["Variable", "Description"])
    for cell in dico[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
    for n, d in VARIABLES_MODELISATION:
        dico.append([n, d])
    dico.append([])
    dico.append(["Règle", "Une case vide = information non renseignée (jamais 0). Dates au format jj/mm/aaaa. "
                          "Les phases sèche, humide et critique viennent de la fiche (dates saisies ou rapportées), sinon "
                          "de l'estimation de l'outil (colonne « origine »). Exemples fictifs exclus."])
    dico.column_dimensions["A"].width = 32
    dico.column_dimensions["B"].width = 90


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
