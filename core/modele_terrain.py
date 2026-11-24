"""Lecture du modèle Word des investigateurs de terrain : « Rapport d'investigation d'un décès / cas confirmé MVE ».

Sections reconnues : I. Identification (CODE VHF, âge, sexe, profession, village, AS, ZS, dates, nature du cas,
enterrement digne et sécurisé, cas contact connu, vaccination, période d'investigation), III. A. Facteurs d'exposition
(contact avec un malade, funérailles, consultations, lien plausible, période d'exposition), B. Histoire de la maladie
(une ligne datée = une étape), listage des contacts par lieu, IV. Actions menées, V. Défis.

Les noms de personnes ne sont JAMAIS repris (cas, cas source, membres de l'équipe, téléphones) : le nom du cas source
est remplacé par son code dans les textes ; l'investigateur devient « Équipe d'investigation ZS … ».
Le fichier est lu ligne par ligne (paragraphes et cellules de tableaux dans l'ordre du document), ce qui fonctionne
que le .doc ait été converti par LibreOffice (tableaux gardés) ou par la conversion du Mac (tableaux à plat).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from core.models import Action, Case, ContactGroup, Event


# ------------------------------------------------------------------------------------------------ lecture du fichier
def doc_vers_docx(path: Path) -> Path:
    """Ancien format Word (.doc) → .docx : LibreOffice (serveur), sinon conversion intégrée du Mac (textutil)."""
    out = Path(tempfile.mkdtemp(prefix="terrain_"))
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        import os
        env = dict(os.environ, HOME=str(out))
        subprocess.run([soffice, f"-env:UserInstallation={(out / 'profil').as_uri()}", "--headless", "--convert-to",
                        "docx", "--outdir", str(out), str(path)], check=False, capture_output=True, timeout=180, env=env)
        res = out / (Path(path).stem + ".docx")
        if res.exists():
            return res
    textutil = shutil.which("textutil")
    if textutil:
        res = out / (Path(path).stem + ".docx")
        subprocess.run([textutil, "-convert", "docx", str(path), "-output", str(res)], check=False,
                       capture_output=True, timeout=120)
        if res.exists():
            return res
    raise ValueError("Ancien format Word (.doc) : ouvrez le fichier dans Word, « Enregistrer sous » au format .docx, "
                     "puis importez ce nouveau fichier.")


def lignes(path: Path | str) -> List[str]:
    """Texte du document, ligne par ligne, dans l'ordre (paragraphes puis cellules des tableaux)."""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    path = Path(path)
    if path.suffix.lower() == ".doc":
        path = doc_vers_docx(path)
    d = Document(str(path))
    out: List[str] = []

    def ajoute(t: str):
        for x in (t or "").replace("\r", "\n").split("\n"):
            x = re.sub(r"[ \t ]+", " ", x).strip()
            if x:
                out.append(x)
    for el in d.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            ajoute(Paragraph(el, d).text)
        elif tag == "tbl":
            for row in Table(el, d).rows:
                vus = []
                for cell in row.cells:
                    if cell._tc in vus:
                        continue
                    vus.append(cell._tc)
                    for p in cell.paragraphs:
                        ajoute(p.text)
    return out


