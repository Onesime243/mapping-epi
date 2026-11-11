"""Import des anciens narratifs d'investigation (Word .docx, PowerPoint .pptx / .ppt).

Les équipes rédigent le narratif d'un cas sous deux formes courantes :
  * le « Rapport d'investigation approfondie » (Word) : tableau d'identification (CODE VHF, AGE, SEXE,
    ZONE DE SANTE…), histoire de la maladie datée, tableau « LIEN DE CONTACT / NOMBRE LISTÉS », actions ;
  * le « Descriptif / narratif du cas confirmé » (PowerPoint) : tableau Âge, Sexe, Statut, Date de début des
    symptômes…, puis des « Observations » datées et les actions de santé publique.

Le texte est découpé en paires « libellé → valeur » (lignes de tableaux) et en lignes de récit. Les champs du
cas sont remplis à partir des libellés ; les lignes qui commencent par une date deviennent des étapes de la
chronologie. Rien n'est inventé : ce qui manque reste vide et apparaît « à compléter » dans l'outil.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from config import theme
from core.models import Action, Case, ContactGroup, Event, IPCSite, LabSample

FORMATS = (".docx", ".pptx", ".ppt")

MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}


def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _cle(s: str) -> str:
    s = _sans_accents(s or "").lower().replace("’", "'")
    return re.sub(r"[^a-z0-9' ]+", " ", s).strip()


def _propre(s: str) -> str:
    s = (s or "").replace("\x0b", "\n").replace("\xa0", " ").replace("’", "'")
    return re.sub(r"[ \t]+", " ", s).strip()


# ---------------------------------------------------------------------------
# Lecture des fichiers
# ---------------------------------------------------------------------------
@dataclass
class Document:
    tables: List[List[List[str]]] = field(default_factory=list)   # tableaux → lignes → cellules
    lignes: List[str] = field(default_factory=list)               # récit, dans l'ordre du document
    titre: str = ""


def _cellules_uniques(cells: Iterable[str]) -> List[str]:
    out: List[str] = []
    for c in cells:
        c = _propre(c)
        if c and (not out or out[-1] != c):     # cellules fusionnées répétées par python-docx
            out.append(c)
    return out


def _lire_docx(path: Path) -> Document:
    import docx
    d = docx.Document(str(path))
    doc = Document()
    for t in d.tables:
        doc.tables.append([_cellules_uniques(c.text for c in r.cells) for r in t.rows])
    for p in d.paragraphs:
        t = _propre(p.text)
        if t:
            doc.lignes.append(t)
            if not doc.titre:
                doc.titre = t
    return doc


def _lire_pptx(path: Path) -> Document:
    from pptx import Presentation
    doc = Document()

    def parcourir(shapes):
        for s in shapes:
            if s.shape_type == 6:                       # groupe
                yield from parcourir(s.shapes)
                continue
            yield s

    for slide in Presentation(str(path)).slides:
        for s in parcourir(slide.shapes):
            if getattr(s, "has_table", False) and s.has_table:
                rows = [_cellules_uniques(c.text for c in r.cells) for r in s.table.rows]
                doc.tables.append(rows)
                # les longues cellules « Observations » contiennent le récit daté
                for r in rows:
                    for c in r[1:]:
                        if len(c) > 80:
                            doc.lignes += [x.strip(" /") for x in c.split("\n") if x.strip(" /")]
            elif s.has_text_frame:
                t = _propre(s.text_frame.text)
                if not t:
                    continue
                if not doc.titre and len(t) > 15:
                    doc.titre = t.replace("\n", " ")
                doc.lignes += [x.strip(" /") for x in t.split("\n") if x.strip(" /")]
    return doc


def _ppt_vers_pptx(path: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ValueError("Format PowerPoint ancien (.ppt) : ouvrez le fichier dans PowerPoint, « Enregistrer sous » "
                         "au format .pptx, puis importez ce nouveau fichier.")
    out = Path(tempfile.mkdtemp(prefix="narratif_"))
    profil = out / "profil"          # profil LibreOffice jetable (le service n'a pas de dossier personnel)
    import os
    env = dict(os.environ, HOME=str(out))
    subprocess.run([soffice, f"-env:UserInstallation={profil.as_uri()}", "--headless", "--convert-to", "pptx",
                    "--outdir", str(out), str(path)], check=False, capture_output=True, timeout=180, env=env)
    res = out / (path.stem + ".pptx")
    if not res.exists():
        raise ValueError("Conversion du .ppt impossible : enregistrez-le au format .pptx puis réimportez-le.")
    return res


def lire(path: Path | str) -> Document:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".docx":
        return _lire_docx(path)
    if ext == ".pptx":
        return _lire_pptx(path)
    if ext == ".ppt":
        return _lire_pptx(_ppt_vers_pptx(path))
    raise ValueError("Format non reconnu : utilisez un narratif Word (.docx) ou PowerPoint (.pptx, .ppt).")


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
_D = r"(\d{1,2})(?:er)?"
_S = r"\s*[/.\-]\s*"
_A = r"(\d{4})"
_AU = r"\s*(?:au|à|a|-|–|—)\s*"
_M = r"(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)"
_MOTIFS = [
    # 11/10/2026 au 24/10/2026
    ("plein-plein", re.compile(_D + _S + r"(\d{1,2})" + _S + _A + _AU + _D + _S + r"(\d{1,2})" + _S + _A)),
    # 31/10 - 01/11/2026
    ("jm-jma", re.compile(_D + _S + r"(\d{1,2})" + _AU + _D + _S + r"(\d{1,2})" + _S + _A)),
    # du 03 au 04/11/2026, 27-29/10/2026
    ("j-jma", re.compile(r"(?<![\d/])" + _D + _AU + _D + _S + r"(\d{1,2})" + _S + _A)),
    # 08 Octobre au 21 Octobre 2026
    ("jm-jm-a", re.compile(_D + r"\s+" + _M + r"(?:\s+" + _A + r")?" + _AU + _D + r"\s+" + _M + r"\s+" + _A, re.I)),
    # 16 au 25 octobre 2026
    ("j-j-m-a", re.compile(_D + _AU + _D + r"\s+" + _M + r"\s+" + _A, re.I)),
    # 26/10/2026
    ("jma", re.compile(_D + _S + r"(\d{1,2})" + _S + _A)),
    # 24 octobre 2026
    ("j-m-a", re.compile(_D + r"\s+" + _M + r"\s+" + _A, re.I)),
]


def _mois(m: str) -> int:
    return MOIS[_sans_accents(m).lower()]


def _date(j, m, a) -> Optional[date]:
    try:
        return date(int(a), int(m) if str(m).isdigit() else _mois(m), int(j))
    except (ValueError, KeyError):
        return None


def _interpreter(nom: str, g: tuple) -> Tuple[Optional[date], Optional[date]]:
    if nom == "plein-plein":
        return _date(g[0], g[1], g[2]), _date(g[3], g[4], g[5])
    if nom == "jm-jma":
        fin = _date(g[2], g[3], g[4])
        return _date(g[0], g[1], g[4]), fin
    if nom == "j-jma":
        return _date(g[0], g[2], g[3]), _date(g[1], g[2], g[3])
    if nom == "jm-jm-a":
        return _date(g[0], g[1], g[2] or g[5]), _date(g[3], g[4], g[5])
    if nom == "j-j-m-a":
        return _date(g[0], g[2], g[3]), _date(g[1], g[2], g[3])
    if nom == "jma":
        return _date(*g), None
    return _date(*g), None   # j-m-a


def trouver_periode(texte: str) -> Tuple[Optional[date], Optional[date], int, int]:
    """Première date (ou période) du texte : (début, fin, position, fin de la correspondance)."""
    meilleur = None
    for nom, rx in _MOTIFS:
        m = rx.search(texte)
        if not m:
            continue
        cle = (m.start(), -(m.end() - m.start()))
        if meilleur is None or cle < meilleur[0]:
            meilleur = (cle, nom, m)
    if not meilleur:
        return None, None, -1, -1
    _, nom, m = meilleur
    d1, d2 = _interpreter(nom, m.groups())
    if d1 and d2 and d2 < d1:
        d1, d2 = d2, d1
    if d2 == d1:
        d2 = None
    return d1, d2, m.start(), m.end()


def premiere_date(texte: str) -> Optional[date]:
    return trouver_periode(texte or "")[0]


# ---------------------------------------------------------------------------
# Paires libellé → valeur
# ---------------------------------------------------------------------------
def _paires(doc: Document) -> List[Tuple[str, List[str]]]:
    out = []
    for t in doc.tables:
        for r in t:
            if len(r) >= 2:
                out.append((_cle(r[0]), r[1:]))
    # libellés « Clé : valeur » dans le récit (ex. « Profession : Orpailleur »)
    return out


def _valeur(paires, *cles, exclure: Tuple[str, ...] = ()) -> Tuple[str, List[str]]:
    for k, v in paires:
        if len(k) <= 60 and any(c in k for c in cles) and not any(x in k for x in exclure):
            return (v[0] if v else ""), v
    return "", []


def _oui(v: str) -> Optional[bool]:
    k = _cle(v)
    if re.search(r"\boui\b|^x\b|:\s*x\b|\bx$", k) or re.search(r"oui\s*:?\s*x", k):
        return True
    if re.search(r"\bnon\b", k):
        return False
    return None


# ---------------------------------------------------------------------------
# Symptômes, lieux, classement des étapes
# ---------------------------------------------------------------------------
_SYMPTOMES = [
    (r"fi[eè]vre|f[ée]bri", "Fièvre"), (r"asth[ée]nie|fatigue", "Fatigue / asthénie"),
    (r"c[ée]phal|maux? de t[eê]te", "Céphalées (maux de tête)"), (r"arthralg|douleurs? articulaire", "Douleurs articulaires"),
    (r"myalg|douleurs? musculaire", "Douleurs musculaires"), (r"courbature", "Courbatures"),
    (r"lombalg|mal (?:au|de) dos|dorsalg", "Mal au dos"), (r"mal de gorge|odynophag", "Mal de gorge"),
    (r"diarrh|selles? liquide", "Diarrhée"), (r"naus[ée]e", "Nausées"), (r"vomiss", "Vomissements"),
    (r"saignement|h[ée]morragi", "Saignements"), (r"hoquet", "Hoquet"),
    (r"yeux rouges|conjonctiv|rougeur oculaire", "Rougeur oculaire"), (r"m[ée]l[ée]na", "Méléna"),
    (r"h[ée]mat[ée]m[èe]se", "Hématémèse"), (r"gingivorragi", "Gingivorragie"), (r"[ée]pistaxis", "Épistaxis"),
    (r"anorexie", "Anorexie"), (r"douleurs? abdominale", "Douleurs abdominales"), (r"\btoux\b", "Toux"),
    (r"[ée]ruption", "Éruption cutanée"),
]
_COURT = {"Fatigue / asthénie": "asthénie", "Céphalées (maux de tête)": "céphalées", "Douleurs articulaires": "arthralgies",
          "Douleurs musculaires": "myalgies", "Douleurs abdominales": "douleurs abdo.", "Rougeur oculaire": "yeux rouges"}


def symptomes(texte: str) -> List[str]:
    t = texte.lower()
    return [nom for rx, nom in _SYMPTOMES if re.search(rx, t)]


_STRUCT = (r"(?:CSDT|CSR|CS|CHU|CH|HGR|HG|PS|CTE|CT|ESS|FOSA|Clinique|clinique|Centre de sant[ée]|Centre hospitalier|"
           r"centre hospitalier|Centre de [Tt]ransit|Poste de sant[ée]|H[oô]pital|h[oô]pital|[Ll]aboratoire(?: provincial)?)")
_NOM = r"\s+(?:(?:de|du|des|la|le)\s+|d'|l')?((?:[A-ZÉÈÀÂ][\w'\-]*)(?:\s+(?:[A-ZÉÈÀÂ][\w'\-]*|mine|Mine))*)"
_RX_STRUCT = re.compile(r"\b(" + _STRUCT + r")" + _NOM)
_RX_LIEU = re.compile(r"\b(?:à|a|dans|vers|sur)\s+(?:la\s+|le\s+|l')?((?:[A-Z][\w'\-]+)(?:[ -][A-Z][\w'\-]+)?)")
_PAS_LIEU = {"La", "Le", "Les", "Il", "Elle", "Ils", "Elles", "Pendant", "Patient", "MVE", "Coartem", "Paracétamol", "Paracetamol",
             "Maladox", "OUI", "NON", "Ebola"}


def lieux(texte: str) -> List[str]:
    out: List[str] = []
    for m in _RX_STRUCT.finditer(texte):
        pre, nom = m.group(1), m.group(2)
        pre = {"clinique": "Clinique", "centre hospitalier": "CH", "Centre hospitalier": "CH",
               "hôpital": "Hôpital", "hopital": "Hôpital", "laboratoire": "Labo", "Laboratoire": "Labo",
               "laboratoire provincial": "Labo provincial", "Laboratoire provincial": "Labo provincial"}.get(pre, pre)
        val = f"{pre} {nom}".strip()
        if nom and nom not in _PAS_LIEU and val not in out:
            out.append(val)
    for m in re.finditer(r"aire de sant[ée]\s+(?:de\s+|du\s+)?([A-Z][\w\-]+)", texte):
        if f"AS {m.group(1).title()}" not in out:
            out.append(f"AS {m.group(1).title()}")
    for m in re.finditer(r"(?:r[ée]sidence|village|quartier|localit[ée]|carri[eè]re(?: mini[eè]re?)?)\s+(?:de\s+|du\s+|à\s+)?([A-Z][\w\-]+)", texte):
        n = m.group(1).title() if m.group(1).isupper() else m.group(1)
        if n not in out and n not in _PAS_LIEU:
            out.append(n)
    if not out:
        if re.search(r"\bdomicile|\bm[ée]nage\b", texte, re.I):
            out.append("Domicile")
        for m in _RX_LIEU.finditer(texte):
            n = m.group(1)
            if n.split()[0] not in _PAS_LIEU and n not in out and not n.isupper() or (n.isupper() and len(n) > 3 and n not in _PAS_LIEU):
                if n not in out:
                    out.append(n.title() if n.isupper() else n)
    return out


def _transport(t: str) -> str:
    t = t.lower()
    if "ambulance" in t:
        return "Ambulance"
    if "moto" in t:
        return "Moto"
    if re.search(r"[àa] pieds?", t):
        return "À pied"
    if re.search(r"v[ée]hicule|voiture|taxi\b", t):
        return "Véhicule"
    if "pirogue" in t or "baleini" in t:
        return "Pirogue"
    return ""


def _personnes(t: str) -> str:
    out = []
    for m in re.finditer(r"(?:accompagn[ée]+e?s?|conduite?s?)\s+(?:de|par)\s+([^.;:()]{3,70})", t, re.I):
        out.append(m.group(1).strip(" ,"))
    if re.search(r"garde[ -]malade", t, re.I):
        out.append("Garde-malade")
    s = ", ".join(dict.fromkeys(out))
    s = re.sub(r",?\s*accompagn\w*\s+(?:de|par)\s+", ", ", s, flags=re.I)
    s = re.sub(r"\b(?:son|sa|ses|un|une)\s+", "", s, flags=re.I)
    return s.strip(" ,")[:60]


_HUMIDE = re.compile(r"diarrh|vomiss|selles? liquide|saign|h[ée]morragi|m[ée]l[ée]na|h[ée]mat[ée]m|hoquet", re.I)


def _classer(t: str, d: Optional[date], j0: Optional[date]) -> Tuple[str, str]:
    """(type d'étape, titre) d'après les mots du récit et la position par rapport au début des symptômes."""
    k = t.lower()
    avant = bool(j0 and d and d < j0)
    consult = re.search(r"consult|alerte|soins|ambulatoire|tradipra|triage", k)
    isol = re.search(r"isol|\bcte\b|centre de traitement|hospitalis|admis", k)
    prelev = re.search(r"[ée]chantillon|pr[ée]l[eè]vement|pr[ée]lev[ée]", k)
    if (avant or not j0) and re.search(r"probable contact|contact avec (?:le|son|sa) cas|exposition|expos[ée]e? |cas contaminant", k):
        return "Exposition", "Exposition probable"
    if (avant or not j0) and re.search(r"garde[ -]malade", k):
        return "Exposition", "Garde-malade auprès d'un malade"
    if (avant or not j0) and re.search(r"fun[ée]railles|deuil|veill[ée]e", k):
        return "Funérailles", "Funérailles (exposition)"
    if not avant and re.search(r"\bd[ée]c[eè]s\b|d[ée]c[ée]d[ée]", k) and not re.search(r"d[ée]c[ée]d[ée]e? confirm", k):
        return "Décès", "Décès"
    if re.search(r"enterr|inhum", k):
        return "Enterrement", "Enterrement"
    if re.search(r"fun[ée]railles", k):
        return "Funérailles", "Funérailles"
    if re.search(r"d[ée]but des (?:signes|sympt)|\bdds\b|d[ée]but de la maladie|apparition des sympt", k):
        return "Début maladie", "Début maladie"
    if consult:
        parts = ["Consultation"] + (["alerte"] if "alerte" in k else []) + (["isolement"] if isol else []) \
            + (["prélèvement"] if prelev else [])
        return ("Hospitalisation" if isol else "Soins / consultation"), " / ".join(parts)
    if isol:
        return "Hospitalisation", "Isolement / prise en charge"
    if prelev and not re.search(r"positif|n[ée]gatif", k):
        return "Prélèvement", "Prélèvement / envoi" if re.search(r"exp[ée]di|envo", k) else "Prélèvement"
    if re.search(r"positif|n[ée]gatif|r[ée]sultat", k):
        return "Laboratoire", "Résultat positif" if "positif" in k else "Résultat de laboratoire"
    if re.search(r"r[ée]f[ée]r[ée]|transf[ée]r", k):
        return "Référence", "Référence"
    if re.search(r"automédi|automedi", k):
        return "Soins / consultation", "Automédication"
    if re.search(r"quitt|se rendre|voyag|à bord|a bord|travers|d[ée]plac", k):
        return "Déplacement", "Déplacement"
    if re.search(r"persistance|aggravation|s'ajout|ajout|apparue?", k):
        return "Autre", "Aggravation des signes"
    return "Autre", ""


def _resume(t: str, syms: List[str]) -> str:
    """Description courte pour la carte : signes rapportés et actes, sinon la phrase raccourcie."""
    k = t.lower()
    actes = []
    for rx, mot in [(r"automédi|automedi", "automédication"), (r"consult", "consultation"), (r"alerte", "alerte"),
                    (r"valid", "validation"), (r"isol", "isolement"), (r"pr[ée]lev", "prélèvement"),
                    (r"exp[ée]di", "envoi labo"), (r"ambulatoire", "soins ambulatoires"), (r"ambulance", "ambulance"),
                    (r"positif", "résultat positif"), (r"sans succ|sans am[ée]lioration", "sans amélioration")]:
        if re.search(rx, k) and mot not in actes:
            actes.append(mot)
    parts = [_COURT.get(s, s.lower()) for s in syms[:4]] + actes[:3]
    if len(parts) >= 2:
        return " • ".join(parts)
    phrase = re.sub(r"\s+", " ", t).strip(" :,;.-")
    if len(phrase) > 78:
        phrase = phrase[:76].rsplit(" ", 1)[0] + "…"
    return phrase[:1].upper() + phrase[1:]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
_PREFIXES = re.compile(r"^(?:[-•*\s]*)(?:en date du|le|les|du|des|depuis le|dds\s*:?\s*(?:serai[t]?|serait)?\s*le|"
                       r"p[ée]riode d'exposition\s*:?\s*du|exposition estim[ée]e\s*:?\s*du)?\s*", re.I)


def _etapes(lignes: List[str], j0: Optional[date]) -> List[Event]:
    events: List[Event] = []
    for brut in lignes:
        for ligne in re.split(r"(?<=[.;])\s+(?=(?:Le|En date du|Du|Depuis le)\s+\d)", brut):
            d1, d2, pos, fin = trouver_periode(ligne)
            if not d1 or pos > 45:
                continue
            reste = ligne[fin:].strip(" :,-–—.;")
            # éviter les titres et lignes d'identification (« Date de confirmation 04/11/2026 », « Rapport du … »)
            tete = _cle(ligne[:pos])
            if re.match(r"^(date|nature|version|p[ée]riode investigation)", tete) or \
                    re.search(r"description|descriptif|rapport|narratif|mapping|confirme du|vivant du", tete) or \
                    (len(reste) < 25 and ligne.upper() == ligne):
                continue
            avant_txt = re.sub(r"\b(?:du|le|en date du|depuis le|des)\s*$", "", ligne[:pos], flags=re.I).strip(" :,-")
            texte = (avant_txt + " " + reste).strip(" :,-")
            typ, titre = _classer(texte, d1, j0)
            if not reste:
                reste = avant_txt
            syms = symptomes(texte)
            lx = lieux(texte)
            ev = Event(date_debut=d1, date_fin=d2, type=typ, titre=titre or typ, description=_resume(reste or texte, syms),
                       transport=_transport(texte), personnes=_personnes(texte),
                       liquides=bool(_HUMIDE.search(texte)))
            if typ == "Déplacement":
                m = re.search(r"quitter\s+(\w[\w'\-]*)\s+pour\s+(\w[\w'\-]*)", texte)
                if m:
                    ev.lieu, ev.lieu_arrivee = m.group(1).title(), m.group(2).title()
                elif lx:
                    ev.lieu_arrivee = lx[-1]
                    ev.lieu = lx[0] if len(lx) > 1 else ""
            elif lx:
                ev.lieu = lx[0] if typ not in ("Hospitalisation", "Laboratoire") else lx[-1]
            if re.search(r"heure|\d{1,2}h\d{0,2}", texte):
                m = re.search(r"\b(\d{1,2}h\d{0,2})\b", texte)
                if m:
                    ev.heure = m.group(1)
            if re.search(r"estim|probable|serai", ligne, re.I):
                ev.date_incertaine = typ in ("Exposition", "Début maladie") and bool(re.search(r"estim|serai", ligne, re.I))
            events.append(ev)
            # une même phrase peut contenir la consultation ET le résultat positif : étape laboratoire en plus
            if typ != "Laboratoire" and re.search(r"positif", texte, re.I) and re.search(r"r[ée]sultat|labo|mve", texte, re.I):
                lx2 = [x for x in lx if re.match(r"(CTE|CT|Labo)", x)]
                events.append(Event(date_debut=d1, type="Laboratoire", titre="Résultat positif",
                                    description="Confirmation au laboratoire", lieu=lx2[-1] if lx2 else "",
                                    personnes="Équipe laboratoire"))
    return events


def _categorie(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" :")
    return s[:1].upper() + s[1:].lower() if s.isupper() else s[:1].upper() + s[1:]


def _contacts(doc: Document) -> List[ContactGroup]:
    groupes: List[ContactGroup] = []
    # tableau « LIEN DE CONTACT | NOMBRE LISTÉS »
    for t in doc.tables:
        if t and t[0] and "lien de contact" in _cle(t[0][0]):
            for r in t[1:]:
                if len(r) < 2 or _cle(r[0]).startswith("total"):
                    continue
                n = re.search(r"\d+", r[1])
                nb = int(n.group()) if n else None
                if nb == 0:
                    continue
                groupes.append(ContactGroup(categorie=_categorie(r[0]), nombre=nb, risque="Haut",
                                            libelle_nombre="listés" if nb else ""))
    if groupes:
        return groupes
    # « Listage des contacts: 43 / Famille: 4 / Ménage transitoire: 19 … »
    dans = False
    for l in doc.lignes:
        k = _cle(l)
        if "listage des contacts" in k:
            dans = True
            continue
        if dans:
            m = re.match(r"^([^:]{2,45}?)\s*:\s*(\d+)\s*$", l.strip())
            if m:
                groupes.append(ContactGroup(categorie=_categorie(m.group(1)), nombre=int(m.group(2)),
                                            risque="Haut", libelle_nombre="listés"))
                continue
            if groupes:
                break
    if not groupes:
        for l in doc.lignes:
            m = re.search(r"listage des contacts\s*:?\s*(\d+)\s*list", l, re.I)
            if m:
                groupes.append(ContactGroup(categorie="Contacts listés", nombre=int(m.group(1)), risque="Haut",
                                            libelle_nombre="listés"))
                break
    return groupes


_STATUT_ACTION = [(r"en cours|continu", "En cours"), (r"\boui\b|r[ée]alis|fait|effectu", "Fait"), (r"\bnon\b", "À faire")]


def _actions_et_pci(doc: Document) -> Tuple[List[Action], List[IPCSite]]:
    actions: List[Action] = []
    pci: List[IPCSite] = []
    vus = set()

    def ajouter(texte: str, statut: str, prio: str = "Important"):
        texte = re.sub(r"\s+", " ", texte).strip(" :;,.-/")
        texte = re.split(r"\s*\(", texte)[0]
        if len(texte) < 4 or _cle(texte) in vus:
            return
        if len(texte) > 70:
            texte = texte[:68].rsplit(" ", 1)[0] + "…"
        vus.add(_cle(texte))
        actions.append(Action(texte=texte[:1].upper() + texte[1:], statut=statut, priorite=prio))

    zone = ""
    for l in doc.lignes:
        k = _cle(l)
        majuscules = sum(ch.isupper() for ch in l) > 0.6 * max(1, sum(ch.isalpha() for ch in l))
        if re.search(r"actions? prevues|recommandation|perspectives", k):
            zone = "prevues"
            continue
        if re.search(r"autres actions|actions? de sante publique", k) and len(l) < 70:
            zone = "liste"
            continue
        if re.search(r"listage contacts|actions? de sante publique menees", k):
            zone = "cle"
            continue
        if re.search(r"defis|difficultes|equipe d'investigation|description du cas|descriptif|narratif", k):
            zone = ""
        # décontamination → PCI
        m = re.search(r"d[ée]contamination\s+(?:de\s+l'|des?\s+|du\s+|de\s+la\s+)?(.+?)\s*:\s*(.+)$", l, re.I)
        if m:
            statut = "Partiel" if re.search(r"cours|partiel", m.group(2), re.I) else (
                "Décontaminé" if re.search(r"oui|fait|r[ée]alis", m.group(2), re.I) else "Non")
            for site in re.split(r"\s+et\s+|,", m.group(1)):
                site = re.sub(r"^(?:l'|le |la |les )", "", site.strip())
                if site and len(site) < 40:
                    pci.append(IPCSite(site=site[:1].upper() + site[1:], statut=statut))
        m = re.match(r"^(.{3,90}?)\s*:\s*(.+)$", l)
        if m and re.match(r"(actions? de sp|actions? de sante)", _cle(m.group(1))):
            for part in re.split(r",|;", m.group(2)):
                ajouter(part, "Fait")
            zone = "liste"
            continue
        if not zone or majuscules or re.match(r"^(entretien|recherche active|revue documentaire|observations|autre\s*:|nombre de)", k):
            continue
        if zone in ("cle", "liste") and m:
            if re.match(r"(famille|menage|ppl|co |co-|amis|chauffeur|voisins|garde|motard)", _cle(m.group(1))) and re.search(r"\d", m.group(2)):
                continue
            statut = next((s for rx, s in _STATUT_ACTION if re.search(rx, m.group(2), re.I)), "Fait")
            if "listage" in _cle(m.group(1)):
                statut = "En cours" if re.search(r"cours|continu", m.group(2), re.I) else "Fait"
            ajouter(m.group(1), statut)
        elif zone == "liste" and not m and len(l) < 140:
            for part in l.split(";"):
                ajouter(part, "Fait")
        elif zone == "prevues":
            texte = m.group(2) if m else l
            dom = m.group(1) if m else ""
            if len(texte) > 6:
                ajouter((dom + " : " if dom and len(dom) < 14 else "") + texte, "À faire", "Urgent")
    return actions, pci


def _labo(events: List[Event], doc: Document) -> List[LabSample]:
    lab = LabSample(type="Sang total")
    trouve = False
    texte_total = " ".join(doc.lignes)
    m = re.search(r"laboratoire\s+(provincial\s+)?(?:de\s+|du\s+)?([A-Z][\w\-]+)", texte_total)
    if m:
        lab.laboratoire = ("Laboratoire provincial " if m.group(1) else "Laboratoire ") + m.group(2)
    elif re.search(r"\bINRB\b", texte_total):
        lab.laboratoire = "INRB"
    for e in events:
        k = (e.titre + " " + e.description).lower()
        if e.type != "Prélèvement" and "prélèvement" in k and e.date_debut:
            trouve = True
            lab.prelevement = lab.prelevement or datetime.combine(e.date_debut, datetime.min.time())
        if e.type == "Prélèvement" and e.date_debut:
            trouve = True
            if "envoi" in k or "expédi" in k:
                lab.envoi = lab.envoi or datetime.combine(e.date_debut, datetime.min.time())
            else:
                lab.prelevement = lab.prelevement or datetime.combine(e.date_debut, datetime.min.time())
        if e.type == "Laboratoire" and e.date_debut:
            trouve = True
            lab.resultat, lab.resultat_le = "Positif", datetime.combine(e.date_debut, datetime.min.time())
    return [lab] if trouve or lab.laboratoire else []


def _localiser(case: Case) -> None:
    """Province, ZS et AS écrites comme dans la pyramide sanitaire (si elles y figurent)."""
    path = Path(__file__).resolve().parents[1] / "config" / "rdc_pyramide.csv"
    if not path.exists():
        return
    zs_k, as_k = _cle(case.zs).replace(" ", ""), _cle(case.aire_sante).replace(" ", "")
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split(";")
        if len(parts) < 3:
            continue
        prov, zs, as_ = parts
        if zs_k and _cle(zs).replace(" ", "") == zs_k:
            case.province = case.province or prov
            case.zs = zs
            if as_k and as_ and _cle(as_).replace(" ", "") == as_k:
                case.aire_sante = as_


def _titre_case(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip(" :./-")
    return s.title() if s.isupper() else s


@dataclass
class Resultat:
    case: Case
    trouves: List[str]
    manquants: List[str]


def extraire(doc: Document) -> Resultat:
    p = _paires(doc)
    c = Case()
    trouves: List[str] = []
    tout = " ".join(doc.lignes + [" ".join(r) for t in doc.tables for r in t])
    if re.search(r"marburg", tout, re.I):
        c.maladie = "Marburg"

    code, _ = _valeur(p, "code vhf", "id vhf", "n epid", "numero epid")
    if code:
        c.code_cas = code.strip()[:40]
    age_txt, _ = _valeur(p, "age")
    m = re.search(r"(\d{1,3})\s*(ans|an|mois)", age_txt, re.I)
    if m:
        c.age = int(m.group(1))
        c.age_unite = "mois" if m.group(2).lower() == "mois" else "ans"
    sexe, _ = _valeur(p, "sexe")
    sk = _cle(sexe)
    if sk.startswith("f"):
        c.sexe = "F"
    elif sk.startswith("m"):
        c.sexe = "M"
    prof, _ = _valeur(p, "profession")
    m = re.search(r"profession\s*:\s*([^()/\n]+?)(?:\(|$)", sexe + " " + prof, re.I)
    c.profession = _titre_case(m.group(1) if m else prof)[:40]
    c.aire_sante = _titre_case(_valeur(p, "aire de sante")[0])
    c.zs = _titre_case(re.sub(r"^zs\s+(de\s+)?", "", _valeur(p, "zone de sante")[0], flags=re.I))
    vill, _ = _valeur(p, "cellule", "quartier", "adresse", "village")
    c.village = _titre_case(re.split(r"\.|réf|ref:", vill, flags=re.I)[0])[:40]
    if not c.zs:
        m = re.search(r"zone de sant[ée] (?:de |du )?([A-Z][\w\-]+)|\bZS (?:de |du )?([A-Z][\w\-]+)", " ".join(doc.lignes[:6]))
        if m:
            c.zs = _titre_case(m.group(1) or m.group(2))
    if not c.aire_sante:
        m = re.search(r"aire de sant[ée] (?:de |du )?([A-Z][\w\-]+)", " ".join(doc.lignes[:6]), re.I)
        if m:
            c.aire_sante = _titre_case(m.group(1))
    _localiser(c)

    statut, _ = _valeur(p, "statut")
    if re.search(r"probable", statut, re.I):
        c.statut = "Probable"
    elif re.search(r"suspect", statut, re.I):
        c.statut = "Suspect"

    dds, _ = _valeur(p, "debut des symptomes", "date de debut", "dds")
    c.debut_symptomes = premiere_date(dds)
    conf, _ = _valeur(p, "date de confirmation", "confirmation")
    c.date_confirmation = premiere_date(conf)
    if not c.date_confirmation:
        m = re.search(r"confirm[ée]?\s+(?:le|du)\s+(\d{1,2}\s*[/.]\s*\d{1,2}\s*[/.]\s*\d{4})", doc.titre + " " + tout, re.I)
        if m:
            c.date_confirmation = premiere_date(m.group(1))

    nat, nat_all = _valeur(p, "nature du cas", "etat actuel", "issue")
    nk = _cle(" ".join(nat_all))
    if re.search(r"vivant\s*:?\s*(oui|x)|^vivant|confirme vivant\s*:?\s*oui", nk) or nk.strip().startswith("vivant"):
        c.issue = "Vivant"
    elif re.search(r"dec[eé]d", nk):
        c.issue = "Décès"
    dd, _ = _valeur(p, "date de deces")
    c.date_deces = premiere_date(dd)
    if c.date_deces:
        c.issue = "Décès"

    # lien épidémiologique
    cc, cc_all = _valeur(p, "cas contact connu", "contact connu")
    suivi, _ = _valeur(p, "contact suivi")
    oui = _oui(cc)
    if oui is True:
        c.contact_connu = "Contact connu suivi" if _oui(suivi) else "Contact connu"
    elif oui is False:
        c.contact_connu = "Non contact"
    src_txt = " ".join(cc_all[1:]) + " " + " ".join(v for k, vv in p if "cas source" in k or "source" in k for v in vv)
    for k_, vv in p:
        if k_.startswith("si oui") and vv and re.search(r"contact|cas contaminant", vv[0], re.I):
            src_txt += " " + vv[0]
    src_txt += " " + " ".join(l for l in doc.lignes if re.search(r"cas contaminant|cas source", l, re.I))
    m = re.search(r"\b(RDC[\s\-_]*[A-Z]{2,4}[\s\-_]*[A-Z]{2,4}[\s\-_]*\d{2,4}(?:[\s\-_]*\d{2,4})?)", src_txt)
    if m:
        c.id_cas_source = re.sub(r"[\s_]+", "-", m.group(1).strip())
    else:
        m = re.search(r"(?i:cas contaminant|cas source|contact de|contact list[ée] autour de)\s*:?\s*"
                      r"((?:[A-ZÉÈ][A-ZÉÈ'\-]{2,}\s*){1,3})", src_txt)
        if m and "NON" not in m.group(1).upper().split():
            c.id_cas_source = m.group(1).strip()[:40]
    if c.contact_connu == "Inconnu" and c.id_cas_source:
        c.contact_connu = "Contact connu"

    per, _ = _valeur(p, "periode investigation", "date investigation")
    c.date_investigation = premiere_date(per)
    if not c.date_investigation:
        m = re.search(r"version en date du\s*(.+)$", " ".join(doc.lignes[:4]), re.I)
        if m:
            c.date_investigation = premiere_date(m.group(1))
    eq, _ = _valeur(p, "equipe d'investigation", "investigateur")
    if not eq:
        for t in doc.tables:
            for r in t:
                if r and "equipe d'investigation" in _cle(r[0]):
                    eq = r[0]
    if eq:
        noms = re.findall(r"(?:Dr\.?\s+|Docteur\s+)?([A-Z][\w]+(?:\s+[A-Z][A-Z\w]+){0,2})\s*[:,]\s*(?:[ÉE]pid|M[ée]decin|Point focal|Infirm)",
                          eq.replace("\n", " "))
        if noms:
            c.investigateur = ", ".join(dict.fromkeys(n.strip() for n in noms))[:80]

    # récit : étapes, symptômes
    events = _etapes(doc.lignes, None)
    if not c.debut_symptomes:
        d = next((e.date_debut for e in events if e.type == "Début maladie"), None)
        c.debut_symptomes = d
    events = _etapes(doc.lignes, c.debut_symptomes)
    events.sort(key=lambda e: (e.date_debut or date.max))
    c.events = events
    narr = " ".join(e.description + " " + e.titre for e in events) + " " + " ".join(doc.lignes)
    c.symptomes = [s for s in symptomes(narr) if s in theme.SYMPTOMS]

    c.contacts = _contacts(doc)
    c.actions, c.ipc = _actions_et_pci(doc)
    c.labs = _labo(events, doc)

    # lieu d'exposition indiqué à part (« Lieu de contact : … à Bangole »)
    lc = " ".join(l for l in doc.lignes if re.search(r"lieu de contact|enterr[ée]", l, re.I))
    for e in c.events:
        if e.type in ("Exposition", "Funérailles") and not e.lieu and lieux(lc):
            e.lieu = lieux(lc)[0]
    from core import rules
    c.places = rules.places_from_events(c)
    if not c.date_confirmation:
        c.date_confirmation = next((e.date_debut for e in c.events if e.type == "Laboratoire" and "positif" in e.titre.lower()), None)
    for pl in c.places:
        n = pl.nom
        if re.match(r"(HGR|HG|CH|CHU|H[oô]pital|CTE|CT)\b", n):
            pl.type = "Hôpital"
        elif re.match(r"(CSR|CSDT|CS|PS|Clinique|ESS|FOSA|Centre de sant|Poste)", n):
            pl.type = "Centre de santé"
        elif n.startswith("Labo"):
            pl.type = "Laboratoire"
        elif n == "Domicile":
            pl.type = "Ménage"

    for lab, ok in [("ID du cas", c.code_cas), ("Âge", c.age is not None), ("Sexe", c.sexe != "Inconnu"),
                    ("Zone de santé", c.zs), ("Aire de santé", c.aire_sante), ("Début des symptômes", c.debut_symptomes),
                    ("Confirmation", c.date_confirmation), ("Issue", c.issue != "Inconnu"),
                    ("Contact connu / non contact", c.contact_connu != "Inconnu")]:
        if ok:
            trouves.append(lab)
    manquants = [lab for lab in ["ID du cas", "Âge", "Sexe", "Zone de santé", "Aire de santé", "Début des symptômes",
                                 "Confirmation", "État", "Contact connu / non contact"] if lab not in trouves]
    if c.contact_connu in theme.CONTACT_AVEC_SOURCE and not c.id_cas_source:
        manquants.append("ID du cas source")
    trouves += [f"{len(c.events)} étape(s) de chronologie", f"{len(c.contacts)} catégorie(s) de contacts",
                f"{len(c.places)} lieu(x)", f"{len(c.actions)} action(s)", f"{len(c.symptomes)} symptôme(s)"]
    return Resultat(c, trouves, manquants)


def importer(path: Path | str) -> Resultat:
    """Lit un narratif Word / PowerPoint et renvoie le cas pré-rempli (à vérifier dans l'outil).

    Un narratif rempli à partir du modèle Word / PowerPoint (core/modele_narratif.py) est lu tableau par tableau,
    comme le classeur Excel ; un ancien narratif libre est analysé à partir du récit."""
    from core import modele_narratif as M
    if Path(path).suffix.lower() in (".docx", ".pptx"):
        lu = M.lire_modele(path)
        if lu is not None:
            noms = {"Chronologie": "étape(s) de chronologie", "Lieux": "lieu(x)", "Contacts": "catégorie(s) de contacts",
                    "PCI": "site(s) PCI", "Laboratoire": "prélèvement(s)", "Actions": "action(s)"}
            trouves = [f"modèle Mapping Épi reconnu, {lu.champs} champ(s) de la fiche"] + \
                      [f"{lu.tableaux[k]} {noms[k]}" for k in noms if k in lu.tableaux]
            return Resultat(lu.case, trouves, M.manquants(lu.case) + lu.erreurs)
    res = extraire(lire(path))
    res.case.note_pied = ""
    return res
