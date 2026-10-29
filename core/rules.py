"""Moteur de règles épidémiologiques.

Toutes les règles sont explicites et renvoient la raison appliquée, affichée à
l'utilisateur en info-bulle : l'agent de terrain garde toujours la main.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from config import theme
from core.models import Case, ContactGroup, Event, Place

ROOT = Path(__file__).resolve().parent.parent
_DISEASES: Optional[dict] = None


def diseases() -> dict:
    global _DISEASES
    if _DISEASES is None:
        with open(ROOT / "config" / "diseases.yaml", encoding="utf-8") as f:
            _DISEASES = yaml.safe_load(f)
    return _DISEASES


def disease_params(name: str) -> dict:
    d = diseases()
    return d.get(name) or d["Autre"]


# ---------------------------------------------------------------------------
# Fenêtres épidémiologiques
# ---------------------------------------------------------------------------
@dataclass
class Windows:
    exposition: Optional[Tuple[date, date]] = None
    contagiosite: Optional[Tuple[date, date]] = None
    j0: Optional[date] = None


def burial_date(case: Case) -> Optional[date]:
    for e in case.events:
        if e.type == "Enterrement" and e.date_debut:
            return e.date_debut
    return None


def windows(case: Case) -> Windows:
    p = disease_params(case.maladie)
    w = Windows(j0=case.debut_symptomes)
    if not case.debut_symptomes:
        return w
    j0 = case.debut_symptomes
    w.exposition = (j0 - timedelta(days=p["incubation_max"]), j0 - timedelta(days=p["incubation_min"]))
    if p["contagiosite"] == "jusqu_inhumation":
        end = burial_date(case) or case.date_deces
        if end is None:
            dated = [e.date_fin or e.date_debut for e in case.events if e.date_debut]
            end = max(dated + [j0])
        w.contagiosite = (j0, end)
    else:
        end = j0 + timedelta(days=int(p["contagiosite"]))
        if case.date_deces and p.get("corps_contagieux"):
            end = max(end, burial_date(case) or case.date_deces)
        w.contagiosite = (j0, end)
    return w


def event_phase(ev: Event, w: Windows) -> str:
    """'exposition', 'contagieux' ou ''."""
    if not ev.date_debut:
        return ""
    start, end = ev.date_debut, ev.date_fin or ev.date_debut
    if w.contagiosite and start <= w.contagiosite[1] and end >= w.contagiosite[0]:
        return "contagieux"
    if w.exposition and start <= w.exposition[1] and end >= w.exposition[0]:
        return "exposition"
    return ""


def relative_day(d: Optional[date], j0: Optional[date]) -> str:
    if not d or not j0:
        return ""
    n = (d - j0).days
    return "J0" if n == 0 else f"J{n:+d}"


# ---------------------------------------------------------------------------
# Risque
# ---------------------------------------------------------------------------
_BASE_RISK = {
    "Exposition": ("À investiguer", "Source d'exposition à confirmer"),
    "Investigation": ("Inconnu", "Informations encore manquantes"),
    "Période à documenter": ("Inconnu", "Période non documentée"),
    "Début maladie": ("Modéré", "Début des symptômes : contagiosité débutante"),
    "Soins / consultation": ("Élevé", "Soins d'un cas symptomatique"),
    "Référence": ("Élevé", "Transport d'un cas symptomatique"),
    "Hospitalisation": ("Élevé", "Hospitalisation d'un cas symptomatique"),
    "Activité communautaire": ("Élevé", "Contacts communautaires d'un cas symptomatique"),
    "Rassemblement religieux": ("Élevé", "Rassemblement avec un cas symptomatique"),
    "Déplacement": ("Élevé", "Déplacement d'un cas symptomatique"),
    "Décès": ("Très élevé", "Décès : charge virale maximale, corps contagieux"),
    "Funérailles": ("Très élevé", "Funérailles : contacts rapprochés avec le corps"),
    "Enterrement": ("Très élevé", "Enterrement non sécurisé"),
    "Prélèvement": ("Élevé", "Manipulation d'échantillon / corps"),
    "Laboratoire": ("Contrôlé", "Circuit laboratoire encadré"),
    "Riposte": ("En cours", "Riposte en cours"),
    "Autre": ("Inconnu", "Type d'étape non précisé"),
}
_ESCALATE = ["Faible", "Modéré", "Élevé", "Très élevé"]


def _escalate(level: str) -> str:
    if level in _ESCALATE and level != "Très élevé":
        return _ESCALATE[_ESCALATE.index(level) + 1]
    return level


def suggest_event_risk(ev: Event, case: Case, w: Optional[Windows] = None) -> Tuple[str, str]:
    w = w or windows(case)
    level, reason = _BASE_RISK.get(ev.type, _BASE_RISK["Autre"])
    reasons = [reason]
    phase = event_phase(ev, w)
    symptomatic_types = {"Soins / consultation", "Référence", "Hospitalisation", "Activité communautaire",
                         "Rassemblement religieux", "Déplacement"}
    if ev.type in symptomatic_types and phase == "exposition":
        level, reasons = "Modéré", ["Avant le début des symptômes : faible contagiosité"]
    if ev.type == "Enterrement" and ev.securise:
        level, reasons = "Contrôlé", ["Enterrement digne et sécurisé"]
    if ev.type in {"Décès", "Funérailles"} and ev.securise:
        level, reasons = "Élevé", ["Prise en charge sécurisée du corps"]
    if ev.liquides and level in _ESCALATE:
        level = _escalate(level)
        reasons.append("liquides biologiques : +1 niveau")
    if ev.sans_pci and level in _ESCALATE:
        level = _escalate(level)
        reasons.append("absence de PCI : +1 niveau")
    if ev.contact_corps:
        level = "Très élevé"
        reasons.append("contact avec le corps")
    return level, " ; ".join(reasons)


def event_risk(ev: Event, case: Case, w: Optional[Windows] = None) -> str:
    return ev.risque or suggest_event_risk(ev, case, w)[0]


def global_risk(case: Case) -> Tuple[str, str]:
    if case.risque_global:
        return case.risque_global, "Saisi par l'investigateur"
    w = windows(case)
    best, why = "Inconnu", "Aucune étape documentée"
    for ev in case.events:
        lvl = event_risk(ev, case, w)
        if theme.risk_rank(lvl) > theme.risk_rank(best):
            best, why = lvl, f"Étape la plus à risque : {ev.titre or ev.type}"
    if case.issue == "Décès" and any(e.type == "Enterrement" and not e.securise for e in case.events):
        best, why = "Très élevé", "Décès suivi d'un enterrement non sécurisé"
    return best, why


def suggest_place_risk(place: Place, case: Case) -> str:
    if place.risque:
        return place.risque
    w = windows(case)
    best = ""
    name = place.nom.strip().lower()
    for ev in case.events:
        if name and (name in ev.lieu.lower() or name in ev.lieu_arrivee.lower()
                     or name in ev.titre.lower()):
            lvl = event_risk(ev, case, w)
            if theme.risk_rank(lvl) > theme.risk_rank(best or "En cours"):
                best = lvl
    return best or "Inconnu"


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------
@dataclass
class ContactSummary:
    total_connu: int = 0
    haut_risque_connu: int = 0
    termes: List[int] = field(default_factory=list)
    categories_inconnues: int = 0
    suivis: int = 0
    phrase: str = ""
    pct_suivi: Optional[float] = None


def contact_summary(case: Case) -> ContactSummary:
    s = ContactSummary()
    for g in case.contacts:
        if g.nombre is None:
            s.categories_inconnues += 1
            continue
        s.total_connu += g.nombre
        if g.risque in ("Haut", "Très haut"):
            s.haut_risque_connu += g.nombre
            s.termes.append(g.nombre)
        if g.suivis is not None:
            s.suivis += g.suivis
    if s.termes:
        detail = f" ({' + '.join(str(t) for t in s.termes)})" if len(s.termes) > 1 else ""
        s.phrase = f"Minimum documenté : {s.haut_risque_connu} contacts à haut risque{detail}."
    else:
        s.phrase = "Aucun contact à haut risque dénombré à ce stade."
    if s.categories_inconnues:
        s.phrase += " Les «\u00a0?\u00a0» restent à compléter."
    if s.total_connu:
        s.pct_suivi = round(100 * s.suivis / s.total_connu, 1)
    return s


def contact_followup_end(g: ContactGroup, case: Case) -> Optional[date]:
    if not g.dernier_contact:
        return None
    return g.dernier_contact + timedelta(days=int(disease_params(case.maladie)["suivi_contacts"]))


# ---------------------------------------------------------------------------
# Laboratoire
# ---------------------------------------------------------------------------
def lab_delay_hours(case: Case) -> Optional[float]:
    for lab in case.labs:
        if lab.prelevement and lab.resultat_le:
            return round((lab.resultat_le - lab.prelevement).total_seconds() / 3600, 1)
    return None


# ---------------------------------------------------------------------------
# Contrôles de cohérence
# ---------------------------------------------------------------------------
@dataclass
class Issue:
    niveau: str   # "erreur" | "alerte" | "info"
    message: str


def check_consistency(case: Case) -> List[Issue]:
    out: List[Issue] = []
    j0 = case.debut_symptomes
    for e in case.events:
        lab = e.titre or e.type
        if e.date_fin and e.date_debut and e.date_fin < e.date_debut:
            out.append(Issue("erreur", f"« {lab} » : la date de fin précède la date de début."))
        if not e.date_debut:
            out.append(Issue("alerte", f"« {lab} » : date inconnue (affichée « ? »)."))
    hosp = [e.date_debut for e in case.events if e.type == "Hospitalisation" and e.date_debut]
    if case.date_deces and hosp and case.date_deces < min(hosp):
        out.append(Issue("erreur", "Le décès est daté avant l'hospitalisation."))
    if case.date_deces and j0 and case.date_deces < j0:
        out.append(Issue("erreur", "Le décès est daté avant le début des symptômes."))
    if case.issue == "Décès" and not case.date_deces:
        out.append(Issue("alerte", "Issue « Décès » sans date de décès."))
    if case.date_deces and case.issue != "Décès":
        out.append(Issue("alerte", "Une date de décès est saisie mais l'issue n'est pas « Décès »."))
    for lab in case.labs:
        if lab.prelevement and lab.resultat_le and lab.resultat_le < lab.prelevement:
            out.append(Issue("erreur", "Le résultat de laboratoire précède le prélèvement."))
        if lab.envoi and lab.prelevement and lab.envoi < lab.prelevement:
            out.append(Issue("erreur", "L'envoi au laboratoire précède le prélèvement."))
    if case.date_confirmation and j0 and case.date_confirmation < j0:
        out.append(Issue("erreur", "La confirmation précède le début des symptômes."))
    place_names = {p.nom.strip().lower() for p in case.places if p.nom.strip()}
    for g in case.contacts:
        if not g.lieu.strip():
            out.append(Issue("info", f"Contacts « {g.categorie} » : lieu de contact non précisé."))
        elif place_names and g.lieu.strip().lower() not in place_names:
            out.append(Issue("info", f"Contacts « {g.categorie} » : le lieu « {g.lieu} » n'est pas dans la liste des lieux."))
        if g.nombre is not None and g.suivis is not None and g.suivis > g.nombre:
            out.append(Issue("erreur", f"Contacts « {g.categorie} » : plus de suivis que de listés."))
    # ordre : uniquement les étapes ponctuelles (sans date de fin)
    last = None
    for e in case.events:
        if e.date_debut and not e.date_fin:
            if last and e.date_debut < last[0]:
                out.append(Issue("alerte", f"« {e.titre or e.type} » est placé après « {last[1]} » mais daté avant."))
            last = (e.date_debut, e.titre or e.type)
    for gap in coverage_gaps(case):
        out.append(Issue("info", f"Période non couverte du {gap[0]:%d/%m} au {gap[1]:%d/%m} : "
                                 "ajouter une étape « Période à documenter » ?"))
    return out


def coverage_gaps(case: Case, min_days: int = 3) -> List[Tuple[date, date]]:
    """Trous dans la chronologie entre le début de la fenêtre d'exposition et la fin de la contagiosité."""
    w = windows(case)
    if not w.exposition:
        return []
    start = w.exposition[0]
    end = w.contagiosite[1] if w.contagiosite else case.debut_symptomes
    spans = sorted((e.date_debut, e.date_fin or e.date_debut) for e in case.events if e.date_debut)
    gaps, cursor = [], start
    for s, f in spans:
        if s - cursor > timedelta(days=min_days):
            gaps.append((cursor, s - timedelta(days=1)))
        cursor = max(cursor, f + timedelta(days=1))
    if end and end - cursor > timedelta(days=min_days):
        gaps.append((cursor, end))
    return gaps


