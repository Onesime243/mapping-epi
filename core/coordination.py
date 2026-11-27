"""Mapping Épi 2.0 : coordination et espaces des piliers.

- command_center : 6 indicateurs et carte de chaleur zones × piliers (onglet Analyse du tableau de bord) ;
- centre_actions : actions des fiches en colonnes, dont « Faite · à valider » (onglet À traiter) ;
- pages des piliers (structure commune rendue par web/templates/pilier.html) : goulots de la surveillance,
  concordance Mapping Épi × DHIS2, vaccination, psychosocial (agrégats seulement), services essentiels, PoE / PoC.

Règle de toujours : une donnée inconnue reste « ND » (jamais 0) ; un pourcentage sans dénominateur n'est pas calculé.
Tout est calculé depuis les fiches ; seuls les rapports journaliers PoE / PoC sont saisis à part (core/poe.py).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Dict, List, Optional, Tuple

from config import theme
from core import rules
from core.langue import tr, trf
from core.lieux import case_label
from core.models import Case
from core.piliers import pilier_action

SEUIL_ROUGE, SEUIL_VERT = 60, 85


# ---------------------------------------------------------------------------------------------------- utilitaires
def _pct(n: Optional[float], d: Optional[float]) -> Optional[float]:
    return round(100 * n / d, 1) if n is not None and d else None


def _ton(p: Optional[float], bas: bool = False) -> str:
    """ok (vert) / al (ambre) / re (rouge) / nd (gris : non documenté)."""
    if p is None:
        return "nd"
    if bas:
        return "ok" if p <= 1 else ("al" if p <= 2 else "re")
    return "re" if p < SEUIL_ROUGE else ("al" if p < SEUIL_VERT else "ok")


def _en() -> bool:
    from core.langue import actuelle
    return actuelle() == "en"


def _nombre(v: float) -> str:
    s = f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"
    return s if _en() else s.replace(".", ",")


def _fmt_pct(p: Optional[float]) -> str:
    return "ND" if p is None else _nombre(p) + ("%" if _en() else " %")


def _fmt_j(v: Optional[float]) -> str:
    return "ND" if v is None else _nombre(v) + (" d" if _en() else " j")


def _som(vals) -> Optional[int]:
    v = [x for x in vals if x is not None]
    return sum(v) if v else None


def _med(v) -> Optional[float]:
    v = [x for x in v if x is not None]
    return round(median(v), 1) if v else None


def _j(a: Optional[date], b: Optional[date]) -> Optional[int]:
    return (b - a).days if a and b else None


def _zs(c: Case) -> str:
    return c.zs or "?"


def _par_zs(cases: List[Case]) -> Dict[str, List[Case]]:
    d: Dict[str, List[Case]] = defaultdict(list)
    for c in cases:
        d[_zs(c)].append(c)
    return dict(sorted(d.items()))


def kpi(t: str, v: str, d: str = "", ton: str = "") -> dict:
    return {"t": t, "v": v, "d": d, "ton": ton}


def barres(titre: str, lignes: List[Tuple[str, Optional[float], str, str]], aide: str = "", large: bool = False) -> dict:
    """lignes : (libellé, valeur ou None, texte affiché, ton)."""
    vmax = max([v for _l, v, _t, _c in lignes if v] + [1])
    return {"type": "barres", "titre": titre, "aide": aide, "large": large,
            "lignes": [{"l": l, "w": (100 * v / vmax) if v else 0, "txt": t, "ton": c} for l, v, t, c in lignes]}


def table(titre: str, entetes: List[str], lignes: List[list], aide: str = "", large: bool = True, liens=None) -> dict:
    """cellule : texte, ou (texte, ton) pour une pastille colorée."""
    rows = []
    for i, l in enumerate(lignes):
        rows.append({"cells": [c if isinstance(c, tuple) else (c, "") for c in l],
                     "lien": liens[i] if liens else None})
    return {"type": "table", "titre": titre, "aide": aide, "large": large, "entetes": entetes, "lignes": rows}


def page(titre: str, sous: str, note: List[str], kpis: List[dict], sections: List[dict]) -> dict:
    return {"titre": titre, "sous": sous, "note": note, "kpis": kpis, "sections": sections}


# ----------------------------------------------------------------------------------------- indicateurs par fiche
def contacts_listes(c: Case) -> Optional[int]:
    return _som(g.nombre for g in c.contacts)


def _suivi(cs: List[Case]) -> Optional[float]:
    paires = [(g.suivis, g.nombre) for c in cs for g in c.contacts if g.suivis is not None and g.nombre]
    return _pct(sum(min(s, n) for s, n in paires), sum(n for _s, n in paires)) if paires else None


def _pci(cs: List[Case]) -> Optional[float]:
    sites = [s for c in cs for s in c.ipc if s.site.strip()]
    return _pct(sum(1 for s in sites if s.statut == "Décontaminé"), len(sites)) if sites else None


def _vacc(cs: List[Case]) -> Optional[float]:
    paires = [(g.vaccines, g.eligibles if g.eligibles else g.nombre) for c in cs for g in c.contacts
              if g.vaccines is not None and (g.eligibles or g.nombre)]
    return _pct(sum(min(v, d) for v, d in paires), sum(d for _v, d in paires)) if paires else None


def _iso(cs: List[Case]) -> Optional[float]:
    d = [_j(c.date_confirmation, c.date_isolement) for c in cs]
    d = [x for x in d if x is not None]
    return _pct(sum(1 for x in d if x <= 1), len(d)) if d else None


def _actions_ok(cs: List[Case], ref: date) -> Tuple[Optional[float], int, int]:
    acts = [a for c in cs for a in c.actions if a.texte.strip()]
    retard = sum(1 for a in acts if a.statut != "Fait" and a.echeance and a.echeance < ref)
    return (_pct(len(acts) - retard, len(acts)) if acts else None), len(acts), retard


def _completude(cs: List[Case]) -> Optional[float]:
    v = [rules.completeness(c)[0] for c in cs]
    return round(sum(v) / len(v), 1) if v else None


COLONNES_HEAT = ["Fiches complètes", "Contacts suivis", "PCI : sites décontaminés", "Vaccination des contacts",
                 "Isolement ≤ 1 j après confirmation", "Actions à jour"]


# ------------------------------------------------------------------------------------------------ command center
def command_center(cases: List[Case], ref: Optional[date] = None) -> dict:
    ref = ref or date.today()
    listes = _som(contacts_listes(c) for c in cases)
    paires = [(contacts_listes(c), contacts_dhis2(c)) for c in cases]
    paires = [(m, d) for m, d in paires if m is not None and d is not None]
    conc = _pct(sum(d for _m, d in paires), sum(m for m, _d in paires)) if paires else None
    ecart = sum(m - d for m, d in paires) if paires else None
    a_ok, n_act, n_ret = _actions_ok(cases, ref)
    comp = _completude(cases)
    sui = _suivi(cases)
    kpis = [kpi(tr("Cas (fiches)"), str(len(cases)), tr("dans la période et le périmètre")),
            kpi(tr("Complétude des fiches"), _fmt_pct(comp), tr("cible ≥ 95 %"), _ton(comp)),
            kpi(tr("Contacts listés"), "ND" if listes is None else f"{listes:,}".replace(",", " "),
                trf("suivis : {p}", p=_fmt_pct(sui)), _ton(sui)),
            kpi(tr("Concordance DHIS2"), _fmt_pct(conc), (trf("écart : {n}", n=ecart) if ecart is not None
                                                           else tr("nombre DHIS2 non saisi")), _ton(conc)),
            kpi(tr("Actions"), str(n_act), tr("tous piliers")),
            kpi(tr("Actions dans les délais"), _fmt_pct(a_ok), trf("{n} en retard", n=n_ret), _ton(a_ok))]
    zones = []
    for z, cs in _par_zs(cases).items():
        vals = [_completude(cs), _suivi(cs), _pci(cs), _vacc(cs), _iso(cs), _actions_ok(cs, ref)[0]]
        zones.append({"zs": z, "n": len(cs), "cells": [{"txt": _fmt_pct(v), "ton": _ton(v)} for v in vals]})
    ec = []
    for z, cs in _par_zs(cases).items():
        p = [(contacts_listes(c), contacts_dhis2(c)) for c in cs]
        p = [(m, d) for m, d in p if m is not None and d is not None]
        if p:
            e = sum(m - d for m, d in p)
            ec.append((z, abs(e), f"{e:+d}", "re" if e > 0 else "bl"))
    issues = Counter(c.issue or "Inconnu" for c in cases)
    ton_issue = {"Guéri": "ok", "Vivant": "ok", "En traitement": "bl", "Décès": "re", "Inconnu": "nd"}
    return {"kpis": kpis, "colonnes": [tr(x) for x in COLONNES_HEAT], "zones": zones,
            "ecarts": barres(tr("Écarts de listing des contacts (fiche − DHIS2)"), sorted(ec, key=lambda x: -x[1]),
                             tr("fiches dont le nombre de contacts est connu dans le mapping et dans DHIS2")),
            "issues": barres(tr("État des cas"), [(tr(k), n, str(n), ton_issue.get(k, "nd"))
                                                  for k, n in issues.most_common()])}


# ---------------------------------------------------------------------------------------------- centre des actions
COLONNES_ACTIONS = [("afaire", "À faire"), ("encours", "En cours"), ("retard", "En retard"),
                    ("avalider", "Faite · à valider"), ("validee", "Validée")]


def centre_actions(cases: List[Case], ref: Optional[date] = None, pilier: str = "") -> dict:
    ref = ref or date.today()
    cols: Dict[str, list] = {k: [] for k, _l in COLONNES_ACTIONS}
    piliers = Counter()
    for c in cases:
        for a in c.actions:
            if not a.texte.strip():
                continue
            p = pilier_action(a)
            piliers[p] += 1
            if pilier and p != pilier:
                continue
            if a.statut == "Fait":
                k = "validee" if a.valide_par.strip() else "avalider"
            elif a.echeance and a.echeance < ref:
                k = "retard"
            else:
                k = "encours" if a.statut == "En cours" else "afaire"
            cols[k].append({"cid": c.id, "code": case_label(c), "zs": _zs(c), "pilier": p, "texte": a.texte,
                            "priorite": a.priorite, "responsable": a.responsable or "?",
                            "echeance": a.echeance, "retard": (ref - a.echeance).days if k == "retard" else None,
                            "preuve": a.preuve, "valide_par": a.valide_par})
    prio = {"Urgent": 0, "Important": 1}
    for k in cols:
        cols[k].sort(key=lambda x: (prio.get(x["priorite"], 2), x["echeance"] or date.max))
    return {"colonnes": [(k, tr(l), cols[k]) for k, l in COLONNES_ACTIONS], "piliers": piliers.most_common(),
            "pilier": pilier}


# ------------------------------------------------------------------------------------------------ goulots
def goulots(cases: List[Case], ref: Optional[date] = None) -> dict:
    ref = ref or date.today()
    n = len(cases)
    prelev = {c.id: min((l.prelevement.date() for l in c.labs if l.prelevement), default=None) for c in cases}
    resul = {c.id: min((l.resultat_le.date() for l in c.labs if l.resultat_le), default=None) for c in cases}
    chaine = [(tr("Cas (fiches)"), n), (tr("Alerte datée"), sum(1 for c in cases if c.date_alerte)),
              (tr("Investigation datée"), sum(1 for c in cases if c.date_investigation)),
              (tr("Prélèvement daté"), sum(1 for c in cases if prelev[c.id])),
              (tr("Résultat daté"), sum(1 for c in cases if resul[c.id])),
              (tr("Confirmation datée"), sum(1 for c in cases if c.date_confirmation)),
              (tr("Isolement effectif daté"), sum(1 for c in cases if c.date_isolement))]
    etapes = [("Symptômes → alerte", lambda c: _j(c.debut_symptomes, c.date_alerte), 2),
              ("Alerte → investigation", lambda c: _j(c.date_alerte, c.date_investigation), 1),
              ("Investigation → prélèvement", lambda c: _j(c.date_investigation, prelev[c.id]), 1),
              ("Prélèvement → résultat", lambda c: _j(prelev[c.id], resul[c.id]), 2),
              ("Symptômes → confirmation", lambda c: _j(c.debut_symptomes, c.date_confirmation), 3),
              ("Confirmation → isolement", lambda c: _j(c.date_confirmation, c.date_isolement), 1),
              ("Confirmation → début de l'anneau", lambda c: _j(c.date_confirmation, c.date_debut_anneau), 2)]
    lignes, retards = [], []
    for lib, f, seuil in etapes:
        v = [(c, f(c)) for c in cases]
        v = [(c, x) for c, x in v if x is not None and x >= 0]
        hors = [(c, x) for c, x in v if x > seuil]
        m = _med([x for _c, x in v])
        p_hors = _pct(len(hors), len(v)) if v else None
        lignes.append([tr(lib), _fmt_j(m), str(len(v)), _fmt_j(seuil),
                       ("ND", "nd") if p_hors is None else (_fmt_pct(p_hors), "re" if p_hors > 40 else ("al" if p_hors > 15 else "ok"))])
        for c, x in hors:
            retards.append((c, tr(lib), x, seuil))
    retards.sort(key=lambda r: -(r[2] - r[3]))
    obstacles = Counter(a.obstacle for c in cases for a in c.actions if a.obstacle.strip())
    sections = [barres(tr("Chaîne de surveillance"), [(l, v, f"{v} / {n}" if n else "ND", "bl") for l, v in chaine],
                       tr("nombre de fiches où chaque étape est datée")),
                table(tr("Délais par étape"), [tr("Étape"), tr("Médiane"), tr("Fiches"), tr("Seuil"), tr("Hors délai")], lignes,
                      tr("calculés depuis les dates saisies dans les fiches ; ND = aucune fiche avec les deux dates"), large=False)]
    if obstacles:
        sections.append(barres(tr("Causes de retard documentées (actions)"),
                               [(tr(k), v, str(v), "al") for k, v in obstacles.most_common(8)]))
    sections.append(table(tr("Fiches hors délai"), [tr("ID du cas"), tr("ZS"), tr("Étape"), tr("Délai"), tr("Seuil")],
                          [[case_label(c), _zs(c), lib, (_fmt_j(x), "re"), _fmt_j(s)] for c, lib, x, s in retards[:40]],
                          tr("40 premières ; ouvrez la fiche pour documenter la cause ou créer une action"),
                          liens=[f"/cas/{c.id}" for c, *_r in retards[:40]]))
    k_inv = sum(1 for _c, lib, *_r in retards if lib == tr("Alerte → investigation"))
    k_iso = sum(1 for _c, lib, *_r in retards if lib == tr("Confirmation → isolement"))
    return page(tr("Goulots d'étranglement de la surveillance"),
                tr("Où la chaîne alerte → investigation → prélèvement → confirmation → isolement se casse"),
                [tr("Calculé à partir des dates déjà saisies dans les fiches (étapes 1 à 3 et Laboratoire)."),
                 tr("Chaque retard peut devenir une action dans la fiche (étape 8), suivie dans le tableau de bord, onglet À traiter.")],
                [kpi(tr("Fiches analysées"), str(n)), kpi(tr("Investigations tardives"), str(k_inv), tr("alerte → investigation > 1 j"), "re" if k_inv else ""),
                 kpi(tr("Isolements tardifs"), str(k_iso), tr("confirmation → isolement > 1 j"), "re" if k_iso else ""),
                 kpi(tr("Résultats manquants"), str(sum(1 for c in cases if prelev[c.id] and not resul[c.id]))
                     , tr("prélèvement sans résultat daté"))],
                sections)


# ------------------------------------------------------------------------------------------------ concordance DHIS2
def statut_concordance(m: Optional[int], d: Optional[int]) -> Tuple[str, str]:
    if m is None or d is None:
        return tr("Comparaison impossible"), "nd"
    if m == d:
        return tr("Concordance numérique"), "ok"
    return (tr("Sous-listing potentiel"), "al") if m > d else (tr("Contacts supplémentaires dans DHIS2"), "bl")


def contacts_dhis2(c: Case) -> Optional[int]:
    """Contacts DHIS2 du cas : synchronisation DHIS2 si disponible, sinon nombre saisi dans la fiche."""
    from core import dhis2
    return dhis2.rapprochement(c)["dhis2"]


def concordance(cases: List[Case]) -> dict:
    from core import dhis2
    d = dhis2.charger()
    rows, liens, statuts = [], [], Counter()
    trouves = 0
    for c in sorted(cases, key=lambda c: (_zs(c), case_label(c))):
        r = dhis2.rapprochement(c, d)
        m, n = r["mapping"], r["dhis2"]
        st, ton = statut_concordance(m, n)
        if r["trouve"] is False:
            st, ton = tr("Introuvable dans la linelist DHIS2"), "re"
        statuts[(st, ton)] += 1
        trouves += bool(r["trouve"])
        ret = ("ND", "nd") if r["trouve"] is None else ((tr("Oui") + (f" · {tr(r['classif'])}" if r["classif"] else ""), "ok")
                                                         if r["trouve"] else (tr("Non"), "re"))
        rows.append([case_label(c), _zs(c), ret, "ND" if m is None else str(m), "ND" if n is None else str(n),
                     ("ND", "nd") if r["difference"] is None else (f"{r['difference']:+d}", "al" if r["difference"] > 0 else
                                                                   ("bl" if r["difference"] < 0 else "ok")), (st, ton)])
        liens.append(f"/cas/{c.id}")
    paires = [(contacts_listes(c), contacts_dhis2(c)) for c in cases]
    paires = [(m, n) for m, n in paires if m is not None and n is not None]
    sm, sd = sum(m for m, _ in paires), sum(n for _, n in paires)
    zs = []
    for z, cs in _par_zs(cases).items():
        p = [(contacts_listes(c), contacts_dhis2(c)) for c in cs]
        p = [(m, n) for m, n in p if m is not None and n is not None]
        if p:
            a, b = sum(m for m, _ in p), sum(d for _, d in p)
            r = _pct(b, a)
            zs.append((z, r, f"{_fmt_pct(r)} · {a} / {b}", _ton(r)))
    conc = _pct(sd, sm) if paires else None
    if d:
        note = [trf("Données DHIS2 du {date} ({source}) : {n_ll} alertes de la liste linéaire, {n_ct} contacts. "
                    "L'ID du mapping (N° EPID) est recherché dans la liste linéaire, puis les contacts rattachés à ce cas index sont comptés.",
                    date=d["maj"].replace("T", " à "), source=tr(d["source"]), n_ll=d["n_ll"], n_ct=d["n_contacts"])]
    else:
        note = [tr("Aucune donnée DHIS2 synchronisée : le nombre DHIS2 saisi à la main dans la fiche (étape 5 Contacts) est utilisé.")]
    note.append(tr("Même nombre ne veut pas dire mêmes personnes : un écart est un signal à investiguer, pas une preuve."))
    return page(tr("Concordance Mapping Épi × DHIS2"),
                tr("Réconciliation des contacts par cas index (nombres seulement)"), note,
                [kpi(tr("Retrouvés dans la linelist DHIS2"), f"{trouves} / {len(cases)}" if d else "ND",
                     tr("ID du mapping = N° EPID"), "" if not d else _ton(_pct(trouves, len(cases)))),
                 kpi(tr("Fiches comparables"), f"{len(paires)} / {len(cases)}", tr("contacts connus des deux côtés")),
                 kpi(tr("Contacts dans les fiches"), str(sm) if paires else "ND"),
                 kpi(tr("Contacts dans DHIS2"), str(sd) if paires else "ND"),
                 kpi(tr("Concordance"), _fmt_pct(conc), trf("écart : {n}", n=sm - sd) if paires else "", _ton(conc))],
                [barres(tr("Statut des fiches"), [(st, n, str(n), ton) for (st, ton), n in statuts.most_common()]),
                 barres(tr("Complétude DHIS2 par zone de santé"), zs, tr("contacts DHIS2 / contacts de la fiche")),
                 table(tr("Détail par cas index"), [tr("ID du cas"), tr("ZS"), tr("Retrouvé dans la linelist DHIS2"),
                                                     tr("Contacts déclarés dans le mapping"), tr("Contacts retrouvés dans DHIS2"),
                                                     tr("Différence (mapping − DHIS2)"), tr("Statut")], rows, liens=liens)])


# ------------------------------------------------------------------------------------------------ vaccination
def vaccination(cases: List[Case], ref: Optional[date] = None) -> dict:
    ref = ref or date.today()
    g_all = [g for c in cases for g in c.contacts]
    listes, elig, vacc = _som(g.nombre for g in g_all), _som(g.eligibles for g in g_all), _som(g.vaccines for g in g_all)
    motifs = Counter(g.motif_non_vaccination for g in g_all if g.motif_non_vaccination.strip())
    dl = _med([_j(c.date_confirmation, c.date_debut_anneau) for c in cases
               if c.date_confirmation and c.date_debut_anneau and c.date_debut_anneau >= c.date_confirmation])
    ouverts = sum(1 for c in cases if c.date_debut_anneau and c.date_debut_anneau >= ref - timedelta(days=6))
    sans = [c for c in cases if not c.date_debut_anneau]
    couv = _vacc(cases)
    zs_rows = []
    for z, cs in _par_zs(cases).items():
        gg = [g for c in cs for g in c.contacts]
        p = _vacc(cs)
        zs_rows.append([z, str(len(cs)), *("ND" if v is None else str(v) for v in
                        (_som(g.nombre for g in gg), _som(g.eligibles for g in gg), _som(g.vaccines for g in gg))),
                        (_fmt_pct(p), _ton(p))])
    return page(tr("Vaccination et protection des contacts"), tr("Contacts éligibles autour des cas et vaccination en anneau"),
                [tr("Saisie dans la fiche : étape 5 Contacts (éligibles, vaccinés, motif) et étape 1 Identité (début de l'anneau)."),
                 tr("Couverture = vaccinés / éligibles (ou / listés si les éligibles ne sont pas saisis).")],
                [kpi(tr("Contacts listés"), "ND" if listes is None else str(listes)),
                 kpi(tr("Éligibles"), "ND" if elig is None else str(elig)),
                 kpi(tr("Vaccinés"), "ND" if vacc is None else str(vacc), _fmt_pct(couv), _ton(couv)),
                 kpi(tr("Confirmation → anneau"), _fmt_j(dl), tr("médiane")),
                 kpi(tr("Anneaux ouverts (7 j)"), str(ouverts)),
                 kpi(tr("Cas sans début d'anneau"), str(len(sans)), "", "al" if sans else "")],
                [barres(tr("Cascade vaccinale"), [(tr("Listés"), listes, "ND" if listes is None else str(listes), "nd"),
                                                  (tr("Éligibles"), elig, "ND" if elig is None else str(elig), "bl"),
                                                  (tr("Vaccinés"), vacc, "ND" if vacc is None else str(vacc), "ok")]),
                 barres(tr("Motifs de non-vaccination"), [(tr(k), n, trf("{n} groupe(s)", n=n), "al") for k, n in motifs.most_common()]
                        or [(tr("Aucun motif saisi"), None, "", "nd")]),
                 table(tr("Par zone de santé"), [tr("ZS"), tr("Cas"), tr("Listés"), tr("Éligibles"), tr("Vaccinés"), tr("Couverture")], zs_rows),
                 table(tr("Cas sans début de vaccination de l'anneau"), [tr("ID du cas"), tr("ZS"), tr("Confirmation")],
                       [[case_label(c), _zs(c), f"{c.date_confirmation:%d/%m/%Y}" if c.date_confirmation else "ND"] for c in sans[:40]],
                       liens=[f"/cas/{c.id}" for c in sans[:40]])])


# ------------------------------------------------------------------------------------------------ psychosocial
def psychosocial(cases: List[Case]) -> dict:
    """Agrégats seulement : aucune liste de cas, aucun détail (confidentialité)."""
    st = Counter(c.besoin_psychosocial for c in cases if c.besoin_psychosocial)
    fam = Counter(c.soutien_famille for c in cases if c.soutien_famille)
    evalues = sum(n for k, n in st.items() if k != "Non évalué")
    besoin = sum(st[k] for k in ("Besoin identifié", "Soutien en cours", "Satisfait", "Référé"))
    recu = sum(st[k] for k in ("Soutien en cours", "Satisfait"))
    ton = {"Satisfait": "ok", "Soutien en cours": "bl", "Référé": "bl", "Besoin identifié": "al",
           "Évaluation en cours": "bl", "Non évalué": "nd"}
    zs_rows = []
    for z, cs in _par_zs(cases).items():
        s = Counter(c.besoin_psychosocial for c in cs if c.besoin_psychosocial)
        zs_rows.append([z, str(len(cs)), str(sum(n for k, n in s.items() if k != "Non évalué")),
                        str(sum(s[k] for k in ("Besoin identifié", "Soutien en cours", "Satisfait", "Référé"))),
                        str(sum(s[k] for k in ("Soutien en cours", "Satisfait"))), str(s["Besoin identifié"]),
                        str(sum(1 for c in cs if not c.besoin_psychosocial))])
    return page(tr("Prise en charge psychosociale"), tr("Agrégats et statuts seulement · aucune liste nominative"),
                [tr("Les fiches ne contiennent que le statut du besoin (étape 9 Besoins) ; les notes d'entretien restent dans l'outil du pilier."),
                 tr("Aucune liste de cas n'est affichée ici : seulement des nombres par statut et par zone.")],
                [kpi(tr("Cas évalués"), str(evalues)), kpi(tr("Besoin identifié"), str(besoin)),
                 kpi(tr("Soutien reçu"), str(recu), "", "ok" if recu else ""), kpi(tr("En attente"), str(st["Besoin identifié"]), "", "al" if st["Besoin identifié"] else ""),
                 kpi(tr("Non renseigné"), str(sum(1 for c in cases if not c.besoin_psychosocial)), tr("fiches sans statut"))],
                [barres(tr("Besoin psychosocial du cas"), [(tr(k), st[k], str(st[k]), ton[k]) for k in theme.PSY_CHOICES if st[k]]
                        or [(tr("Aucun statut saisi"), None, "", "nd")]),
                 barres(tr("Soutien à la famille"), [(tr(k), fam[k], str(fam[k]), ton[k]) for k in theme.PSY_CHOICES if fam[k]]
                        or [(tr("Aucun statut saisi"), None, "", "nd")]),
                 table(tr("Par zone de santé"), [tr("ZS"), tr("Cas"), tr("Évalués"), tr("Besoin identifié"), tr("Soutien reçu"),
                                                 tr("En attente"), tr("Non renseigné")], zs_rows)])


# ------------------------------------------------------------------------------------------------ services essentiels
def services(cases: List[Case]) -> dict:
    ton = {"Documenté": "ok", "À vérifier": "al", "À planifier": "al", "Sans objet": "nd"}
    lignes = []
    for k, lab in theme.BESOINS_CSSE:
        cnt = Counter(getattr(c, k) for c in cases if getattr(c, k))
        lignes.append([tr(lab)] + [str(cnt[s]) for s in theme.BESOIN_CHOICES] + [str(sum(1 for c in cases if not getattr(c, k)))])
    attente = [(c, [tr(lab) for k, lab in theme.BESOINS_CSSE if getattr(c, k) in ("À vérifier", "À planifier")]) for c in cases]
    attente = [(c, l) for c, l in attente if l]
    doc = sum(1 for c in cases for k, _l in theme.BESOINS_CSSE if getattr(c, k) == "Documenté")
    return page(tr("Continuité des services de santé essentiels"), tr("Besoins des patients (statuts de l'étape 9 Besoins)"),
                [tr("Côté patient : statuts saisis dans la fiche (étape 9 Besoins)."),
                 tr("Côté structures (consultations, CPN, accouchements, vaccination de routine) : à brancher plus tard sur le SNIS (DHIS2) ; rien n'est saisi dans Mapping Épi.")],
                [kpi(tr("Cas avec un besoin en attente"), str(len(attente)), tr("à vérifier ou à planifier"), "al" if attente else ""),
                 kpi(tr("Besoins documentés"), str(doc), "", "ok" if doc else ""),
                 kpi(tr("Fiches sans aucun statut"), str(sum(1 for c in cases if not any(getattr(c, k) for k, _l in theme.BESOINS_CSSE))))],
                [table(tr("Statuts par besoin"), [tr("Besoin")] + [tr(s) for s in theme.BESOIN_CHOICES] + [tr("Non renseigné")], lignes),
                 table(tr("Cas avec un besoin en attente"), [tr("ID du cas"), tr("ZS"), tr("Besoins à vérifier ou à planifier")],
                       [[case_label(c), _zs(c), ", ".join(l)] for c, l in attente[:40]], liens=[f"/cas/{c.id}" for c, _l in attente[:40]])])


# ------------------------------------------------------------------------------------------------ PoE / PoC
def poe_poc(rapports: List[dict], cases: List[Case], ref: Optional[date] = None) -> dict:
    ref = ref or date.today()
    d7 = ref - timedelta(days=6)

    def dt(r):
        try:
            return date.fromisoformat(r.get("date", ""))
        except ValueError:
            return None
    recents = [r for r in rapports if dt(r) and dt(r) >= d7]
    som = lambda k, rs: _som(r.get(k) for r in rs)      # noqa: E731
    voy, scr, al, inv = (som(k, recents) for k in ("voyageurs", "screenes", "alertes", "investiguees"))
    couv = _pct(scr, voy)
    pts = defaultdict(list)
    for r in recents:
        pts[r.get("point") or "?"].append(r)
    par_point = []
    for p, rs in sorted(pts.items()):
        cp = _pct(som("screenes", rs), som("voyageurs", rs))
        par_point.append((p, cp, _fmt_pct(cp), "re" if cp is not None and cp < SEUIL_RAPPORT else ("ok" if cp is not None else "nd")))
    passages = [(c, ev) for c in cases for ev in c.sorted_events() if ev.poe_poc.strip()]
    rows = [[r.get("date", ""), r.get("point", ""), r.get("zs", "") or "?", *("ND" if r.get(k) is None else str(r.get(k))
            for k in ("voyageurs", "screenes", "alertes", "investiguees"))] for r in sorted(rapports, key=lambda r: r.get("date", ""), reverse=True)[:60]]
    return page(tr("PoE / PoC et mobilité"), tr("Couverture du screening aux points d'entrée et de contrôle · 7 derniers jours"),
                [tr("Rapports journaliers saisis par point (formulaire ci-dessous) ; les passages des cas viennent de la chronologie des fiches (colonne « PoE / PoC franchi »)."),
                 tr("Couverture = voyageurs screenés / voyageurs enregistrés ; objectif 95 %.")],
                [kpi(tr("Voyageurs enregistrés"), "ND" if voy is None else f"{voy:,}".replace(",", " "), tr("7 derniers jours")),
                 kpi(tr("Screenés"), "ND" if scr is None else f"{scr:,}".replace(",", " ")),
                 kpi(tr("Couverture"), _fmt_pct(couv), tr("objectif 95 %"), "re" if couv is not None and couv < SEUIL_RAPPORT else ("ok" if couv else "")),
                 kpi(tr("Alertes détectées"), "ND" if al is None else str(al), trf("{n} investiguées", n="ND" if inv is None else inv)),
                 kpi(tr("Passages de cas documentés"), str(len(passages)), tr("chronologie des fiches"))],
                [barres(tr("Couverture par point (7 jours)"), par_point or [(tr("Aucun rapport sur 7 jours"), None, "", "nd")]),
                 table(tr("Passages des cas aux PoE / PoC"), [tr("ID du cas"), tr("ZS"), tr("Date"), tr("Trajet"), tr("PoE / PoC")],
                       [[case_label(c), _zs(c), f"{ev.date_debut:%d/%m/%Y}" if ev.date_debut else "ND",
                         f"{ev.lieu or '?'} → {ev.lieu_arrivee or '?'}", ev.poe_poc] for c, ev in passages[:40]],
                       liens=[f"/cas/{c.id}" for c, _e in passages[:40]]),
                 table(tr("Rapports journaliers"), [tr("Date"), tr("Point"), tr("ZS"), tr("Voyageurs"), tr("Screenés"),
                                                    tr("Alertes"), tr("Investiguées")], rows)])


SEUIL_RAPPORT = 95


# ------------------------------------------------------------------------------------------------ PCI
def pci_delais(cases: List[Case]) -> dict:
    sites = [s for c in cases for s in c.ipc if s.site.strip()]
    d = [_j(s.identifie_le, s.date) for s in sites]
    d = [x for x in d if x is not None and x >= 0]
    return {"sites": len(sites), "decontamines": sum(1 for s in sites if s.statut == "Décontaminé"),
            "verifies": sum(1 for s in sites if s.verifie_le), "avec_preuve": sum(1 for s in sites if s.preuve.strip()),
            "delai_median": _med(d), "delai_n": len(d)}
