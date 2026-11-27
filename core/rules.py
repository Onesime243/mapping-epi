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
from core.langue import tr, trf
from core.models import NOTE_PIED_DEFAUT, Case, ContactGroup, Event, Place

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
    reasons = [tr(reason)]
    phase = event_phase(ev, w)
    stage = event_stage(ev, ph)
    symptomatic_types = {"Soins / consultation", "Référence", "Hospitalisation", "Activité communautaire",
                         "Rassemblement religieux", "Déplacement"}
    if ev.type in symptomatic_types and (stage in ("incubation", "infection") or (not stage and phase == "exposition")):
        level, reasons = "Faible", [tr("Avant le début des symptômes (incubation) : non contagieux")]
    elif ev.type not in _SANS_PATIENT:
        # la phase ne relève le risque que si elle est documentée (signes datés ou saisis), pas seulement estimée
        if stage == "humide" and level in _ESCALATE:
            if ph.humide_source in ("saisie", "rapportée"):
                level = _escalate(level)
                reasons.append(tr("phase humide : très contagieux (liquides biologiques) +1 niveau"))
            else:
                reasons.append(tr("phase humide probable (estimée) : vérifier les signes"))
        elif stage == "critique" and level in _ESCALATE:
            if ph.critique_source == "rapportée":
                level = "Très élevé"
                reasons.append(tr("phase critique : saignements / défaillances, très contagieux"))
            else:
                reasons.append(tr("phase critique probable (estimée)"))
    if ev.type == "Enterrement" and ev.securise:
        level, reasons = "Contrôlé", [tr("Enterrement digne et sécurisé")]
    if ev.type in {"Décès", "Funérailles"} and ev.securise:
        level, reasons = "Élevé", [tr("Prise en charge sécurisée du corps")]
    if ev.liquides and level in _ESCALATE:
        level = _escalate(level)
        reasons.append(tr("liquides biologiques : +1 niveau"))
    if ev.sans_pci and level in _ESCALATE:
        level = _escalate(level)
        reasons.append(tr("absence de PCI : +1 niveau"))
    if ev.contact_corps:
        level = "Très élevé"
        reasons.append(tr("contact avec le corps"))
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
        return case.risque_global, tr("Saisi par l'investigateur")
    w = windows(case)
    ph = phases(case)
    best, why = "Inconnu", tr("Aucune étape documentée")
    for ev in case.events:
        lvl = ev.risque or suggest_event_risk(ev, case, w, ph)[0]
        if theme.risk_rank(lvl) > theme.risk_rank(best):
            best, why = lvl, trf("Étape la plus à risque : {etape}", etape=ev.titre or tr(ev.type))
    if case.issue == "Décès" and any(e.type == "Enterrement" and not e.securise for e in case.events):
        best, why = "Très élevé", tr("Décès suivi d'un enterrement non sécurisé")
    stade = phase_atteinte(case, ph)
    non_listes = not case.contacts or any(g.nombre is None for g in case.contacts)
    if stade in ("humide", "critique") and non_listes:
        best = "Très élevé"
        why += trf(" ; phase {stade} atteinte et contacts non (entièrement) listés", stade=tr(stade))
    elif case.contact_connu == "Non contact" and best in _ESCALATE:
        best = _escalate(best)
        why += tr(" ; non connu comme contact : chaîne de transmission non identifiée (+1 niveau)")
    elif case.contact_connu == "Contact connu suivi":
        why += tr(" ; contact connu et suivi")
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
        s.phrase = trf("Minimum documenté : {n} contacts à haut risque{detail}.", n=s.haut_risque_connu, detail=detail)
    else:
        s.phrase = tr("Aucun contact à haut risque dénombré à ce stade.")
    if s.categories_inconnues:
        s.phrase += tr(" Les «\u00a0?\u00a0» restent à compléter.")
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
        lab = e.titre or tr(e.type)
        if e.date_fin and e.date_debut and e.date_fin < e.date_debut:
            out.append(Issue("erreur", trf("« {etape} » : la date de fin précède la date de début.", etape=lab)))
        if not e.date_debut:
            out.append(Issue("alerte", trf("« {etape} » : date inconnue (affichée « ? »).", etape=lab)))
    hosp = [e.date_debut for e in case.events if e.type == "Hospitalisation" and e.date_debut]
    if case.date_deces and hosp and case.date_deces < min(hosp):
        out.append(Issue("erreur", tr("Le décès est daté avant l'hospitalisation.")))
    if case.date_deces and j0 and case.date_deces < j0:
        out.append(Issue("erreur", tr("Le décès est daté avant le début des symptômes.")))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.id_cas_source.strip():
        out.append(Issue("erreur", tr("Contact connu : l'ID du cas source est obligatoire (à compléter).")))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.date_contact_source:
        out.append(Issue("alerte", tr("Contact connu : renseigner la date du dernier contact avec le cas source "
                                      "(l'exposition n'est pas estimée pour un contact connu).")))
    if case.date_notification and j0 and case.date_notification < j0:
        out.append(Issue("erreur", tr("La notification précède le début des symptômes.")))
    if case.date_notification and case.date_confirmation and case.date_confirmation < case.date_notification:
        out.append(Issue("alerte", tr("La confirmation précède la notification.")))
    if case.date_contact_source and j0 and case.date_contact_source > j0:
        out.append(Issue("alerte", tr("Le dernier contact avec le cas source est postérieur au début des symptômes.")))
    if case.vaccine == "Oui" and not case.date_vaccination:
        out.append(Issue("info", tr("Cas vacciné : préciser la date de vaccination.")))
    if case.debut_symptomes and case.phase_dds in ("", "Inconnue"):
        out.append(Issue("info", tr("Préciser la phase des premiers signes rapportés (sèche, humide ou critique) : "
                                    "elle détermine le J0 retenu.")))
    for e in personnes_manquantes(case):
        out.append(Issue("alerte", trf("« {etape} » : personnes présentes à compléter.", etape=e.titre or tr(e.type))))
    if case.issue == "Décès" and not case.date_deces:
        out.append(Issue("alerte", tr("État « Décès » sans date de décès.")))
    if case.date_deces and case.issue != "Décès":
        out.append(Issue("alerte", tr("Une date de décès est saisie mais l'état n'est pas « Décès ».")))
    for lab in case.labs:
        if lab.prelevement and lab.resultat_le and lab.resultat_le < lab.prelevement:
            out.append(Issue("erreur", tr("Le résultat de laboratoire précède le prélèvement.")))
        if lab.envoi and lab.prelevement and lab.envoi < lab.prelevement:
            out.append(Issue("erreur", tr("L'envoi au laboratoire précède le prélèvement.")))
    if case.date_confirmation and j0 and case.date_confirmation < j0:
        out.append(Issue("erreur", tr("La confirmation précède le début des symptômes.")))
    place_names = {p.nom.strip().lower() for p in case.places if p.nom.strip()}
    for g in case.contacts:
        if not g.lieu.strip():
            out.append(Issue("info", trf("Contacts « {cat} » : lieu de contact non précisé.", cat=g.categorie)))
        elif place_names and g.lieu.strip().lower() not in place_names:
            out.append(Issue("info", trf("Contacts « {cat} » : le lieu « {lieu} » n'est pas dans la liste des lieux.", cat=g.categorie, lieu=g.lieu)))
        if g.nombre is not None and g.suivis is not None and g.suivis > g.nombre:
            out.append(Issue("erreur", trf("Contacts « {cat} » : plus de suivis que de listés.", cat=g.categorie)))
    # ordre : uniquement les étapes ponctuelles (sans date de fin)
    last = None
    for e in case.events:
        if e.date_debut and not e.date_fin:
            if last and e.date_debut < last[0]:
                out.append(Issue("alerte", trf("« {etape} » est placé après « {avant} » mais daté avant.", etape=e.titre or tr(e.type), avant=last[1])))
            last = (e.date_debut, e.titre or tr(e.type))
    out.extend(controles_qualite(case))
    for gap in coverage_gaps(case):
        out.append(Issue("info", trf("Période non couverte du {debut} au {fin} : ajouter une étape « Période à documenter » ?",
                                    debut=f"{gap[0]:%d/%m}", fin=f"{gap[1]:%d/%m}")))
    par_lieu: dict = {}
    for ou, extrait in noms_personnes(case):
        par_lieu.setdefault(ou, []).append(extrait)
    for ou, ex in par_lieu.items():
        cites = ", ".join(f"« {e} »" for e in ex)
        out.append(Issue("alerte", trf("Nom de personne ? {ou} : {cites}. L'outil ne doit contenir que des identifiants : "
                                      "remplacez le nom par un ID ou un rôle (ex. « mère du cas »).", ou=ou, cites=cites)))
    return out


