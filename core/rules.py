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


def phase_dds_jours(case: Case) -> Optional[Tuple[int, int]]:
    """(début, fin) de la phase où était le cas à la date de début rapportée, en jours après J0 (None si inconnue)."""
    key = theme.PHASE_DDS_KEYS.get(case.phase_dds or "")
    pj = disease_params(case.maladie).get("phases_jours") or {}
    if key and key in pj:
        return int(pj[key][0]), int(pj[key][1])
    return None


def recul_j0(case: Case) -> int:
    """Jours entre le début réel de la maladie et la date rapportée par l'équipe.

    Phase des premiers signes précisée : fin de cette phase (sèche 3 j, humide 7 j, critique 16 j) ;
    sinon le recul par défaut de la maladie (MVE / Marburg : 3 j, premiers signes supposés en phase sèche)."""
    ph = phase_dds_jours(case)
    if ph:
        return ph[1]
    return int(disease_params(case.maladie).get("recul_j0", 0) or 0)


@dataclass
class EstimationJ0:
    j0: Optional[date] = None          # J0 retenu (milieu de l'intervalle si estimé)
    j0_min: Optional[date] = None
    j0_max: Optional[date] = None
    source: str = ""                   # « rapportée », « début maladie », « phase humide », « décès », « soins »

    @property
    def estime(self) -> bool:
        return self.source not in ("", "rapportée")


def _humide_datee(case: Case, apres: Optional[date] = None) -> Optional[date]:
    if case.debut_phase_humide:
        return case.debut_phase_humide
    wet = [e.date_debut for e in case.sorted_events()
           if e.date_debut and (apres is None or e.date_debut > apres) and _wet_text(e)]
    return wet[0] if wet else None