# ---------------------------------------------------------------------------
# Actions suggérées
# ---------------------------------------------------------------------------
@dataclass
class Suggestion:
    texte: str
    priorite: str
    raison: str


def suggest_actions(case: Case) -> List[Suggestion]:
    out: List[Suggestion] = []
    s = contact_summary(case)

    def add(texte, prio, raison):
        if texte not in case.suggestions_rejetees and all(texte != x.texte for x in out):
            out.append(Suggestion(texte, prio, raison))

    if case.contacts:
        add("Boucler tous les contacts", "Urgent", s.phrase)
    unknown = [g.categorie.strip() for g in case.contacts if g.nombre is None and g.categorie.strip()]
    if unknown:
        def low(c: str) -> str:
            return c if c[:2].isupper() else c[0].lower() + c[1:]
        add("Identifier " + " / ".join(low(c) for c in unknown[:3]) + (" …" if len(unknown) > 3 else ""),
            "Urgent", "Catégories de contacts non dénombrées")
    if any(e.type == "Exposition" and event_risk(e, case) in ("À investiguer", "Inconnu") for e in case.events) \
            or not any(e.type == "Exposition" for e in case.events):
        add("Reconstituer la source d'exposition", "Urgent", "Source d'exposition non confirmée")
    deadly = case.issue == "Décès" or any(e.type in ("Funérailles", "Enterrement") for e in case.events)
    p = disease_params(case.maladie)
    if case.contacts or deadly:
        add(f"Suivi quotidien {p['suivi_contacts']} jours des contacts", "Important",
            "Durée de suivi pour " + case.maladie)
    if any(e.type == "Enterrement" and not e.securise for e in case.events):
        add("Sensibiliser la communauté (EDS) et suivre les participants aux funérailles", "Urgent",
            "Enterrement non sécurisé")
    bad = [x.site for x in case.ipc if x.statut in ("Non", "Partiel", "Inconnu")]
    if bad:
        add("PCI / décontamination : " + ", ".join(bad), "Urgent", "Sites non décontaminés")
    for x in case.ipc:
        if x.statut == "Décontaminé" and not (x.date and x.equipe and x.produit):
            add(f"Documenter date / équipe / produit : {x.site}", "Important", "Décontamination incomplètement documentée")
    delay = lab_delay_hours(case)
    if delay is None and case.labs:
        add("Documenter les délais de laboratoire", "Important", "Heures de prélèvement / résultat manquantes")
    elif delay is not None and delay > p["labo_delai_alerte_h"]:
        add(f"Analyser le délai laboratoire ({delay:.0f} h)", "Important", "Délai supérieur au seuil")
    if any(e.transport.lower() == "moto" for e in case.events):
        add("Identifier et suivre les motards", "Urgent", "Transport à moto d'un cas symptomatique ou du corps")
    if coverage_gaps(case):
        add("Documenter les périodes manquantes de la chronologie", "Important", "Trous dans la chronologie")
    hcw = [pl.nom for pl in case.places if pl.type in ("Centre de santé", "Hôpital")]
    if hcw:
        add("Vacciner / suivre le personnel soignant : " + ", ".join(hcw), "Important",
            "Exposition en structure de soins")
    return out