def _mentionne_cte(e: Event) -> bool:
    import re
    txt = f" {e.lieu_arrivee or e.lieu} {e.titre} "
    return bool(re.search(r"\bCT[EI]\b", txt, re.I))


def controles_qualite(case: Case) -> List[Issue]:
    """Contrôles de la chronologie simplifiée et de la cascade des contacts (lot 1 de Mapping Épi 2.0).
    Rien n'est corrigé automatiquement : chaque point est signalé pour vérification."""
    out: List[Issue] = []
    j0 = case.debut_symptomes
    conf = case.date_confirmation
    if case.date_alerte and j0 and case.date_alerte < j0:
        out.append(Issue("alerte", tr("L'alerte précède le début des symptômes rapporté.")))
    if case.date_alerte and case.date_investigation and case.date_investigation < case.date_alerte:
        out.append(Issue("alerte", tr("L'investigation précède l'alerte.")))
    if conf and case.date_isolement and (case.date_isolement - conf).days > 1:
        out.append(Issue("alerte", trf("Isolement effectif {n} j après la confirmation (seuil 1 j) : motif à documenter.",
                                       n=(case.date_isolement - conf).days)))
    if j0 and case.date_isolement and case.date_isolement < j0:
        out.append(Issue("alerte", tr("L'isolement est daté avant le début des symptômes rapporté.")))
    if case.date_admission_cte:
        if case.date_deces and case.date_deces < case.date_admission_cte:
            out.append(Issue("erreur", tr("Le décès est daté avant l'admission au CTE.")))
        if j0 and case.date_admission_cte < j0:
            out.append(Issue("alerte", tr("L'admission au CTE précède le début des symptômes rapporté.")))
        cte = [e.date_debut for e in case.sorted_events() if e.date_debut and _mentionne_cte(e)]
        if cte and case.date_admission_cte not in cte:
            out.append(Issue("alerte", trf("Contradiction : admission au CTE le {a}, mais la chronologie place le CTE le {b}. "
                                           "Valider la bonne date.", a=f"{case.date_admission_cte:%d/%m}", b=f"{cte[0]:%d/%m}")))
    # cascade des contacts : chaque étape a son propre nombre
    for g in case.contacts:
        cat = g.categorie or "?"
        if g.exposes is not None and g.nombre is not None and g.nombre > g.exposes:
            out.append(Issue("alerte", trf("Contacts « {cat} » : plus de listés que d'exposés estimés.", cat=cat)))
        if g.nombre is not None and g.symptomatiques is not None and g.symptomatiques > g.nombre:
            out.append(Issue("erreur", trf("Contacts « {cat} » : plus de contacts devenus symptomatiques que de listés.", cat=cat)))
        if g.nombre is not None and g.confirmes is not None and g.confirmes > g.nombre:
            out.append(Issue("erreur", trf("Contacts « {cat} » : plus de contacts devenus confirmés que de listés.", cat=cat)))
    listes = [g.nombre for g in case.contacts if g.nombre is not None]
    suivis = [g.suivis for g in case.contacts if g.suivis is not None]
    suivi_fait = any("suivi" in (a.texte or "").lower() and a.statut == "Fait" for a in case.actions)
    if listes and sum(listes) > 0 and suivis and sum(suivis) == 0 and suivi_fait:
        out.append(Issue("alerte", tr("Contacts : 0 suivi saisi alors qu'une action de suivi est marquée « Fait » : à réconcilier.")))
    from core import dhis2 as _dhis2
    rap = _dhis2.rapprochement(case)
    if rap["trouve"] is False and case.code_cas.strip():
        out.append(Issue("alerte", tr("ID du cas introuvable dans la liste linéaire DHIS2 : vérifier le N° EPID.")))
    dl, ds = rap["dhis2"], (case.contacts_dhis2_suivis if rap["source"] == "saisi" else None)
    if dl is not None and ds is not None and ds > dl:
        out.append(Issue("erreur", tr("DHIS2 : plus de contacts suivis que de listés.")))
    if dl is not None and listes:
        ecart = sum(listes) - dl
        if ecart > 0:
            out.append(Issue("info", trf("Contacts : {m} listés dans la fiche, {d} dans DHIS2 (sous-listing potentiel, écart {e}). "
                                         "Même nombre ne veut pas dire mêmes personnes.", m=sum(listes), d=dl, e=ecart)))
        elif ecart < 0:
            out.append(Issue("info", trf("Contacts : {d} listés dans DHIS2, {m} dans la fiche ({e} de plus dans DHIS2).",
                                         m=sum(listes), d=dl, e=-ecart)))
    # issue clinique : deux PCR négatives après le dernier résultat positif, cas toujours « En traitement »
    res = sorted([(l.resultat_le or l.prelevement, l.resultat) for l in case.labs if (l.resultat_le or l.prelevement) and l.resultat],
                 key=lambda r: r[0])
    neg = 0
    for _d, r in res:
        neg = neg + 1 if r == "Négatif" else 0
    if neg >= 2 and any(r == "Positif" for _d, r in res) and case.issue == "En traitement":
        out.append(Issue("info", tr("Deux PCR négatives après le résultat positif et cas toujours « En traitement » : "
                                    "issue à valider par la prise en charge.")))
    # lieux peut-être identiques (même nom une fois les sigles et accents retirés)
    from core.lieux import cle
    vus: dict = {}
    noms = [p.nom.strip() for p in case.places if p.nom.strip()]
    generiques = {"cm", "cs", "csr", "ps", "hgr", "ch", "chu", "hopital", "clinique", "centre", "medical", "sante",
                  "poste", "de", "du", "des", "la", "le", "les", "l", "d"}
    for n in noms:
        k = " ".join(w for w in cle(n).split() if w not in generiques)
        if len(k) < 4:
            continue
        if k in vus and vus[k] != n:
            out.append(Issue("info", trf("Lieux peut-être identiques : « {a} » et « {b} » (fusionner ?).", a=vus[k], b=n)))
        vus.setdefault(k, n)
    return out