# ------------------------------------------------------------------------------------------------ outils
def _n(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper()
    s = s.replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def reconnu(ls: List[str]) -> bool:
    t = " | ".join(_n(x) for x in ls[:400])
    return "CODE VHF" in t and ("IDENTIFICATION DU DECES" in t or "IDENTIFICATION DU CAS" in t) and \
        ("HISTOIRE DE LA MALADIE" in t or "LISTAGE CONTACTS" in t or "FACTEURS D'EXPOSITION" in t)


LABELS = ["CODE VHF", "NOM", "POST NOM", "POSTNOM", "PRENOM", "AGE", "SEXE", "PROFESSION", "VILLAGE", "AIRE DE SANTE",
          "COMMUNE/TERRITOIRE", "COMMUNE / TERRITOIRE", "ZONE DE SANTE", "LIEU DE DETECTION", "SOURCE DE L'ALERTE",
          "DATE DE NOTIFICATION", "DATE DE CONFIRMATION", "DATE DE DEBUT DES SYMPTOMES", "NATURE DU CAS",
          "DATE DE DECES", "ENTERREMENT DIGNE ET SECURISE FAIT", "CAS CONTACT CONNU", "CAS VACCINE",
          "PERIODE INVESTIGATION", "PERIODE D'INVESTIGATION"]


def _est_label(l: str) -> bool:
    n = _n(l).rstrip(" :")
    return n in LABELS or n.startswith("II-") or n.startswith("II -") or n.startswith("II.")


def _valeur(ls: List[str], *labels: str, max_lignes: int = 1) -> str:
    """Texte qui suit un libellé (sur la même ligne après « : », sinon les lignes suivantes jusqu'au libellé suivant)."""
    for i, l in enumerate(ls):
        n = _n(l)
        for lab in labels:
            if n == lab or n.rstrip(" :") == lab:
                vals = []
                for x in ls[i + 1:i + 1 + max_lignes + 3]:
                    if _est_label(x):
                        break
                    vals.append(x)
                    if len(vals) >= max_lignes:
                        break
                return " ".join(vals).strip()
            if n.startswith(lab + " :") or n.startswith(lab + ":"):
                return l.split(":", 1)[1].strip()
    return ""


def _bloc(ls: List[str], debut: str, fins: Tuple[str, ...]) -> List[str]:
    """Lignes entre un titre de section et le suivant."""
    i0 = next((i for i, l in enumerate(ls) if debut in _n(l)), None)
    if i0 is None:
        return []
    out = []
    for l in ls[i0 + 1:]:
        if any(f in _n(l) for f in fins):
            break
        out.append(l)
    return out


def coche(texte: str, option: str) -> bool:
    """« ☒ Oui » : l'option est cochée (☒, ☑, ✓ ou X juste avant)."""
    t = (texte or "")
    for k in ("☒", "☑", "✓", "✔", "■", "⊠"):
        t = t.replace(k, " QXQ ")
    t = _n(t.replace("☐", " QOQ "))
    return bool(re.search(r"QXQ\s*" + re.escape(_n(option)), t))


_DATE = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?")


def dates(texte: str, annee: Optional[int] = None) -> List[date]:
    """Dates d'un texte, ex. « Du 10 au 13/11/2026 » → 10/11/2026, 13/11/2026 ; « le 8/11/2026 »."""
    t = texte or ""
    out: List[date] = []
    m = re.search(r"(?:du|DU|Du)\s+(\d{1,2})\s+(?:au|AU)\s+(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{2,4})", t)
    if m:
        a = int(m.group(4)) + (2000 if len(m.group(4)) == 2 else 0)
        try:
            out += [date(a, int(m.group(3)), int(m.group(1))), date(a, int(m.group(3)), int(m.group(2)))]
        except ValueError:
            pass
        t = t[:m.start()] + t[m.end():]
    for j, mo, a in _DATE.findall(t):
        an = int(a) + (2000 if a and len(a) == 2 else 0) if a else (annee or (out[-1].year if out else date.today().year))
        try:
            out.append(date(an, int(mo), int(j)))
        except ValueError:
            continue
    return sorted(set(out))


def periode(texte: str, annee: Optional[int] = None) -> Tuple[Optional[date], Optional[date]]:
    """Première période d'une phrase : « du 10 au 13/11/2026 » → (10/11, 13/11) ; sinon (première date, None)."""
    m = re.search(r"(?:du|DU|Du)\s+(\d{1,2})(?:\s*/\s*(\d{1,2}))?(?:\s*/\s*\d{2,4})?\s+(?:au|AU)\s+"
                  r"(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?", texte or "")
    if m:
        a = m.group(5)
        an = int(a) + (2000 if len(a) == 2 else 0) if a else (annee or date.today().year)
        try:
            return date(an, int(m.group(2) or m.group(4)), int(m.group(1))), date(an, int(m.group(4)), int(m.group(3)))
        except ValueError:
            pass
    d = dates(texte, annee)
    return (d[0] if d else None), None


def _date1(texte: str) -> Optional[date]:
    d = dates(texte)
    return d[0] if d else None


# ------------------------------------------------------------------------------------------------ chronologie
_LIEU = re.compile(r"((?i:village|quartier|CTE|CSR|CS|HGR|PS|poste de santé|AS|ZS)\s+[A-ZÀ-Ü][\w’'\-]+(?:\s+[A-ZÀ-Ü][A-ZÀ-Ü’'\-]+)?)")


def _lieux(t: str) -> List[str]:
    vus = []
    if re.search(r"(?i)\bà domicile\b|\bau domicile\b", t):
        vus.append("Domicile")
    for m in _LIEU.finditer(t):
        if re.search(r"(?i)refus\w*", t[max(0, m.start() - 45):m.start()]):
            continue
        x = re.sub(r"\s+", " ", m.group(1)).strip(" ,;.")
        x = x[0].upper() + x[1:]
        if x.lower() not in [v.lower() for v in vus]:
            vus.append(x)
    return vus


def _type(t: str) -> List[Tuple[str, str]]:
    """(type d'étape, titre) détectés dans une ligne de l'histoire de la maladie, dans l'ordre logique."""
    n = _n(t)
    out = []
    if re.search(r"SOIGN|CONTACT (DIRECT )?AVEC|EXPOS", n) and re.search(r"CONTAMINANT|SOURCE|RDC-|DECEDE LE", n) \
            and not re.search(r"DEVENU SUSPECT", n):
        out.append(("Exposition", "Exposition (soins au cas source)" if "SOIGN" in n else "Exposition probable"))
    if re.search(r"DEVENU SUSPECT|DEBUT (DE LA )?MALADIE|PREMIERS SIGNES|A PRESENTE|AVEC COMME SIGNES", n):
        out.append(("Début maladie", "Début maladie"))
    if re.search(r"TRADIPRATICIEN|GUERISSEU|CONSULT|TRAITE A DOMICILE|INFIRMIER|AUTOMEDICATION|PHARMACIE", n) \
            and not out:
        out.append(("Soins / consultation", "Soins / consultation"))
    if re.search(r"DEPLAC|S'EST RENDU|RETOURNE", n) or (re.search(r"REFERE|REFERENCE", n) and "REFUS" not in n):
        out.append(("Déplacement", "Déplacement"))
    if re.search(r"HOSPITALIS|ISOLE AU|ADMIS", n):
        out.append(("Hospitalisation", "Hospitalisation"))
    if re.search(r"ALERTE DECES|DECES COMMUNAUTAIRE|EST DECEDE|DECEDE A|DECEDE AU", n):
        out.append(("Décès", "Décès communautaire" if "COMMUNAUTAIRE" in n else "Décès"))
    if re.search(r"SWAB|PRELEVEMENT", n) and not re.search(r"RESULTAT", n):
        out.append(("Prélèvement", "Prélèvement (swab)"))
    if re.search(r"LABO|RESULTAT", n):
        out.append(("Laboratoire", "Résultat du laboratoire"))
    if re.search(r"ENTERREMENT|INHUMATION|FUNERAILLES", n):
        out.append(("Enterrement" if "FUNERAILLES" not in n else "Funérailles",
                    "Enterrement non sécurisé" if "NON SECURISE" in n else "Enterrement"))
    if not out:
        out.append(("Autre", "Étape du parcours"))
    return out


MOTIFS = {"Exposition": r"SOIGN|CONTACT|EXPOS", "Début maladie": r"SUSPECT|DEBUT|SIGNES", "Soins / consultation":
          r"TRADIPRATICIEN|GUERISSEU|CONSULT|TRAITE|INFIRMIER|AUTOMEDICATION", "Déplacement": r"DEPLAC|RENDU|RETOURN|REFER",
          "Hospitalisation": r"HOSPITALIS|ISOLE|ADMIS", "Décès": r"DECES|DECEDE", "Prélèvement": r"SWAB|PRELEVEMENT",
          "Laboratoire": r"LABO|RESULTAT", "Enterrement": r"ENTERREMENT|INHUMATION", "Funérailles": r"FUNERAILLES"}
PERSONNES = [(r"TRADIPRATICIEN", "Tradipraticiens"), (r"GUERISSEU", "Guérisseuse"), (r"INFIRMIER", "Infirmier"),
             (r"FAMILLE|PARENT", "Famille"), (r"COMMUNAUT", "Communauté"), (r"VOISIN", "Voisins"),
             (r"EQUIPE DE (LA )?RIPOSTE", "Équipe de riposte"), (r"\bAPA\b", "APA"), (r"MOTARD|TAXI", "Motard / taximan"),
             (r"CLIENT", "Clients")]


def _phrase(t: str, typ: str) -> str:
    """Partie de la ligne qui concerne ce type d'étape (une ligne peut décrire deux événements)."""
    morceaux = [x.strip() for x in re.split(r"(?<=[.;])\s+|\s+(?=Cette même date|Le même jour)", t) if x.strip()]
    for x in morceaux:
        if re.search(MOTIFS.get(typ, r"$^"), _n(x)):
            return x
    return t


def _etapes(histoire: List[str], annee: Optional[int], masquer) -> List[Event]:
    from core import narratif as NR
    evs: List[Event] = []
    for brut in histoire:
        t = brut.strip(" -•–;")
        if len(t) < 8 or not dates(t, annee):
            continue
        dl = dates(t, annee)
        for typ, titre in _type(t):
            ph = _phrase(t, typ) if len(_type(t)) > 1 else t
            d1, d2 = periode(ph, annee)
            d1 = d1 or dl[0]
            if typ in ("Enterrement", "Décès", "Prélèvement", "Laboratoire"):
                d2 = None
                if not dates(ph, annee):
                    d1 = dl[-1]
            lx = _lieux(ph)
            np = _n(ph)
            pers = " / ".join(dict.fromkeys(p for motif, p in PERSONNES if re.search(motif, np)))
            ev = Event(date_debut=d1, date_fin=d2 if d2 and d2 != d1 else None, type=typ, titre=titre,
                       description=masquer(ph)[:220], transport=NR._transport(ph),
                       personnes="" if typ in ("Laboratoire", "Prélèvement") else (pers or NR._personnes(ph)))
            if typ == "Enterrement":
                ev.securise = not re.search(r"NON[ -]SECURISE", np)
            if typ == "Déplacement" and len(lx) >= 2:
                ev.lieu, ev.lieu_arrivee = lx[0], lx[1]
            elif typ == "Laboratoire":
                ev.lieu = next((x for x in lx if "LABO" in _n(x)), "Laboratoire")
            elif lx:
                ev.lieu = lx[-1] if typ in ("Enterrement", "Décès") else lx[0]
            evs.append(ev)
    return evs


# ------------------------------------------------------------------------------------------------ lecture complète
class Lecture:
    def __init__(self, case: Case, trouves: List[str], manquants: List[str]):
        self.case, self.trouves, self.manquants = case, trouves, manquants


def lire(path: Path | str, ls: Optional[List[str]] = None) -> Optional[Lecture]:
    from core import narratif as NR
    from core import obligatoires as OBL
    from core import pyramide
    ls = ls if ls is not None else lignes(path)
    if not reconnu(ls):
        return None
    c = Case(maladie="MVE", statut="Confirmé")
    trouves: List[str] = []

    # noms de personnes : jamais repris ; le nom du cas source est remplacé par son code
    noms = [x for x in (_valeur(ls, "NOM"), _valeur(ls, "POST NOM", "POSTNOM"), _valeur(ls, "PRENOM")) if x and len(x) > 2
            and not _est_label(x)]
    code_source = ""
    m = re.search(r"\bRDC[-\s]?[A-Z]{2,4}[-\s]?[A-Z]{2,4}[-\s]?\d{2}[-\s]?\d{3,9}(?:[-\s]?[A-Z]{2,4})?\b",
                  " ".join(_bloc(ls, "CAS CONTACT CONNU", ("CAS VACCINE",))))
    if m:
        code_source = re.sub(r"\s+", "", m.group(0))
    nom_source = ""
    for i, l in enumerate(ls):
        if "NOM DU CONTACT" in _n(l):
            # le nom suit le libellé ou le code, sur la même ligne ou les suivantes : mots en capitales
            for x in [l.split("NOM DU CONTACT")[-1] if "NOM DU CONTACT" in l else ""] + ls[i + 1:i + 4]:
                x = re.sub(r"\bRDC[-\w ]*?-MVE\b|\bRDC-[\w-]+", " ", x)
                m2 = re.search(r"\b([A-ZÀ-Ü][A-ZÀ-Ü’'\-]{1,}(?:\s+[A-ZÀ-Ü][A-ZÀ-Ü’'\-]{1,})+)\b", x)
                if m2 and not _est_label(m2.group(1)) and "CODE" not in m2.group(1):
                    nom_source = m2.group(1).strip()
                    break
            break

    def masquer(t: str) -> str:
        for nm in [nom_source] + noms:
            if nm and len(nm) > 2:
                t = re.sub(re.escape(nm), code_source or "le cas", t, flags=re.I) if nm == nom_source else \
                    re.sub(r"\b" + re.escape(nm) + r"\b", "le cas", t, flags=re.I)
        if code_source:
            t = re.sub(r"(" + re.escape(code_source) + r")(\s*" + re.escape(code_source) + r")+", r"\1", t)
        t = re.sub(r"(?:\+?243|0)\s?\d{2,3}\s?\d{3}\s?\d{3,4}", "", t)          # téléphones
        t = re.sub(r"\S+@\S+", "", t)                                           # courriels
        return re.sub(r"\s{2,}", " ", t).strip()

    # -- I. identification
    code = _valeur(ls, "CODE VHF")
    if code:
        c.code_cas = re.sub(r"\s+", "", code)
        trouves.append("ID du cas (code VHF)")
    age = re.search(r"\d{1,3}", _valeur(ls, "AGE"))
    if age:
        c.age = int(age.group(0))
        c.age_unite = "mois" if "MOIS" in _n(_valeur(ls, "AGE")) else "ans"
        trouves.append("Âge")
    sx = _n(_valeur(ls, "SEXE"))
    if sx[:1] in ("M", "F"):
        c.sexe = sx[:1]
        trouves.append("Sexe")
    prof = _valeur(ls, "PROFESSION")
    if prof:
        c.profession = masquer(prof)
    c.village = _valeur(ls, "VILLAGE")
    aire, zs = _valeur(ls, "AIRE DE SANTE"), _valeur(ls, "ZONE DE SANTE")
    pyr = pyramide.get()
    province = pyr.province_of(zs) or ""
    c.province, c.zs, c.aire_sante = pyr.canonical(province, zs.title() if zs.isupper() else zs,
                                                    aire.title() if aire.isupper() else aire)
    if c.zs:
        trouves.append("Zone et aire de santé")
    for cle, champ, lib in (("DATE DE NOTIFICATION", "date_notification", "Notification"),
                            ("DATE DE CONFIRMATION", "date_confirmation", "Confirmation"),
                            ("DATE DE DEBUT DES SYMPTOMES", "debut_symptomes", "Début des symptômes"),
                            ("DATE DE DECES", "date_deces", "Décès")):
        d = _date1(_valeur(ls, cle))
        if d:
            setattr(c, champ, d)
            trouves.append(lib)
    annee = (c.debut_symptomes or c.date_notification or date.today()).year
    nature = " ".join(_bloc(ls, "NATURE DU CAS", ("DATE DE DECES", "ENTERREMENT")))
    if coche(nature, "Décès") or coche(nature, "Confirmé déc") or c.date_deces:
        c.issue = "Décès"
    elif coche(nature, "Vivant"):
        c.issue = "Vivant"
    if coche(nature, "Probable"):
        c.statut = "Probable"
    if c.issue != "Inconnu":
        trouves.append("État du cas")
    eds = " ".join(_bloc(ls, "ENTERREMENT DIGNE ET SECURISE", ("CAS CONTACT CONNU",)))
    enterrement = None
    if coche(eds, "Non"):
        de = dates(eds.split("enterrement")[-1] if "enterrement" in eds.lower() else eds, annee)
        lx = _lieux(eds)
        enterrement = Event(date_debut=de[-1] if de else c.date_deces, lieu=lx[-1] if lx else "", type="Enterrement",
                            titre="Enterrement non sécurisé", description="Enterrement digne et sécurisé non fait",
                            personnes="Famille / communauté", securise=False)
    elif coche(eds, "Oui"):
        enterrement = Event(date_debut=c.date_deces, type="Enterrement", titre="Enterrement digne et sécurisé",
                            description="EDS réalisé", personnes="Équipe EDS", securise=True)
    cc = " ".join(_bloc(ls, "CAS CONTACT CONNU", ("CAS VACCINE",)))
    if coche(cc, "Oui"):
        c.contact_connu = "Contact connu"
        c.id_cas_source = code_source
        trouves.append("Contact connu" + (" et ID du cas source" if code_source else ""))
    elif coche(cc, "Non"):
        c.contact_connu = "Non contact"
        trouves.append("Non contact")
    vac = " ".join(_bloc(ls, "CAS VACCINE", ("PERIODE INVESTIGATION", "PERIODE D'INVESTIGATION")))
    if coche(vac, "Oui"):
        c.vaccine = "Oui"
        c.date_vaccination = _date1(vac.split("DATE")[-1] if "DATE" in vac.upper() else vac)
    elif coche(vac, "Non"):
        c.vaccine = "Non"
    di = dates(_valeur(ls, "PERIODE INVESTIGATION", "PERIODE D'INVESTIGATION"), annee)
    if di:
        c.date_investigation = di[0]
    c.investigateur = "Équipe d'investigation" + (f" ZS {c.zs}" if c.zs else "")

    # -- III. A. exposition, B. histoire de la maladie
    expo = _bloc(ls, "FACTEURS D'EXPOSITION", ("HISTOIRE DE LA MALADIE",))
    histoire = _bloc(ls, "HISTOIRE DE LA MALADIE", ("LISTAGE CONTACTS", "LISTAGE DES CONTACTS", "IV-", "IV -", "IV."))
    evs = _etapes(histoire, annee, masquer)
    texte_expo = " ".join(expo)
    if c.contact_connu == "Contact connu":
        lien = " ".join(_bloc(ls, "LIEN(S) EPIDEMIOLOGIQUE", ("HISTOIRE DE LA MALADIE",))) or texte_expo
        m = re.search(r"entre le ([^.;]{4,40}?\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4})", lien, re.I)
        ds = dates(m.group(1), annee) if m else []
        if ds:
            c.date_contact_source = ds[-1]
    if not any(e.type == "Exposition" for e in evs):
        m = re.search(r"date de d[ée]but des sympt[ôo]mes\s*:?\s*([^\n]{6,40})", texte_expo, re.I)
        dp = dates(m.group(1), annee) if m else []
        if dp:
            evs.insert(0, Event(date_debut=dp[0], date_fin=dp[-1] if len(dp) > 1 else None, type="Exposition",
                                titre="Exposition probable", date_incertaine=True,
                                description=masquer("Période d'exposition estimée à partir du début des symptômes"),
                                personnes="Cas source / entourage" if code_source else ""))
    if enterrement and not any(e.type == "Enterrement" for e in evs):
        evs.append(enterrement)
    elif enterrement:
        for e in evs:
            if e.type == "Enterrement" and not e.lieu:
                e.lieu = enterrement.lieu
    for e in evs:          # exposition dans l'officine ou au domicile du cas, quand le texte le dit
        if e.type == "Exposition" and not e.lieu:
            nd = _n(e.description + " " + texte_expo)
            lieu = "Pharmacie" if "PHARMAC" in nd else ("Domicile" if "DOMICILE" in nd else "")
            if lieu:
                e.lieu = lieu + (f", village {c.village}" if c.village else "")
    evs.sort(key=lambda e: e.date_debut or date.max)
    c.events = evs
    if evs:
        trouves.append(f"{len(evs)} étape(s) de chronologie")

    # symptômes et phase des premiers signes
    tous = " ".join(histoire + expo)
    c.symptomes = NR.symptomes(tous)
    debut = next((e for e in evs if e.type == "Début maladie"), None)
    if debut:
        nd = _n(debut.description)
        if re.search(r"SAIGN|HEMORRAG|GINGIVO|EPISTAXIS", nd):
            c.phase_dds = "Phase critique"
        elif re.search(r"VOMISS|DIARRH", nd):
            c.phase_dds = "Phase humide"
        elif re.search(r"FIEVRE|CEPHAL|FATIGUE|ASTHENIE|DOULEUR", nd):
            c.phase_dds = "Phase sèche"
    if c.symptomes:
        trouves.append(f"{len(c.symptomes)} symptôme(s)")

    # -- listage des contacts par lieu
    tab = _bloc(ls, "PAR LIEU DE CONTACT", ("IV-", "IV -", "IV.", "ACTIONS DE SANTE"))
    groupes: List[ContactGroup] = []
    i = 0
    while i < len(tab):
        lab = tab[i]
        nl = _n(lab)
        if nl in ("LIEU DE CONTACT", "NOMBRE LISTES", "NOMBRE LISTE") or nl.startswith("TOTAL"):
            i += 2 if nl.startswith("TOTAL") else 1
            continue
        val = tab[i + 1] if i + 1 < len(tab) else ""
        if re.fullmatch(r"\d+", val.strip()) or "COURS" in _n(val) or val.strip() in ("?", "-", ""):
            n = int(val) if val.strip().isdigit() else None
            groupes.append(ContactGroup(categorie=masquer(lab)[:60], nombre=n, risque="Haut", libelle_nombre="listés",
                                        lieu=""))
            i += 2
        else:
            i += 1
    c.contacts = groupes
    if groupes:
        trouves.append(f"{len(groupes)} catégorie(s) de contacts")

    # -- IV. actions menées, V. défis
    i0 = next((i for i, l in enumerate(ls) if re.match(r"IV\s*[-.]", _n(l)) and "ACTION" in _n(l)), None)
    acts = []
    if i0 is not None:
        for l in ls[i0 + 1:]:
            if re.match(r"V\s*[-.]|VI|VII", _n(l)) or "DEFIS" in _n(l):
                break
            acts.append(l)
    c.actions = [Action(texte=masquer(a.strip(" -•"))[:160], priorite="Important", statut="Fait")
                 for a in acts if len(a.strip(" -•")) > 3]
    if c.actions:
        trouves.append(f"{len(c.actions)} action(s) menée(s)")
    defis = _bloc(ls, "DEFIS ET DIFFICULTES", ("VII", "VI.", "VI-", "EQUIPE D'INVESTIGA", "MAPPING DU CAS"))
    defis = [d.rstrip(" ,;") for d in defis]
    defis = [masquer(d.strip(" -•")) for d in defis if len(d.strip(" -•")) > 3]
    if defis:
        c.note_pied = ("Défis : " + " ; ".join(defis))[:400]

    trouves.insert(0, "modèle terrain « Rapport d'investigation MVE » reconnu (noms de personnes non repris)")
    manque = OBL.manquants(c)
    return Lecture(c, trouves, manque)