# ---------------------------------------------------------------------------
# Complétude
# ---------------------------------------------------------------------------
CRITICAL_FIELDS = [
    ("rang", "Rang du cas"), ("sexe", "Sexe"), ("age", "Âge"), ("zs", "Zone de santé"),
    ("aire_sante", "Aire de santé"), ("date_confirmation", "Date de confirmation"),
    ("debut_symptomes", "Date de début des symptômes"), ("issue", "Issue"),
    ("investigateur", "Investigateur"),
]


def completeness(case: Case) -> Tuple[int, List[str]]:
    missing = []
    for key, label in CRITICAL_FIELDS:
        v = getattr(case, key)
        if v in (None, "", "Inconnu"):
            missing.append(label)
    if not case.events:
        missing.append("Au moins une étape de chronologie")
    if not case.places:
        missing.append("Lieux & expositions")
    if not case.contacts:
        missing.append("Contacts")
    if not case.ipc:
        missing.append("PCI / décontamination")
    if not case.labs:
        missing.append("Laboratoire")
    if any(not e.date_debut for e in case.events):
        missing.append("Dates de certaines étapes")
    unknown_contacts = sum(1 for g in case.contacts if g.nombre is None)
    if unknown_contacts:
        missing.append(f"{unknown_contacts} catégorie(s) de contacts non dénombrée(s)")
    total = len(CRITICAL_FIELDS) + 7
    score = max(0, round(100 * (total - len(missing)) / total))
    return score, missing


def places_from_events(case: Case) -> List[Place]:
    """Propose des lieux à partir de la chronologie (sans doublons)."""
    known = {p.nom.strip().lower() for p in case.places}
    out: List[Place] = []
    type_map = {"Hospitalisation": "Hôpital", "Soins / consultation": "Centre de santé",
                "Rassemblement religieux": "Église / lieu de culte", "Funérailles": "Funérailles",
                "Enterrement": "Enterrement", "Laboratoire": "Laboratoire"}
    for e in case.events:
        for name in (e.lieu, e.lieu_arrivee):
            n = name.strip()
            if not n or "→" in n or n.lower() in known:
                continue
            known.add(n.lower())
            out.append(Place(nom=n, type=type_map.get(e.type, "Village / quartier"),
                             population=e.personnes, risque=""))
    for p in out:
        p.risque = suggest_place_risk(p, case)
    return out