# ---------------------------------------------------------------------------
# Noms de personnes dans les textes libres (confidentialité)
# ---------------------------------------------------------------------------
import re as _re

# sigles et mots en majuscules courants dans une riposte : jamais pris pour un nom
_SIGLES = {"MVE", "PCI", "IPC", "HGR", "CTE", "CS", "ZS", "AS", "EDS", "OMS", "WHO", "MSF", "ALIMA", "IRC", "INRB",
           "UMIE", "RDC", "SGI", "PPL", "CBCA", "CEBCE", "CEPAC", "CBCE", "CECA", "FICTIF", "EPI", "PEV", "UNICEF",
           "IMC", "MDM", "CICR", "ONG", "ID", "RAS", "NB", "OK", "CAS", "HGRB", "HGRK", "CSR", "PS", "CH", "PNLMVE",
           "DPS", "BCZ", "MCZ", "IT", "ITM", "REKO", "RECO", "PTME", "VIH", "TB", "SIDA", "GPS", "SMS", "PDF",
           "MPOX", "EBOLA", "MARBURG", "NON", "OUI", "INCONNU", "DECES", "DÉCÈS", "ALERTE", "URGENT", "PCR", "RDT",
           "TDR", "SpO2", "TASK", "FORCE", "PRÉSIDENTIELLE", "PRESIDENTIELLE", "SYSTÈME", "SYSTEME", "GESTION",
           "INCIDENT", "DÉMONSTRATION", "DEMONSTRATION", "CONFIRMÉ", "CONFIRME", "POSITIF", "NÉGATIF", "NEGATIF",
           "SUSPECT", "PROBABLE", "CONTACT", "CONTACTS", "DOMICILE", "HOPITAL", "HÔPITAL", "MARCHE", "MARCHÉ",
           "EGLISE", "ÉGLISE", "ECOLE", "ÉCOLE", "CENTRE", "SANTE", "SANTÉ", "PROVINCE", "ZONE", "AIRE"}
