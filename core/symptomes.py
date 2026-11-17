"""Symptômes par phase de la maladie, pour l'analyse et la modélisation.

Deux sources, sans rien inventer :
- la liste des symptômes cochés dans la fiche : la phase est celle de leur groupe (sèche, humide, hémorragique) ;
- le texte du parcours (titre et description de chaque étape) : « le malade a développé des céphalées, une asthénie
  physique, des vomissements… ». La phase est celle de l'étape à sa date (rules.event_stage).
Une mention précédée de « sans », « pas de », « absence de » ou « ni » n'est pas comptée.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from config import theme
from core import rules
from core.models import Case

PHASES = [("seche", "Phase sèche"), ("humide", "Phase humide"), ("critique", "Phase critique")]
LIB_PHASE = dict(PHASES) | {"avant": "Avant J0", "symptomatique": "Phase symptomatique", "non_datee": "Non datée"}

# symptôme → motif (texte sans accents, en minuscules)
SYMPTOMES = [
    ("Fièvre", r"fievre|febrile|hyperthermi|corps chaud"),
    ("Céphalées", r"cephal|maux? de tete"),
    ("Asthénie / fatigue", r"asthen|fatigu|faiblesse (generale|physique)|lassitude|malaise general"),
    ("Douleurs articulaires", r"arthralg|douleurs? articul|faiblesse articul|polyarthr"),
    ("Douleurs musculaires / courbatures", r"myalg|douleurs? muscul|courbatur"),
    ("Mal de dos", r"mal (au|de) dos|lombalg|douleurs? (du|au) dos"),
    ("Mal de gorge / dysphagie", r"mal de gorge|odynophag|dysphag|douleurs? (de|a la) gorge"),
    ("Anorexie", r"anorexi|perte d.appetit|inappetence"),
    ("Nausées", r"nausee"),
    ("Vomissements", r"vomi"),
    ("Diarrhée", r"diarrh|selles liquides"),
    ("Douleurs abdominales", r"douleurs? abdomin|mal de ventre|maux de ventre|epigastr"),
    ("Hoquet", r"hoquet"),
    ("Rougeur oculaire", r"rougeur oculaire|yeux rouges|conjonctiv"),
    ("Toux", r"\btoux"),
    ("Douleur thoracique", r"douleurs? thorac"),
    ("Dyspnée / détresse respiratoire", r"dyspn|detresse respiratoire|difficultes? respiratoire|essouffl"),
    ("Éruption cutanée", r"eruption|rash|exanthem"),
    ("Tuméfaction / œdème", r"tumefaction|gonflement|oedeme|œdeme"),
    ("Saignements (non précisés)", r"saign|hemorrag"),
    ("Gingivorragie", r"gingivorr|saignements? (des|aux) gencive"),
    ("Épistaxis", r"epistaxis|saignements? (du|au) nez"),
    ("Méléna", r"melena|selles noires"),
    ("Hématémèse", r"hematemes|vomissements? de sang|vomi du sang"),
    ("Hématurie", r"hematuri|urines? sanglant"),
    ("Saignements aux points d'injection", r"points? d.injection"),
    ("Confusion / trouble de conscience", r"confusion|desorient|obnubil|coma\b|agitation"),
    ("Convulsions", r"convuls"),
    ("Hypotension / choc", r"hypotension|etat de choc"),
    ("Anurie / oligurie", r"anuri|oliguri"),
]
NOMS = [n for n, _m in SYMPTOMES]
_MOTIFS = [(n, re.compile(m)) for n, m in SYMPTOMES]
_NEGATION = re.compile(r"(sans|pas de|pas d'|absence d[e']|ni)\s*$")
# libellés de la liste de la fiche → noms ci-dessus
_COCHES = {"Fièvre": "Fièvre", "Fatigue / asthénie": "Asthénie / fatigue", "Céphalées (maux de tête)": "Céphalées",
           "Douleurs articulaires": "Douleurs articulaires", "Douleurs musculaires": "Douleurs musculaires / courbatures",
           "Courbatures": "Douleurs musculaires / courbatures", "Mal au dos": "Mal de dos",
           "Mal de gorge": "Mal de gorge / dysphagie", "Diarrhée": "Diarrhée", "Nausées": "Nausées",
           "Vomissements": "Vomissements", "Saignements": "Saignements (non précisés)", "Hoquet": "Hoquet",
           "Rougeur oculaire": "Rougeur oculaire", "Méléna": "Méléna", "Hématémèse": "Hématémèse",
           "Gingivorragie": "Gingivorragie", "Épistaxis": "Épistaxis",
           "Saignements aux points d'injection": "Saignements aux points d'injection", "Anorexie": "Anorexie",
           "Douleurs abdominales": "Douleurs abdominales", "Toux": "Toux", "Éruption cutanée": "Éruption cutanée"}


@dataclass
class Mention:
    phase: str            # seche, humide, critique, avant, symptomatique, non_datee
    symptome: str
    date: Optional[date]
    source: str           # « étape 19/07 · Début maladie » ou « liste de la fiche »


def _plat(t: str) -> str:
    return unicodedata.normalize("NFD", (t or "").lower()).encode("ascii", "ignore").decode()


def dans_texte(texte: str) -> List[str]:
    """Symptômes cités dans un texte libre (une mention niée n'est pas comptée)."""
    t = _plat(texte)
    trouves = []
    for nom, rx in _MOTIFS:
        for m in rx.finditer(t):
            if not _NEGATION.search(t[max(0, m.start() - 14):m.start()]):
                trouves.append((m.start(), nom))
                break
    out = [nom for _pos, nom in sorted(trouves)]           # dans l'ordre du texte
    precis = {"Gingivorragie", "Épistaxis", "Méléna", "Hématémèse", "Hématurie", "Saignements aux points d'injection"}
    if "Saignements (non précisés)" in out and precis & set(out):
        out.remove("Saignements (non précisés)")      # « gingivorragie » contient déjà un saignement
    return out


def _phase_etape(ev, ph) -> str:
    st = rules.event_stage(ev, ph) if ph else ""
    return {"infection": "avant", "incubation": "avant", "seche": "seche", "humide": "humide", "critique": "critique",
            "deces": "critique", "symptomes": "symptomatique"}.get(st, "non_datee")


def mentions(c: Case) -> List[Mention]:
    try:
        ph = rules.phases(c)
    except Exception:
        ph = None
    out: List[Mention] = []
    for ev in c.events:
        texte = f"{ev.titre} {ev.description}"
        noms = dans_texte(texte)
        if not noms:
            continue
        phase = _phase_etape(ev, ph)
        src = f"étape {ev.date_debut:%d/%m} · {ev.titre or ev.type}" if ev.date_debut else f"étape · {ev.titre or ev.type}"
        out += [Mention(phase, n, ev.date_debut, src) for n in noms]
    for s in c.symptomes:
        nom = _COCHES.get(s)
        if not nom:
            continue
        if s in theme.HEMORRHAGIC:
            phase, quand = "critique", ph.critique if ph else None
        elif s in theme.SYMPTOMES_HUMIDES:
            phase, quand = "humide", ph.humide if ph else None
        elif s in theme.SYMPTOMES_SECS:
            phase, quand = "seche", ph.j0 if ph else None
        else:
            phase, quand = "non_datee", None
        out.append(Mention(phase, nom, quand, "liste de la fiche"))
    # une seule fois chaque (phase, symptôme) : la première mention datée
    vus: Dict[tuple, Mention] = {}
    for m in sorted(out, key=lambda m: (m.date or date.max)):
        vus.setdefault((m.phase, m.symptome), m)
    return list(vus.values())


def phases_documentees(c: Case, ms: List[Mention]) -> set:
    """Phases pour lesquelles la fiche dit quelque chose : un symptôme, ou une étape datée dans cette phase."""
    try:
        ph = rules.phases(c)
    except Exception:
        ph = None
    doc = {m.phase for m in ms}
    for ev in c.events:
        doc.add(_phase_etape(ev, ph))
    return doc


def frequences(cases: List[Case]) -> Dict[str, List[tuple]]:
    """Par phase : [(symptôme, nombre de cas, cas documentés dans la phase)], du plus fréquent au moins fréquent."""
    cpt: Dict[str, Counter] = defaultdict(Counter)
    base: Counter = Counter()
    for c in cases:
        ms = mentions(c)
        doc = phases_documentees(c, ms)
        for p, _l in PHASES:
            if p in doc:
                base[p] += 1
        for m in ms:
            cpt[m.phase][m.symptome] += 1
    return {p: [(s, n, base[p]) for s, n in cpt[p].most_common()] for p, _l in PHASES}


def par_etape(c: Case) -> List[dict]:
    """Pour chaque étape datée qui cite des symptômes : la date, le jour (J±n), la phase et les symptômes, dans
    l'ordre du texte, sans regroupement (ex. 19/07/2026 → Fièvre ; Asthénie / fatigue ; Céphalées ; Vomissements)."""
    try:
        ph = rules.phases(c)
    except Exception:
        ph = None
    out = []
    for ev in sorted((e for e in c.events if e.date_debut), key=lambda e: e.date_debut):
        noms = dans_texte(f"{ev.titre} {ev.description}")
        if not noms:
            continue
        out.append({"date": ev.date_debut, "jour": rules.relative_day(ev.date_debut, ph.j0) if ph else "",
                    "phase": LIB_PHASE.get(_phase_etape(ev, ph), ""), "etape": ev.titre or ev.type,
                    "symptomes": noms})
    return out
