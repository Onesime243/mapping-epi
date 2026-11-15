"""Rapports par pilier de la riposte (surveillance, contacts, PCI, laboratoire, actions, qualité des données).

Chaque pilier répond à une sélection des questions du « cadre d'analyse et de suivi des mappings MVE » (UMIE-INRB)
auxquelles les données de l'outil permettent de répondre. Les autres questions sont listées en annexe avec la donnée
qui manque. Règle : aucune valeur inventée ; une information non renseignée est comptée à part.
Période : cas notifiés entre deux dates (date de notification, à défaut confirmation, à défaut début des symptômes).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import median
from typing import Dict, List, Optional, Tuple

from config import theme
from core import indicateurs as IND
from core import riposte as R
from core import rules
from core.models import Action, Case

PILIERS_RAPPORT = [
    ("surveillance", "Surveillance et investigation"),
    ("contacts", "Contacts et vaccination"),
    ("pci", "Prévention et contrôle des infections (PCI)"),
    ("labo", "Laboratoire et prise en charge"),
    ("actions", "Actions et coordination"),
    ("qualite", "Qualité des données"),
]

# -- pilier d'une action (champ « Pilier », sinon déduit du texte) -----------------------------------------
_MOTS = [
    ("Vaccination", r"vaccin|anneau"),
    ("PCI", r"d[ée]contam|pci|d[ée]sinfect|\beds\b|enterrement|inhumation|triage|hygi[eè]ne"),
    ("Laboratoire", r"pr[ée]l[eè]v|labo|[ée]chantillon|r[ée]sultat|test"),
    ("Prise en charge", r"isol|\bcte\b|transf[eé]r|prise en charge|traitement|r[ée]f[ée]r|hospitalis"),
    ("Suivi des contacts", r"contact|suivi|lister|listage|boucler"),
    ("Engagement communautaire", r"sensibil|communaut|r[ée]sistan|leader|dialogue|mobilis"),
    ("Surveillance", r"investig|source|alerte|surveill|identifier|recherch|cas suspect|notifi"),
]


def pilier_action(a: Action) -> str:
    if a.pilier in theme.PILIERS:
        return a.pilier
    t = (a.texte or "").lower()
    for nom, motif in _MOTS:
        if re.search(motif, t):
            return nom
    return "Coordination"


# -- structures ---------------------------------------------------------------------------------------------------
@dataclass
class Graphique:
    titre: str
    categories: List[str]
    series: Dict[str, List[float]]
    unite: str = ""
    horizontal: bool = False
    empile: bool = False
    note: str = ""


@dataclass
class Section:
    cle: str
    titre: str
    objectif: str
    kpis: List[Tuple[str, str]] = field(default_factory=list)                 # (libellé, valeur)
    questions: List[Tuple[str, str]] = field(default_factory=list)            # (question, réponse)
    graphiques: List[Graphique] = field(default_factory=list)
    tableaux: List[Tuple[str, List[str], List[list]]] = field(default_factory=list)
    attention: List[str] = field(default_factory=list)


@dataclass
class Rapport:
    debut: date
    fin: date
    province: str
    perimetre: str
    n_cas: int
    n_total: int
    sections: List[Section]
    resume: List[str]
    non_couverts: List[Tuple[str, str, str]]
    genere_le: datetime = field(default_factory=lambda: datetime.now().replace(microsecond=0))


# -- outils ---------------------------------------------------------------------------------------------------------
def _med(v) -> Optional[float]:
    v = [x for x in v if x is not None]
    return median(v) if v else None


def _j(v: Optional[float], unite: str = "j") -> str:
    return "?" if v is None else f"{v:g} {unite}".strip().replace(".", ",")


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f} % ({a}/{b})" if b else "?"


def _ratio(a: int, b: int) -> float:
    return round(100 * a / b, 1) if b else 0.0


def _code(c: Case) -> str:
    return c.code_cas or c.titre_court()


def _isolement(c: Case) -> Optional[date]:
    return R.date_isolement(c)


def selection(cases: List[Case], debut: date, fin: date, province: str = "") -> List[Case]:
    from core import pyramide
    out = []
    for c in cases:
        if c.exemple():
            continue
        if province and pyramide.norm(c.province) != pyramide.norm(province):
            continue
        d, _ = IND.date_notification(c)
        if d and debut <= d <= fin:
            out.append(c)
    return out


def _par_zs(cases: List[Case]) -> Dict[str, List[Case]]:
    g: Dict[str, List[Case]] = defaultdict(list)
    for c in cases:
        g[c.zs or "ZS ?"].append(c)
    return dict(sorted(g.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def _periodes(debut: date, fin: date) -> Tuple[List[date], str]:
    """Jours si la période fait au plus 21 jours, sinon semaines (lundi)."""
    if (fin - debut).days <= 21:
        return [debut + timedelta(days=i) for i in range((fin - debut).days + 1)], "jour"
    d0 = debut - timedelta(days=debut.weekday())
    out, d = [], d0
    while d <= fin:
        out.append(d)
        d += timedelta(days=7)
    return out, "semaine"


# -- piliers -------------------------------------------------------------------------------------------------------
def _surveillance(cases: List[Case], debut: date, fin: date, crees: Dict[str, str], brouillons: int) -> Section:
    from core.links import build_chains, shared_places
    s = Section("surveillance", "Surveillance et investigation",
                "Vérifier que chaque cas est investigué vite et à fond : délais, parcours, sources et chaînes.")
    n = len(cases)
    notif = [(c.date_notification - c.debut_symptomes).days for c in cases if c.date_notification and c.debut_symptomes]
    conf = [(c.date_confirmation - c.date_notification).days for c in cases
            if c.date_confirmation and c.date_notification]
    cons = []
    for c in cases:
        ds = [e.date_debut for e in c.events if e.type == "Soins / consultation" and e.date_debut]
        if ds and c.debut_symptomes:
            cons.append((min(ds) - c.debut_symptomes).days)
    creation = []
    for c in cases:
        d, _ = IND.date_notification(c)
        cr = (crees.get(c.id) or "")[:10]
        if d and cr:
            creation.append((date.fromisoformat(cr) - d).days)
    connus = [c for c in cases if c.contact_connu != "Inconnu"]
    sans_lien = [c for c in connus if c.contact_connu == "Non contact"]
    avec_source = [c for c in cases if c.id_cas_source.strip()]
    ch = build_chains(cases)
    gens = []

    def walk(node, g):
        gens.append(g)
        for k in node.children:
            walk(k, g + 1)
    for r in ch.roots:
        walk(r, 0)
    communs = [p for p in shared_places(cases) if len(p.cases) > 1]
    nb_lieux = [len(c.places) for c in cases]
    types = Counter(p.type or "Autre" for c in cases for p in c.places)
    transport = sum(1 for c in cases if any(e.type == "Déplacement" or e.transport for e in c.events))
    soins = sum(1 for c in cases if any(p.type in ("Centre de santé", "Hôpital") for p in c.places)
                or any(e.type in ("Soins / consultation", "Hospitalisation") for e in c.events))
    zs_n = len({c.zs for c in cases if c.zs})

    s.kpis = [("Cas notifiés", str(n)), ("Zones de santé touchées", str(zs_n)),
              ("Délai médian début → notification", _j(_med(notif))),
              ("Cas sans lien épidémiologique", _pct(len(sans_lien), len(connus)))]
    q = s.questions
    q.append(("Combien de cas confirmés ont été notifiés durant la période ?", f"{n} cas dans {zs_n} zone(s) de santé."))
    q.append(("Quel est le délai entre la notification et la création du mapping ?",
              f"Médiane {_j(_med(creation))} ; créés le jour même ou le lendemain : {_pct(sum(1 for x in creation if x <= 1), len(creation))} ; "
              f"dans les 48 h : {_pct(sum(1 for x in creation if x <= 2), len(creation))} ; après plus de 72 h : "
              f"{_pct(sum(1 for x in creation if x > 3), len(creation))}."))
    q.append(("Combien de mappings sont restés au statut brouillon ?",
              f"{brouillons} brouillon(s) non enregistré(s) dans le périmètre, champs obligatoires manquants."))
    q.append(("Quel est le délai entre le début des symptômes et la première consultation ?",
              f"Médiane {_j(_med(cons))} ({len(cons)} cas avec une consultation datée)."))
    q.append(("Quel est le délai entre le début des symptômes et la notification ?", f"Médiane {_j(_med(notif))} ({len(notif)} cas)."))
    q.append(("Quel est le délai entre la notification et la confirmation ?", f"Médiane {_j(_med(conf))} ({len(conf)} cas)."))
    q.append(("Combien de lieux ont été fréquentés par chaque cas ?",
              f"Médiane {_j(_med(nb_lieux), 'lieu(x)')} par cas ; {sum(nb_lieux)} lieux au total."))
    q.append(("Quels types de lieux sont les plus fréquemment visités ?",
              ", ".join(f"{k} ({v})" for k, v in types.most_common(5)) or "Aucun lieu renseigné."))
    q.append(("Combien de cas ont fréquenté des établissements de soins ?", _pct(soins, n)))
    q.append(("Combien ont utilisé un moyen de transport (déplacement documenté) ?", _pct(transport, n)))
    q.append(("Quels lieux sont fréquentés par plusieurs cas ?",
              "; ".join(f"{p.name} ({len(p.cases)} cas)" for p in communs[:6]) or "Aucun lieu commun détecté."))
    q.append(("Quelle proportion des cas possède une source probable d'infection identifiée ?",
              f"{_pct(len(avec_source), n)} avec un ID de cas source renseigné."))
    q.append(("Combien de cas restent sans lien épidémiologique identifié ?",
              f"{len(sans_lien)} cas « non contact » ; {n - len(connus)} cas au statut inconnu."))
    q.append(("Combien de chaînes de transmission ont pu être reconstruites ?",
              f"{len(ch.roots)} chaîne(s) d'au moins deux cas ; jusqu'à {max(gens) if gens else 0} génération(s) ; "
              f"{len(ch.isolated)} cas isolé(s) sans lien dans l'outil."))

    periodes, pas = _periodes(debut, fin)
    idx = {p: i for i, p in enumerate(periodes)}
    serie = [0] * len(periodes)
    for c in cases:
        d, _ = IND.date_notification(c)
        k = d if pas == "jour" else d - timedelta(days=d.weekday())
        if k in idx:
            serie[idx[k]] += 1
    s.graphiques.append(Graphique(f"Cas notifiés par {pas}", [f"{p:%d/%m}" for p in periodes], {"Cas": serie}, "cas"))
    z = _par_zs(cases)
    zn = list(z)[:12]
    s.graphiques.append(Graphique("Délai médian début des symptômes → notification par zone de santé",
                                  zn, {"Jours": [_med([(c.date_notification - c.debut_symptomes).days for c in z[k]
                                                       if c.date_notification and c.debut_symptomes]) or 0 for k in zn]},
                                  "jours", horizontal=True,
                                  note="0 = délai non calculable (dates manquantes)"))
    if types:
        tt = types.most_common(8)
        s.graphiques.append(Graphique("Types de lieux fréquentés", [k for k, _ in tt], {"Lieux": [v for _, v in tt]},
                                      "lieux", horizontal=True))
    if _med(notif) is not None and _med(notif) > 3:
        s.attention.append(f"Délai médian de notification de {_j(_med(notif))} : au-delà de 3 jours, le cas a eu le temps "
                           "d'exposer de nombreux contacts.")
    if connus and len(sans_lien) / len(connus) > 0.25:
        s.attention.append(f"{len(sans_lien)} cas sans lien épidémiologique : chaînes invisibles à investiguer.")
    if brouillons:
        s.attention.append(f"{brouillons} fiche(s) encore en brouillon : investigations non finalisées.")
    return s


def _contacts(cases: List[Case]) -> Section:
    s = Section("contacts", "Contacts et vaccination",
                "Mesurer l'exhaustivité du listage, la part suivie et la protection des contacts par la vaccination.")
    groupes = [(c, g) for c in cases for g in c.contacts]
    listes = [g.nombre for _c, g in groupes if g.nombre is not None]
    par_cas = [sum(g.nombre for g in c.contacts if g.nombre is not None) for c in cases if c.contacts]
    haut = sum(g.nombre for _c, g in groupes if g.nombre is not None and g.risque in ("Haut", "Très haut"))
    sans_risque = sum(1 for _c, g in groupes if g.risque in ("", "Inconnu"))
    non_den = sum(1 for _c, g in groupes if g.nombre is None)
    ls = [(g.nombre, g.suivis) for _c, g in groupes if g.nombre is not None and g.suivis is not None]
    lv = [(g.nombre, g.vaccines) for _c, g in groupes if g.nombre is not None and g.vaccines is not None]
    cat = Counter()
    for _c, g in groupes:
        if g.nombre is not None:
            cat[g.categorie or "Autre"] += g.nombre
    anneau = [(c.date_debut_anneau - c.date_confirmation).days for c in cases
              if c.date_debut_anneau and c.date_confirmation and c.date_debut_anneau >= c.date_confirmation]
    vac_cas = [c for c in cases if c.vaccine != "Inconnu"]
    s.kpis = [("Contacts listés", str(sum(listes))), ("Médiane par cas", _j(_med(par_cas), "")),
              ("Contacts suivis", _pct(sum(b for _a, b in ls), sum(a for a, _b in ls))),
              ("Contacts vaccinés", _pct(sum(b for _a, b in lv), sum(a for a, _b in lv)))]
    q = s.questions
    q.append(("Combien de contacts ont été identifiés par cas ?",
              f"Médiane {_j(_med(par_cas), '')} contact(s) par cas ; {sum(listes)} contacts listés au total."))
    q.append(("Combien de contacts sont classés à haut risque ?", f"{haut} contacts dans des groupes à risque haut ou très haut."))
    q.append(("Combien de groupes de contacts n'ont pas encore de classification de risque ?", f"{sans_risque} groupe(s)."))
    q.append(("Combien de catégories de contacts restent non dénombrées ?", f"{non_den} groupe(s) au nombre inconnu (« ? »)."))
    q.append(("Où les contacts ont-ils été identifiés (ménages, soins, transports, lieux communautaires) ?",
              ", ".join(f"{k} : {v}" for k, v in cat.most_common(6)) or "Aucun contact dénombré."))
    q.append(("Quel pourcentage des contacts listés est suivi ?",
              f"{_pct(sum(b for _a, b in ls), sum(a for a, _b in ls))} (groupes où le nombre listé et le nombre suivi sont renseignés)."))
    q.append(("Quel est le taux de vaccination parmi les contacts listés ?",
              f"{_pct(sum(b for _a, b in lv), sum(a for a, _b in lv))} (colonne « Vaccinés »)."))
    q.append(("Quel est le délai entre la confirmation et le début de la vaccination de l'anneau ?",
              f"Médiane {_j(_med(anneau))} ; {_pct(len(anneau), len(cases))} des cas ont un anneau daté."))
    q.append(("Combien de cas étaient vaccinés ?",
              f"{_pct(sum(1 for c in vac_cas if c.vaccine == 'Oui'), len(vac_cas))} parmi les cas au statut renseigné."))
    if cat:
        cc = cat.most_common(8)
        s.graphiques.append(Graphique("Contacts listés par catégorie", [k for k, _ in cc], {"Contacts": [v for _, v in cc]},
                                      "contacts", horizontal=True))
    z = _par_zs(cases)
    zn = list(z)[:12]
    suiv, vacc = [], []
    for k in zn:
        a = [(g.nombre, g.suivis) for c in z[k] for g in c.contacts if g.nombre is not None and g.suivis is not None]
        b = [(g.nombre, g.vaccines) for c in z[k] for g in c.contacts if g.nombre is not None and g.vaccines is not None]
        suiv.append(_ratio(sum(y for _x, y in a), sum(x for x, _y in a)))
        vacc.append(_ratio(sum(y for _x, y in b), sum(x for x, _y in b)))
    if zn:
        s.graphiques.append(Graphique("Contacts suivis et vaccinés par zone de santé (%)", zn,
                                      {"Suivis": suiv, "Vaccinés": vacc}, "%"))
    if ls and sum(b for _a, b in ls) / max(1, sum(a for a, _b in ls)) < 0.9:
        s.attention.append("Moins de 90 % des contacts listés sont suivis : risque de cas secondaires non détectés.")
    if non_den:
        s.attention.append(f"{non_den} groupe(s) de contacts non dénombré(s) : listage incomplet.")
    return s


def _pci(cases: List[Case]) -> Section:
    s = Section("pci", "Prévention et contrôle des infections (PCI)",
                "Vérifier que chaque site à risque est évalué, décontaminé et documenté, et que les enterrements sont sécurisés.")
    sites = [(c, x) for c in cases for x in c.ipc]
    st = Counter(x.statut or "Inconnu" for _c, x in sites)
    delais = [(x.date - c.date_confirmation).days for c, x in sites
              if x.statut == "Décontaminé" and x.date and c.date_confirmation]
    complets = sum(1 for _c, x in sites if x.date and x.equipe.strip() and x.produit.strip())
    lieux = sum(len(c.places) for c in cases)
    dc = [c for c in cases if c.issue == "Décès"]
    ent = [(c, R.enterrement_securise(c)) for c in dc]
    ent = [(c, v) for c, v in ent if v is not None]
    restants = [f"{x.site} ({c.zs})" for c, x in sites if x.statut in ("Non", "Partiel", "Inconnu")]
    s.kpis = [("Sites PCI documentés", str(len(sites))), ("Décontaminés", _pct(st.get("Décontaminé", 0), len(sites))),
              ("Délai médian confirmation → décontamination", _j(_med(delais))),
              ("Enterrements sécurisés", _pct(sum(1 for _c, v in ent if v), len(ent)))]
    q = s.questions
    q.append(("Combien de lieux ont été identifiés, et combien de sites ont une évaluation PCI ?",
              f"{lieux} lieux d'exposition ; {len(sites)} sites PCI documentés."))
    q.append(("Combien de décontaminations ont été réalisées ?", f"{st.get('Décontaminé', 0)} sites décontaminés ; "
              f"{st.get('Partiel', 0)} partiels ; {st.get('Non', 0)} non faits."))
    q.append(("Quel est le taux de réalisation des décontaminations ?", _pct(st.get("Décontaminé", 0), len(sites))))
    q.append(("Combien de lieux ont un statut PCI inconnu ?", f"{st.get('Inconnu', 0)} site(s)."))
    q.append(("Quel est le délai médian entre la confirmation et l'intervention PCI ?",
              f"{_j(_med(delais))} ({len(delais)} décontaminations datées) ; dans les 24 h : "
              f"{_pct(sum(1 for x in delais if x <= 1), len(delais))}."))
    q.append(("Combien d'interventions disposent d'une date, d'une équipe et d'un produit documentés ?", _pct(complets, len(sites))))
    q.append(("Quels sites présentent encore un risque non maîtrisé ?", "; ".join(restants[:10]) or "Aucun site en attente."))
    q.append(("Les enterrements des cas décédés ont-ils été dignes et sécurisés ?",
              f"{_pct(sum(1 for _c, v in ent if v), len(ent))} parmi les décès avec une étape « Enterrement »."))
    ordre = ["Décontaminé", "Partiel", "Non", "Inconnu"]
    s.graphiques.append(Graphique("État des sites PCI", ordre, {"Sites": [st.get(k, 0) for k in ordre]}, "sites"))
    z = _par_zs(cases)
    zn = [k for k in z if any(c.ipc for c in z[k])][:12]
    if zn:
        series = {k: [sum(1 for c in z[n] for x in c.ipc if (x.statut or "Inconnu") == k) for n in zn] for k in ordre}
        s.graphiques.append(Graphique("Sites PCI par zone de santé et par état", zn, series, "sites", empile=True))
    if restants:
        s.attention.append(f"{len(restants)} site(s) non décontaminé(s), partiel(s) ou inconnu(s) : à traiter en priorité.")
    if ent and any(not v for _c, v in ent):
        s.attention.append("Des enterrements n'ont pas été sécurisés : risque élevé de transmission aux funérailles.")
    return s


def _labo(cases: List[Case]) -> Section:
    s = Section("labo", "Laboratoire et prise en charge",
                "Mesurer les délais diagnostiques, l'isolement et le parcours de soins avant la prise en charge.")
    delais_h = []
    for c in cases:
        h = rules.lab_delay_hours(c)
        if h is not None:
            delais_h.append(round(h))
    preleves = sum(1 for c in cases if c.labs)
    iso = [(c, _isolement(c)) for c in cases]
    iso_d = [(i - c.debut_symptomes).days for c, i in iso if i and c.debut_symptomes]
    avant = sum(1 for c, i in iso if i and c.date_confirmation and i < c.date_confirmation)
    apres = sum(1 for c, i in iso if i and c.date_confirmation and i >= c.date_confirmation)
    consult = []
    for c, i in iso:
        if i:
            consult.append(sum(1 for e in c.events if e.type == "Soins / consultation" and e.date_debut and e.date_debut <= i))
    plusieurs = sum(1 for x in consult if x >= 2)
    dc = [c for c in cases if c.issue == "Décès"]
    com = [c for c in dc if R.deces_communautaire(c)]
    seuil = 48
    s.kpis = [("Cas prélevés", _pct(preleves, len(cases))), ("Délai médian prélèvement → résultat", _j(_med(delais_h), "h")),
              ("Délai médian début → isolement", _j(_med(iso_d))), ("Décès communautaires", _pct(len(com), len(dc)))]
    q = s.questions
    q.append(("Combien de cas ont été prélevés ?", _pct(preleves, len(cases))))
    q.append(("Quel est le délai entre le prélèvement et le résultat ?",
              f"Médiane {_j(_med(delais_h), 'h')} ; en {seuil} h ou moins : {_pct(sum(1 for x in delais_h if x <= seuil), len(delais_h))}."))
    q.append(("Quel est le délai entre le début des symptômes et l'isolement ?",
              f"Médiane {_j(_med(iso_d))} ; isolés en 3 jours ou moins : {_pct(sum(1 for x in iso_d if x <= 3), len(iso_d))}."))
    q.append(("Combien de cas ont été isolés avant ou après la confirmation ?", f"{avant} avant, {apres} après la confirmation."))
    q.append(("Quel est le nombre médian de consultations avant l'isolement ?",
              f"{_j(_med(consult), '')} ; {plusieurs} cas ont consulté au moins deux fois avant d'être isolés."))
    q.append(("Combien de décès sont survenus dans la communauté, sans hospitalisation ?", _pct(len(com), len(dc))))
    if delais_h:
        bornes = [(0, 24, "≤ 24 h"), (25, 48, "25 à 48 h"), (49, 72, "49 à 72 h"), (73, 10 ** 6, "> 72 h")]
        s.graphiques.append(Graphique("Délai prélèvement → résultat", [b[2] for b in bornes],
                                      {"Cas": [sum(1 for x in delais_h if b[0] <= x <= b[1]) for b in bornes]}, "cas"))
    if iso_d:
        b2 = [(-10 ** 6, 1, "≤ 1 j"), (2, 3, "2 à 3 j"), (4, 7, "4 à 7 j"), (8, 10 ** 6, "> 7 j")]
        s.graphiques.append(Graphique("Délai début des symptômes → isolement", [b[2] for b in b2],
                                      {"Cas": [sum(1 for x in iso_d if b[0] <= x <= b[1]) for b in b2]}, "cas"))
    if delais_h and _med(delais_h) > seuil:
        s.attention.append(f"Délai médian de résultat de {_j(_med(delais_h), 'h')} : au-delà de {seuil} h.")
    if com:
        s.attention.append(f"{len(com)} décès communautaire(s) : cas détectés trop tard.")
    if plusieurs:
        s.attention.append(f"{plusieurs} cas ont consulté plusieurs structures avant l'isolement : exposition des soignants.")
    return s


def _actions(cases: List[Case], ref: date) -> Section:
    s = Section("actions", "Actions et coordination",
                "Suivre ce qui a été prescrit à partir des mappings : responsable, échéance, réalisation et retards, par pilier.")
    acts = [(c, a) for c in cases for a in c.actions if a.texte.strip()]
    n = len(acts)
    resp = sum(1 for _c, a in acts if a.responsable.strip())
    ech = sum(1 for _c, a in acts if a.echeance)
    faites = sum(1 for _c, a in acts if a.statut == "Fait")
    cours = sum(1 for _c, a in acts if a.statut == "En cours")
    retard = [(c, a) for c, a in acts if a.statut != "Fait" and a.echeance and a.echeance < ref]
    crit = [(c, a) for c, a in acts if a.priorite == "Urgent" and a.statut != "Fait"]
    crit_sans = sum(1 for _c, a in crit if not a.responsable.strip())
    cas_crit = len({c.id for c, _a in crit})
    par_p = defaultdict(lambda: Counter())
    for _c, a in acts:
        par_p[pilier_action(a)][a.statut] += 1
    s.kpis = [("Actions prescrites", str(n)), ("Réalisées", _pct(faites, n)), ("En retard", str(len(retard))),
              ("Urgentes ouvertes", str(len(crit)))]
    q = s.questions
    q.append(("Combien d'actions ont été générées, et combien en moyenne par cas ?",
              f"{n} actions ; {n / len(cases):.1f} par cas." if cases else "Aucun cas."))
    q.append(("Combien d'actions concernent chaque pilier ?",
              ", ".join(f"{p} : {sum(v.values())}" for p, v in sorted(par_p.items(), key=lambda kv: -sum(kv[1].values())))
              or "Aucune action."))
    q.append(("Combien d'actions ont un responsable identifié ?", _pct(resp, n)))
    q.append(("Combien ont une échéance définie ?", _pct(ech, n)))
    q.append(("Combien sont en attente, en cours ou réalisées ?", f"{n - faites - cours} à faire, {cours} en cours, {faites} faites."))
    q.append(("Combien sont en retard ?", f"{len(retard)} action(s) non faites dont l'échéance est dépassée."))
    q.append(("Combien d'actions critiques (urgentes) sont ouvertes, et combien sans responsable ?",
              f"{len(crit)} ouvertes, dont {crit_sans} sans responsable."))
    q.append(("Combien de cas présentent au moins une action critique non résolue ?", _pct(cas_crit, len(cases))))
    sans_preuve = sum(1 for _c, a in acts if a.statut == "Fait" and not a.preuve.strip())
    verif = sum(1 for _c, a in acts if a.statut == "Fait" and a.valide_par.strip())
    bloq = Counter(a.obstacle for _c, a in acts if a.statut != "Fait" and a.obstacle)
    q.append(("Combien d'actions réalisées ont été vérifiées par un superviseur ?", _pct(verif, faites)))
    q.append(("Combien d'actions sont déclarées réalisées sans preuve ?", f"{sans_preuve} sur {faites} réalisées."))
    q.append(("Quels obstacles bloquent ou retardent les actions (sécurité, communauté, intrants…) ?",
              ", ".join(f"{k} : {v}" for k, v in bloq.most_common()) or "Aucun obstacle signalé."))
    piliers = [p for p in theme.PILIERS if p in par_p]
    if piliers:
        s.graphiques.append(Graphique("Actions par pilier et par statut", piliers,
                                      {st: [par_p[p].get(st, 0) for p in piliers] for st in theme.ACTION_STATUS_CHOICES},
                                      "actions", horizontal=True, empile=True))
    if retard:
        rows = sorted(retard, key=lambda x: x[1].echeance)[:15]
        s.tableaux.append(("Actions en retard (les plus anciennes)", ["Cas", "ZS", "Action", "Pilier", "Responsable", "Échéance"],
                           [[_code(c), c.zs, a.texte, pilier_action(a), a.responsable or "à désigner",
                             f"{a.echeance:%d/%m/%Y}"] for c, a in rows]))
        s.attention.append(f"{len(retard)} action(s) en retard à relancer en réunion de coordination.")
    if crit_sans:
        s.attention.append(f"{crit_sans} action(s) urgente(s) sans responsable.")
    return s


def _qualite(cases: List[Case], brouillons: int, doublons: int) -> Section:
    s = Section("qualite", "Qualité des données",
                "S'assurer que les mappings sont assez complets et cohérents pour orienter les opérations.")
    comp = [rules.completeness(c) for c in cases]
    scores = [x[0] for x in comp]
    manq = Counter(m.split(" :")[0] for _s, ms in comp for m in ms)
    incoh = Counter()
    for c in cases:
        for i in rules.check_consistency(c):
            if i.niveau == "erreur":
                incoh[c.id] += 1
    lieux = [p for c in cases for p in c.places]
    geo = sum(1 for p in lieux if p.lat is not None and p.lon is not None)
    s.kpis = [("Complétude moyenne", f"{sum(scores) / len(scores):.0f} %" if scores else "?"),
              ("Fiches complètes à 90 % ou plus", _pct(sum(1 for x in scores if x >= 90), len(scores))),
              ("Fiches avec incohérence", _pct(len(incoh), len(cases))), ("Lieux géolocalisés", _pct(geo, len(lieux)))]
    q = s.questions
    q.append(("Quel est le taux moyen de complétude des mappings ?", s.kpis[0][1]))
    q.append(("Combien de mappings ont une complétude supérieure ou égale à 90 % ?", s.kpis[1][1]))
    q.append(("Quelles variables sont le plus souvent manquantes ?",
              ", ".join(f"{k} ({v})" for k, v in manq.most_common(6)) or "Aucune."))
    q.append(("Combien de fiches présentent des dates incohérentes ?", f"{len(incoh)} fiche(s) avec au moins une incohérence bloquante."))
    q.append(("Quelle proportion des lieux est géolocalisée ?", s.kpis[3][1]))
    q.append(("Combien de cas disposent de plusieurs mappings potentiellement dupliqués ?", f"{doublons} paire(s) de doublons possibles."))
    q.append(("Combien de mappings sont restés en brouillon ?", f"{brouillons}."))
    if manq:
        mm = manq.most_common(8)
        s.graphiques.append(Graphique("Éléments le plus souvent manquants", [k for k, _ in mm], {"Fiches": [v for _, v in mm]},
                                      "fiches", horizontal=True))
    z = _par_zs(cases)
    zn = list(z)[:12]
    if zn:
        s.graphiques.append(Graphique("Complétude moyenne par zone de santé (%)", zn,
                                      {"Complétude": [round(sum(rules.completeness(c)[0] for c in z[k]) / len(z[k])) for k in zn]},
                                      "%"))
    if scores and sum(scores) / len(scores) < 80:
        s.attention.append("Complétude moyenne sous 80 % : renforcer la supervision des fiches.")
    if incoh:
        s.attention.append(f"{len(incoh)} fiche(s) avec des dates incohérentes à corriger.")
    return s


NON_COUVERTS = [
    ("A. Couverture", "Combien de mappings ont été validés, rejetés ou soumis à investigation complémentaire ?",
     "Circuit de validation par un superviseur"),
    ("A. Couverture", "Combien de cas confirmés de la liste linéaire n'ont pas de mapping ?", "Rapprochement avec la liste linéaire"),
    ("C. Délais", "Délais alerte → validation → investigation", "Dates d'alerte et de validation de l'alerte"),
    ("D. Mobilité", "Corridors de mobilité entre zones et provinces", "Zone de santé de chaque lieu visité"),
    ("E et F. Contacts", "Suivi quotidien sur 21 jours, contacts perdus de vue, J7 / J14 / J21", "Registre nominatif de suivi (Go.Data)"),
    ("G. PCI", "Vérification des décontaminations par un superviseur, preuves, réévaluations", "Validation et pièces justificatives"),
    ("H. Investigation", "Investigations complémentaires recommandées, démarrées, achevées", "Registre des investigations"),
    ("J. Communauté", "Résistances communautaires, motifs, résolution", "Registre des incidents communautaires"),
    ("K. Vaccination", "Éligibilité, refus, indisponibilité du vaccin", "Données nominatives de vaccination"),
    ("L. Coordination", "Notifications interzones émises, reçues, traitées", "Registre des notifications interzones"),
    ("S. Impact", "Coût par investigation, par action PCI, par contact suivi", "Données de coût"),
]


def construire(cases_perimetre: List[Case], debut: date, fin: date, province: str = "", piliers: Optional[List[str]] = None,
               perimetre: str = "", crees: Optional[Dict[str, str]] = None, brouillons: int = 0) -> Rapport:
    from core.doublons import doublons as find_dbl
    cases = selection(cases_perimetre, debut, fin, province)
    total = len([c for c in cases_perimetre if not c.exemple()])
    piliers = piliers or [k for k, _ in PILIERS_RAPPORT]
    secs: List[Section] = []
    for k, _t in PILIERS_RAPPORT:
        if k not in piliers:
            continue
        if k == "surveillance":
            secs.append(_surveillance(cases, debut, fin, crees or {}, brouillons))
        elif k == "contacts":
            secs.append(_contacts(cases))
        elif k == "pci":
            secs.append(_pci(cases))
        elif k == "labo":
            secs.append(_labo(cases))
        elif k == "actions":
            secs.append(_actions(cases, fin))
        elif k == "qualite":
            secs.append(_qualite(cases, brouillons, len(find_dbl(cases))))
    resume = [f"{len(cases)} cas notifiés du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}"
              f"{' en ' + province if province else ''} ({total} cas au total dans le périmètre)."]
    for s_ in secs:
        resume += s_.attention[:1]
    if len(resume) == 1:
        resume.append("Aucun point d'attention majeur sur la période.")
    return Rapport(debut, fin, province, perimetre, len(cases), total, secs, resume[:7], NON_COUVERTS)