_TITRES = r"(?:M\.|Mr|Mme|Mlle|Monsieur|Madame|Mademoiselle|Maman|Mama|Papa|Docteur|Dr|Pasteur|Abbé|Chef|Infirmier|Infirmière)"
_MAJ = r"[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ][A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ'-]{2,}"
_TITLE = r"[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ][a-zàâäçéèêëîïôöùûü'-]{2,}"
_RE_MAJ2 = _re.compile(rf"\b{_MAJ}(?:\s+{_MAJ})+\b")                      # MUSUBAO MURATUSI
_RE_MAJ_TITLE = _re.compile(rf"\b{_MAJ}\s+{_TITLE}\b|\b{_TITLE}\s+{_MAJ}\b")   # MUSUBAO Benedicte
_RE_TITRE = _re.compile(rf"\b{_TITRES}\s+(?:{_TITLE}|{_MAJ})(?:\s+(?:{_TITLE}|{_MAJ}))?")   # Maman Benedicte, Dr Kasereka
_PARENTE = r"(?:frère|frere|sœur|soeur|mère|mere|père|pere|fils|fille|oncle|tante|épouse|epouse|époux|epoux|mari|femme|cousin|cousine|voisin|voisine|enfant)"
_RE_PARENTE = _re.compile(rf"\b{_PARENTE}\s+(?:{_TITLE}|{_MAJ})(?:\s+(?:{_TITLE}|{_MAJ}))?")         # frère KAMBALE