def estimer_j0(case: Case) -> EstimationJ0:
    """J0 du cas, quelle que soit la phase où il a été trouvé (vivant ou décédé).

    Date rapportée connue : J0 = date rapportée − recul (la maladie a commencé 2 à 3 jours avant).
    Sinon, on remonte depuis ce qui est daté, en tenant compte de l'intervalle habituel entre les phases :
    étape « Début maladie » (même recul), phase humide (J4 à J7), décès (J7 à J10), premiers soins (J0 à J3).
    Plusieurs repères : on garde l'intervalle commun s'il existe."""
    p = disease_params(case.maladie)
    recul = recul_j0(case)
    if case.debut_symptomes:
        j = case.debut_symptomes - timedelta(days=recul)
        return EstimationJ0(j, j, j, "rapportée")
    rep: List[Tuple[date, date, str]] = []
    debut = next((e.date_debut for e in case.sorted_events() if e.type == "Début maladie" and e.date_debut), None)
    if debut:
        j = debut - timedelta(days=recul)
        rep.append((j, j, "début maladie"))
    if p.get("phase_humide_j"):
        h = _humide_datee(case)
        if h:
            a, b = p.get("phase_humide_intervalle", [p["phase_humide_j"], p["phase_humide_j"]])
            rep.append((h - timedelta(days=int(b)), h - timedelta(days=int(a)), "phase humide"))
    dc = case.date_deces or next((e.date_debut for e in case.sorted_events() if e.type == "Décès" and e.date_debut), None)
    if dc and p.get("deces_intervalle"):
        a, b = p["deces_intervalle"]
        rep.append((dc - timedelta(days=int(b)), dc - timedelta(days=int(a)), "décès"))
    soins = next((e.date_debut for e in case.sorted_events()
                  if e.type in ("Soins / consultation", "Référence", "Hospitalisation") and e.date_debut), None)
    if soins:
        rep.append((soins - timedelta(days=int(p.get("soins_apres_j0_max", 3))), soins, "soins"))
    if not rep:
        return EstimationJ0()
    lo, hi, src = rep[0]
    for a, b, s in rep[1:]:
        if max(lo, a) <= min(hi, b):          # repères cohérents : on resserre l'intervalle
            lo, hi = max(lo, a), min(hi, b)
            if s not in src:
                src += " + " + s
    j = lo + timedelta(days=(hi - lo).days // 2)
    return EstimationJ0(j, lo, hi, src)


def j0_retenu(case: Case) -> Optional[date]:
    """J0 utilisé pour les calculs (rapporté − recul, ou estimé depuis la phase où le cas a été trouvé)."""
    return estimer_j0(case).j0


def exposition_estimee(case: Case) -> Optional[Tuple[date, date]]:
    """Date estimée d'exposition (intervalle), calculée depuis le J0 retenu ou estimé."""
    e = estimer_j0(case)
    if not e.j0:
        return None
    p = disease_params(case.maladie)
    return (e.j0_min - timedelta(days=p["incubation_max"]), e.j0_max - timedelta(days=p["incubation_min"]))


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
    j0 = j0_retenu(case)
    w = Windows(j0=j0)
    if not j0:
        return w
    w.exposition = exposition_estimee(case)
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


# ---------------------------------------------------------------------------
# Phases de la maladie : point d'infection → incubation → phase sèche → phase humide (→ décès)
# ---------------------------------------------------------------------------
@dataclass
class Phases:
    j0: Optional[date] = None                       # J0 retenu (rapporté − recul)
    j0_rapporte: Optional[date] = None              # date rapportée par l'équipe
    recul: int = 0
    j0_source: str = ""                             # rapportée, ou repère utilisé pour l'estimer
    j0_intervalle: Optional[Tuple[date, date]] = None
    exposition: Optional[Tuple[date, date]] = None  # point d'infection estimé (J-max → J-min)
    incubation: Optional[Tuple[int, int]] = None     # (min, max) jours
    incubation_typique: Optional[Tuple[int, int]] = None
    humide: Optional[date] = None                   # entrée en phase humide
    humide_source: str = ""                          # « saisie », « rapportée » (chronologie / symptômes) ou « estimée »
    critique: Optional[date] = None                 # entrée en phase critique (phase 3 : saignements, défaillances)
    critique_source: str = ""
    deces: Optional[date] = None
    phase_dds: str = ""                              # seche / humide / critique : phase à la date rapportée
    exposition_source: str = "estimée"               # estimée, dernier contact, cas source, à rechercher
    source_label: str = ""                           # ID du cas source quand ses dates ont servi
    deux_phases: bool = False                        # MVE / Marburg : phases sèche et humide


def _wet_text(ev: Event) -> bool:
    t = f"{ev.titre} {ev.description}".lower()
    return ev.liquides or any(m in t for m in theme.MOTS_HUMIDES)


def _critical_text(ev: Event) -> bool:
    t = f"{ev.titre} {ev.description}".lower()
    return any(m in t for m in theme.MOTS_CRITIQUES)


def periode_contagieuse(case: Case) -> Optional[Tuple[date, date]]:
    """Période où le cas était contagieux : J0 retenu → inhumation (ou décès, ou dernière étape datée)."""
    return windows(case).contagiosite


def exposition_contact(case: Case, source: Optional[Case] = None) -> Tuple[Optional[Tuple[date, date]], str, str]:
    """Exposition d'un contact connu, sans estimation depuis son propre J0 (recommandation de l'équipe) :
    1. date(s) du dernier contact avec le cas source saisies dans la fiche ;
    2. sinon la période contagieuse du cas source (s'il est enregistré), limitée à la fenêtre d'incubation du cas ;
    3. sinon « à rechercher ». Renvoie (intervalle, origine, ID du cas source utilisé)."""
    if case.date_contact_source:
        return (case.date_contact_source, case.date_contact_source), "dernier contact", ""
    if source is not None:
        cont = periode_contagieuse(source)
        if cont:
            est = exposition_estimee(case)
            if est and max(cont[0], est[0]) <= min(cont[1], est[1]):
                return (max(cont[0], est[0]), min(cont[1], est[1])), "cas source", source.code_cas or ""
            return cont, "cas source", source.code_cas or ""
    return None, "à rechercher", ""


def phases(case: Case, source: Optional[Case] = None) -> Phases:
    p = disease_params(case.maladie)
    est = estimer_j0(case)
    ph = Phases(j0=est.j0, j0_rapporte=case.debut_symptomes, recul=recul_j0(case), j0_source=est.source,
                j0_intervalle=(est.j0_min, est.j0_max) if est.j0 else None, incubation=(p["incubation_min"], p["incubation_max"]),
                deux_phases=bool(p.get("phase_humide_j")))
    ph.phase_dds = theme.PHASE_DDS_KEYS.get(case.phase_dds or "", "")
    if p.get("incubation_typique"):
        ph.incubation_typique = tuple(p["incubation_typique"])
    ph.deces = case.date_deces or next((e.date_debut for e in case.sorted_events() if e.type == "Décès" and e.date_debut), None)
    j0 = ph.j0
    if not j0:
        return ph
    ph.exposition = exposition_estimee(case)
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE:
        expo, origine, lab = exposition_contact(case, source)
        ph.exposition_source, ph.source_label = origine, lab
        if expo:
            ph.exposition = expo
    if not ph.deux_phases:
        return ph
    if case.debut_phase_humide:
        ph.humide, ph.humide_source = case.debut_phase_humide, "saisie"
    else:
        # la phase sèche dure au moins le jour du début : on cherche les signes humides après J0
        # l'étape « Début maladie » (date rapportée) décrit les premiers signes : on cherche après elle
        debut = next((e.date_debut for e in case.sorted_events() if e.type == "Début maladie" and e.date_debut), None)
        apres = ph.j0_rapporte or debut or j0
        wet = [e.date_debut for e in case.sorted_events() if e.date_debut and e.date_debut > apres and _wet_text(e)]
        if wet:
            ph.humide, ph.humide_source = wet[0], "rapportée"
        else:
            ph.humide, ph.humide_source = j0 + timedelta(days=int(p["phase_humide_j"])), "estimée"
    dds = case.debut_symptomes
    if ph.phase_dds in ("humide", "critique") and dds and not case.debut_phase_humide \
            and not (ph.humide_source == "rapportée" and ph.humide <= dds):
        ph.humide, ph.humide_source = dds, "rapportée"          # premiers signes rapportés déjà humides
    # phase critique (phase 3) : signes datés dans la chronologie, phase des premiers signes, ou décès
    crit = [e.date_debut for e in case.sorted_events() if e.date_debut and e.date_debut > j0 and _critical_text(e)
            and e.type not in ("Laboratoire", "Riposte", "Investigation")]
    if ph.phase_dds == "critique" and dds:
        ph.critique, ph.critique_source = dds, "rapportée"
    elif crit:
        ph.critique, ph.critique_source = crit[0], "rapportée"
    elif ph.deces:
        a = int((p.get("phases_jours") or {}).get("critique", [7, 16])[0])
        ph.critique, ph.critique_source = min(ph.deces, j0 + timedelta(days=a)), "estimée"
    if ph.critique and ph.humide and ph.critique < ph.humide:
        ph.humide, ph.humide_source = ph.critique, ph.critique_source
    if ph.deces and ph.humide > ph.deces:
        ph.humide, ph.humide_source = ph.deces, "estimée"
    if ph.deces and ph.critique and ph.critique > ph.deces:
        ph.critique = ph.deces
    return ph


def event_stage(ev: Event, ph: Phases) -> str:
    """Phase de la maladie au début de l'étape : infection, incubation, seche, humide, deces, symptomes ou ''."""
    if not ev.date_debut or not ph.j0:
        return ""
    d = ev.date_debut
    if d < ph.j0:
        return "infection" if ev.type == "Exposition" else "incubation"
    if ev.type in {"Décès", "Funérailles", "Enterrement"} or (ph.deces and d >= ph.deces):
        return "deces"
    if not ph.deux_phases:
        return "symptomes"
    if ph.critique and d >= ph.critique:
        return "critique"
    return "humide" if ph.humide and d >= ph.humide else "seche"


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


_SANS_PATIENT = {"Laboratoire", "Riposte", "Investigation", "Période à documenter", "Exposition"}


def suggest_event_risk(ev: Event, case: Case, w: Optional[Windows] = None,
                       ph: Optional["Phases"] = None) -> Tuple[str, str]:
    """Risque suggéré d'une étape, en trois temps (règle affichée en info-bulle) :
    1. état du cas : phase de la maladie à la date de l'étape (incubation non contagieuse, phase humide +1,
       phase critique très élevé) ;
    2. mode de transmission : contact avec le corps, liquides biologiques, absence de PCI, prise en charge sécurisée ;
    3. l'état des contacts est pris en compte dans le risque global du cas (global_risk)."""
    w = w or windows(case)
    ph = ph or phases(case)
    level, reason = _BASE_RISK.get(ev.type, _BASE_RISK["Autre"])
    reasons = [reason]
    phase = event_phase(ev, w)
    stage = event_stage(ev, ph)
    symptomatic_types = {"Soins / consultation", "Référence", "Hospitalisation", "Activité communautaire",
                         "Rassemblement religieux", "Déplacement"}
    if ev.type in symptomatic_types and (stage in ("incubation", "infection") or (not stage and phase == "exposition")):
        level, reasons = "Faible", ["Avant le début des symptômes (incubation) : non contagieux"]
    elif ev.type not in _SANS_PATIENT:
        # la phase ne relève le risque que si elle est documentée (signes datés ou saisis), pas seulement estimée
        if stage == "humide" and level in _ESCALATE:
            if ph.humide_source in ("saisie", "rapportée"):
                level = _escalate(level)
                reasons.append("phase humide : très contagieux (liquides biologiques) +1 niveau")
            else:
                reasons.append("phase humide probable (estimée) : vérifier les signes")
        elif stage == "critique" and level in _ESCALATE:
            if ph.critique_source == "rapportée":
                level = "Très élevé"
                reasons.append("phase critique : saignements / défaillances, très contagieux")
            else:
                reasons.append("phase critique probable (estimée)")
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


def phase_atteinte(case: Case, ph: Optional["Phases"] = None) -> str:
    """Phase la plus avancée documentée : seche, humide, critique (ou '')."""
    ph = ph or phases(case)
    if ph.phase_dds == "critique" or ph.critique_source == "rapportée" or ph.deces \
            or any(s in theme.HEMORRHAGIC for s in case.symptomes):
        return "critique"
    if ph.phase_dds == "humide" or ph.humide_source in ("saisie", "rapportée") \
            or any(s in theme.SYMPTOMES_HUMIDES for s in case.symptomes):
        return "humide"
    return "seche" if ph.j0 else ""


def global_risk(case: Case) -> Tuple[str, str]:
    """Risque global : étape la plus à risque, puis état du cas (phase atteinte) et état des contacts."""
    if case.risque_global:
        return case.risque_global, "Saisi par l'investigateur"
    w = windows(case)
    ph = phases(case)
    best, why = "Inconnu", "Aucune étape documentée"
    for ev in case.events:
        lvl = ev.risque or suggest_event_risk(ev, case, w, ph)[0]
        if theme.risk_rank(lvl) > theme.risk_rank(best):
            best, why = lvl, f"Étape la plus à risque : {ev.titre or ev.type}"
    if case.issue == "Décès" and any(e.type == "Enterrement" and not e.securise for e in case.events):
        best, why = "Très élevé", "Décès suivi d'un enterrement non sécurisé"
    stade = phase_atteinte(case, ph)
    non_listes = not case.contacts or any(g.nombre is None for g in case.contacts)
    if stade in ("humide", "critique") and non_listes:
        best = "Très élevé"
        why += f" ; phase {stade} atteinte et contacts non (entièrement) listés"
    elif case.contact_connu == "Non contact" and best in _ESCALATE:
        best = _escalate(best)
        why += " ; non connu comme contact : chaîne de transmission non identifiée (+1 niveau)"
    elif case.contact_connu == "Contact connu suivi":
        why += " ; contact connu et suivi"
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
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.id_cas_source.strip():
        out.append(Issue("erreur", "Contact connu : l'ID du cas source est obligatoire (à compléter)."))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.date_contact_source:
        out.append(Issue("alerte", "Contact connu : renseigner la date du dernier contact avec le cas source "
                                   "(l'exposition n'est pas estimée pour un contact connu)."))
    if case.date_notification and j0 and case.date_notification < j0:
        out.append(Issue("erreur", "La notification précède le début des symptômes."))
    if case.date_notification and case.date_confirmation and case.date_confirmation < case.date_notification:
        out.append(Issue("alerte", "La confirmation précède la notification."))
    if case.date_contact_source and j0 and case.date_contact_source > j0:
        out.append(Issue("alerte", "Le dernier contact avec le cas source est postérieur au début des symptômes."))
    if case.vaccine == "Oui" and not case.date_vaccination:
        out.append(Issue("info", "Cas vacciné : préciser la date de vaccination."))
    if case.debut_symptomes and case.phase_dds in ("", "Inconnue"):
        out.append(Issue("info", "Préciser la phase des premiers signes rapportés (sèche, humide ou critique) : "
                                 "elle détermine le J0 retenu."))
    for e in personnes_manquantes(case):
        out.append(Issue("alerte", f"« {e.titre or e.type} » : personnes présentes à compléter."))
    if case.issue == "Décès" and not case.date_deces:
        out.append(Issue("alerte", "État « Décès » sans date de décès."))
    if case.date_deces and case.issue != "Décès":
        out.append(Issue("alerte", "Une date de décès est saisie mais l'état n'est pas « Décès »."))
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
    ("debut_symptomes", "Date de début des symptômes"), ("phase_dds", "Phase des premiers signes rapportés"),
    ("issue", "État du cas"), ("date_notification", "Date de notification"), ("vaccine", "Vacciné ou non"),
    ("agent_sante", "Agent de santé (PPL) ou non"),
    ("investigateur", "Investigateur"), ("contact_connu", "Contact connu ou non contact"),
]


def personnes_manquantes(case: Case) -> List[Event]:
    """Étapes de la chronologie dont les « Personnes présentes » ne sont pas renseignées."""
    return [e for e in case.events if not e.personnes.strip() and e.type not in theme.SANS_PERSONNES]


def completeness(case: Case) -> Tuple[int, List[str]]:
    missing = []
    for key, label in CRITICAL_FIELDS:
        v = getattr(case, key)
        if v in (None, "", "Inconnu", "Inconnue"):
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
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.id_cas_source.strip():
        missing.append("ID du cas source (contact connu)")
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.date_contact_source:
        missing.append("Date du dernier contact avec le cas source")
    sans = personnes_manquantes(case)
    if sans:
        missing.append(f"Personnes présentes : {len(sans)} étape(s) à compléter")
    total = len(CRITICAL_FIELDS) + 10
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