def _lieux_connus(case: Case) -> set:
    from core import pyramide
    noms = set()
    try:
        py = pyramide.get()
        for z in py.zones(case.province or ""):
            noms.add(pyramide.norm(z))
        for a in py.aires(case.province or "", case.zs or ""):
            noms.add(pyramide.norm(a))
    except Exception:
        pass
    for x in (case.zs, case.aire_sante, case.province, case.village):
        if x:
            noms.add(pyramide.norm(x))
    for p in case.places:
        for mot in (p.nom or "").split():
            noms.add(pyramide.norm(mot))
    for e in case.events:
        for t in (e.lieu, e.lieu_arrivee):
            for mot in (t or "").split():
                noms.add(pyramide.norm(mot))
    return {n for n in noms if n}


def noms_personnes(case: Case) -> List[Tuple[str, str]]:
    """(où, extrait) des passages de texte libre qui ressemblent à un nom de personne. Repérage prudent :
    plusieurs mots en MAJUSCULES qui ne sont pas des sigles, un mot en majuscules accolé à un prénom,
    ou un titre suivi d'un nom (« Maman Benedicte »). Les noms de lieux connus de la fiche sont ignorés."""
    from core import pyramide
    lieux = _lieux_connus(case)

    def suspect(extrait: str, rx) -> bool:
        mots = [m for m in _re.split(r"[\s'-]+", extrait) if m]
        if rx in (_RE_TITRE, _RE_PARENTE):
            noms = mots[1:]
            return bool(noms) and not all(pyramide.norm(m) in lieux or m.upper() in _SIGLES for m in noms)
        majs = [m for m in mots if m.isupper() and len(m) >= 4 and m not in _SIGLES and pyramide.norm(m) not in lieux]
        return bool(majs)

    textes = []
    for i, e in enumerate(case.events, 1):
        lab = trf("Chronologie, étape {i} ({etape})", i=i, etape=e.titre or tr(e.type))
        textes += [(lab, e.titre), (lab, e.description), (lab, e.personnes)]
    for g in case.contacts:
        ouc = trf("Contacts « {cat} »", cat=g.categorie)
        textes += [(ouc, g.categorie), (ouc, g.lien)]
    for p in case.places:
        textes.append((trf("Lieu « {nom} »", nom=p.nom), p.population))
    textes.append((tr("Note de bas de page"), case.note_pied if case.note_pied != NOTE_PIED_DEFAUT else ""))
    out, vus = [], set()
    for ou, t in textes:
        t = (t or "").strip()
        if not t:
            continue
        # « avecMUSUBAO » : sépare un mot collé à un nom en majuscules
        t2 = _re.sub(r"([a-zàâäçéèêëîïôöùûü])([A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ]{3,})", r"\1 \2", t)
        for rx in (_RE_TITRE, _RE_PARENTE, _RE_MAJ2, _RE_MAJ_TITLE):
            for m in rx.finditer(t2):
                ex = m.group(0).strip()
                if any(ex in d or d in ex for o_, d in vus if o_ == ou):
                    continue
                if suspect(ex, rx) and (ou, ex) not in vus:
                    vus.add((ou, ex))
                    out.append((ou, ex))
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
    texte: str             # texte enregistré dans l'action (français, comme les autres choix)
    priorite: str
    raison: str            # affichée dans la langue de l'utilisateur
    affiche: str = ""      # texte affiché dans la langue de l'utilisateur (vide = texte)


def suggest_actions(case: Case) -> List[Suggestion]:
    out: List[Suggestion] = []
    s = contact_summary(case)

    # anciens libellés : une suggestion écartée sous son ancien nom reste écartée
    anciens = {"Lister tous les contacts": "Boucler tous les contacts"}

    def add(texte, prio, raison, affiche=None):
        rejet = texte in case.suggestions_rejetees or anciens.get(texte) in case.suggestions_rejetees
        if not rejet and all(texte != x.texte for x in out) and not (
                texte in anciens and any(a.texte.strip() == anciens[texte] for a in case.actions)):
            out.append(Suggestion(texte, prio, tr(raison), affiche if affiche is not None else tr(texte)))

    if case.contacts:
        add("Lister tous les contacts", "Urgent", s.phrase)
    unknown = [g.categorie.strip() for g in case.contacts if g.nombre is None and g.categorie.strip()]
    if unknown:
        def low(c: str) -> str:
            return c if c[:2].isupper() else c[0].lower() + c[1:]
        liste = " / ".join(low(c) for c in unknown[:3]) + (" …" if len(unknown) > 3 else "")
        add("Identifier " + liste, "Urgent", "Catégories de contacts non dénombrées", trf("Identifier {liste}", liste=liste))
    if any(e.type == "Exposition" and event_risk(e, case) in ("À investiguer", "Inconnu") for e in case.events) \
            or not any(e.type == "Exposition" for e in case.events):
        add("Reconstituer la source d'exposition", "Urgent", "Source d'exposition non confirmée")
    deadly = case.issue == "Décès" or any(e.type in ("Funérailles", "Enterrement") for e in case.events)
    p = disease_params(case.maladie)
    if case.contacts or deadly:
        add(f"Suivi quotidien {p['suivi_contacts']} jours des contacts", "Important",
            trf("Durée de suivi pour {maladie}", maladie=tr(case.maladie)),
            trf("Suivi quotidien {n} jours des contacts", n=p["suivi_contacts"]))
    if any(e.type == "Enterrement" and not e.securise for e in case.events):
        add("Sensibiliser la communauté (EDS) et suivre les participants aux funérailles", "Urgent",
            "Enterrement non sécurisé")
    bad = [x.site for x in case.ipc if x.statut in ("Non", "Partiel", "Inconnu")]
    if bad:
        add("PCI / décontamination : " + ", ".join(bad), "Urgent", "Sites non décontaminés",
            trf("PCI / décontamination : {sites}", sites=", ".join(bad)))
    for x in case.ipc:
        if x.statut == "Décontaminé" and not (x.date and x.equipe and x.produit):
            add(f"Documenter date / équipe / produit : {x.site}", "Important", "Décontamination incomplètement documentée",
                trf("Documenter date / équipe / produit : {site}", site=x.site))
    delay = lab_delay_hours(case)
    if delay is None and case.labs:
        add("Documenter les délais de laboratoire", "Important", "Heures de prélèvement / résultat manquantes")
    elif delay is not None and delay > p["labo_delai_alerte_h"]:
        add(f"Analyser le délai laboratoire ({delay:.0f} h)", "Important", "Délai supérieur au seuil",
            trf("Analyser le délai laboratoire ({h} h)", h=f"{delay:.0f}"))
    if any(e.transport.lower() == "moto" for e in case.events):
        add("Identifier et suivre les motards", "Urgent", "Transport à moto d'un cas symptomatique ou du corps")
    if coverage_gaps(case):
        add("Documenter les périodes manquantes de la chronologie", "Important", "Trous dans la chronologie")
    hcw = [pl.nom for pl in case.places if pl.type in ("Centre de santé", "Hôpital")]
    if hcw:
        add("Vacciner / suivre le personnel soignant : " + ", ".join(hcw), "Important",
            "Exposition en structure de soins",
            trf("Vacciner / suivre le personnel soignant : {lieux}", lieux=", ".join(hcw)))
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
            missing.append(tr(label))
    if not case.events:
        missing.append(tr("Au moins une étape de chronologie"))
    if not case.places:
        missing.append(tr("Lieux & expositions"))
    if not case.contacts:
        missing.append(tr("Contacts"))
    if not case.ipc:
        missing.append(tr("PCI / décontamination"))
    if not case.labs:
        missing.append(tr("Laboratoire"))
    if any(not e.date_debut for e in case.events):
        missing.append(tr("Dates de certaines étapes"))
    unknown_contacts = sum(1 for g in case.contacts if g.nombre is None)
    if unknown_contacts:
        missing.append(trf("{n} catégorie(s) de contacts non dénombrée(s)", n=unknown_contacts))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.id_cas_source.strip():
        missing.append(tr("ID du cas source (contact connu)"))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.date_contact_source:
        missing.append(tr("Date du dernier contact avec le cas source"))
    sans = personnes_manquantes(case)
    if sans:
        missing.append(trf("Personnes présentes : {n} étape(s) à compléter", n=len(sans)))
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
