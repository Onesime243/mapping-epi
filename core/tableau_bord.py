"""Tableau de bord de la riposte (super-administrateurs).

Tout est calculé à partir des fiches enregistrées du périmètre (jamais les exemples FICTIF). Règle : une donnée non
renseignée n'est jamais comptée comme 0 ; elle est signalée « non renseigné ».
Période : cas notifiés entre deux dates (notification, à défaut confirmation, à défaut début des symptômes).
Les alertes viennent de règles fixes (SEUILS) et renvoient chacune à la fiche concernée.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape as e
from statistics import median
from typing import Dict, List, Optional, Tuple

from config import theme
from core import indicateurs as IND
from core import pyramide, rules
from core import riposte as R
from core.langue import actuelle, tr, trf
from core.models import Action, Case
from core.piliers import pilier_action

SEUILS = {
    "delai_conf": 5,         # jours entre début des symptômes et confirmation (au-delà : alerte)
    "delai_conf_crit": 10,   # au-delà : critique
    "suivi_min": 80,         # % de contacts à haut risque suivis (en dessous : alerte)
    "completude": 80,        # % de complétude de la fiche (en dessous : à surveiller)
    "retard_crit": 2,        # jours de retard d'une action urgente (au-delà : critique)
}
HAUT_RISQUE = {"Très haut", "Haut"}

class _Categories(list):
    """Liste (clé, libellé, classe CSS) dont le libellé sort dans la langue courante quand on la parcourt."""

    def __iter__(self):
        for k, lib, cl in list.__iter__(self):
            yield k, tr(lib), cl


class _Libelles(dict):
    """Libellés des catégories, traduits à la lecture (LIB_CAT[clé])."""

    def __getitem__(self, k):
        return tr(dict.__getitem__(self, k))

    def get(self, k, defaut=None):
        return self[k] if k in self else defaut


# catégories d'actions : (clé, libellé, classe CSS)
CATEGORIES = _Categories([
    ("verifiee", "Vérifiées", "c-ok"),
    ("a_verifier", "Réalisées, à vérifier", "c-av"),
    ("sans_preuve", "Réalisées sans preuve", "c-sp"),
    ("en_cours", "En cours ou à faire", "c-ec"),
    ("retard", "En retard", "c-re"),
    ("bloquee", "Bloquées", "c-bl"),
])
LIB_CAT = _Libelles({k: v for k, v, _ in list.__iter__(CATEGORIES)})
CLS_CAT = {k: c for k, _v, c in CATEGORIES}


# -- structures ----------------------------------------------------------------------------------------------------
@dataclass
class Tuile:
    titre: str
    axes: str
    valeur: str
    detail: str
    pct: Optional[float] = None          # barre de progression (0 à 100)
    ton: str = "nd"                      # ok | alerte | crit | nd
    delta: str = ""
    delta_ton: str = ""                  # up (mieux) | dn (moins bien)
    onglet: str = ""                     # onglet ouvert au clic
    serie: List[Optional[float]] = field(default_factory=list)   # 8 dernières semaines (None = pas de donnée)
    serie_txt: str = ""                  # évolution de la dernière semaine, en mots
    serie_ton: str = ""                  # up (mieux) | dn (moins bien)
    seuil: Optional[float] = None        # ligne pointillée (délai)


@dataclass
class Alerte:
    niveau: str                          # crit | alerte
    texte: str
    cid: Optional[str] = None            # fiche concernée
    code: str = ""
    texte_fr: str = ""                   # même texte en français (signature du suivi des alertes, indépendante de la langue)


def _alerte(niveau: str, texte: str, cid: Optional[str] = None, code: str = "", **valeurs) -> Alerte:
    """Alerte dans la langue courante ; `texte` est le modèle français (à trous {…})."""
    return Alerte(niveau, trf(texte, **valeurs), cid, code, texte.format(**valeurs))


@dataclass
class LigneCas:
    case: Case
    code: str
    notif: Optional[date]
    completude: int
    delai: Optional[int]
    contacts: Optional[int]              # listés (None : aucun groupe dénombré)
    suivis: Optional[int]                # suivis (None : non renseigné)
    hr: int                              # contacts à haut risque listés
    lieux: int
    lieux_ok: int
    actions: int
    actions_faites: int
    statut: str = "À jour"               # Critique | À surveiller | À jour
    alertes: List[Alerte] = field(default_factory=list)


@dataclass
class LigneAction:
    case: Case
    code: str
    action: Action
    pilier: str
    categorie: str
    retard: Optional[int]


@dataclass
class Tableau:
    debut: date
    fin: date
    province: str
    zs: str
    pilier: str
    n: int
    n_total: int
    tuiles: List[Tuile]
    alertes: List[Alerte]
    cas: List[LigneCas]
    actions: List[LigneAction]
    bilan_actions: Dict[str, int]
    par_pilier: List[Tuple[str, Dict[str, int]]]
    obstacles: List[Tuple[str, int]]
    semaines: List[Tuple[date, int, Optional[float]]]      # (lundi, cas, délai médian)
    par_zs: List[dict]
    transmission: dict
    qualite: dict
    groupes: List[dict] = field(default_factory=list)          # alertes regroupées par cas (critiques d'abord)
    alertes_generales: List[Alerte] = field(default_factory=list)  # alertes sans cas précis


# -- outils --------------------------------------------------------------------------------------------------------
def _code(c: Case) -> str:
    return c.code_cas.strip() or c.titre_court()


def _num(v: Optional[float], unite: str = "") -> str:
    if v is None:
        return tr("non renseigné")
    s = f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{s} {tr(unite) if unite else ''}".strip()


def _pct(a: int, b: int) -> Optional[float]:
    return round(100 * a / b, 1) if b else None


def _fmt_pct(p: Optional[float]) -> str:
    return tr("non renseigné") if p is None else f"{p:.0f} %"


def selection(cases: List[Case], debut: date, fin: date, province: str = "", zs: str = "") -> List[Case]:
    out = []
    for c in cases:
        if c.exemple():
            continue
        if province and pyramide.norm(c.province) != pyramide.norm(province):
            continue
        if zs and pyramide.norm(c.zs) != pyramide.norm(zs):
            continue
        d, _ = IND.date_notification(c)
        if d and debut <= d <= fin:
            out.append(c)
    return out


def delai_conf(c: Case) -> Optional[int]:
    if c.debut_symptomes and c.date_confirmation:
        d = (c.date_confirmation - c.debut_symptomes).days
        return d if d >= 0 else None
    return None


def categorie_action(a: Action, ref: date) -> Tuple[str, Optional[int]]:
    if a.statut == "Fait":
        if a.valide_par.strip():
            return "verifiee", None
        return ("a_verifier" if a.preuve.strip() else "sans_preuve"), None
    retard = (ref - a.echeance).days if a.echeance and a.echeance < ref else None
    if a.obstacle.strip():
        return "bloquee", retard
    if retard:
        return "retard", retard
    return "en_cours", None


def _contacts(c: Case) -> Tuple[Optional[int], Optional[int], int, Optional[int]]:
    """(listés, suivis, haut risque listés, haut risque suivis) ; None = non renseigné."""
    groupes = [g for g in c.contacts if g.nombre is not None]
    listes = sum(g.nombre for g in groupes) if groupes else None
    avec_suivi = [g for g in groupes if g.suivis is not None]
    suivis = sum(g.suivis for g in avec_suivi) if avec_suivi else None
    hr = [g for g in groupes if g.risque in HAUT_RISQUE]
    hr_n = sum(g.nombre for g in hr)
    hr_suivi = [g for g in hr if g.suivis is not None]
    hr_s = sum(g.suivis for g in hr_suivi) if hr_suivi else None
    return listes, suivis, hr_n, hr_s


# -- analyse d'un cas ------------------------------------------------------------------------------------------------
def ligne_cas(c: Case, ref: date) -> LigneCas:
    code = _code(c)
    comp = rules.completeness(c)[0]
    dl = delai_conf(c)
    listes, suivis, hr_n, hr_s = _contacts(c)
    ok = sum(1 for s in c.ipc if s.statut == "Décontaminé")
    acts = [a for a in c.actions if a.texte.strip()]
    lc = LigneCas(c, code, IND.date_notification(c)[0], comp, dl, listes, suivis, hr_n, len(c.ipc), ok, len(acts),
                  sum(1 for a in acts if a.statut == "Fait"))
    al = lc.alertes
    if hr_n:
        if hr_s == 0:
            al.append(_alerte("crit", "{n} contacts à haut risque listés, aucun en suivi.", c.id, code, n=hr_n))
        elif hr_s is None:
            al.append(_alerte("alerte", "{n} contacts à haut risque listés, suivi non renseigné.", c.id, code, n=hr_n))
        elif 100 * hr_s / hr_n < SEUILS["suivi_min"]:
            al.append(_alerte("alerte", "{s} sur {n} contacts à haut risque suivis ({p:.0f} %).", c.id, code,
                              s=hr_s, n=hr_n, p=100 * hr_s / hr_n))
    if not c.contacts:
        al.append(_alerte("alerte", "aucun contact listé.", c.id, code))
    if dl is not None and dl > SEUILS["delai_conf"]:
        niv = "crit" if dl > SEUILS["delai_conf_crit"] else "alerte"
        al.append(_alerte(niv, "{d} jours entre début des symptômes et confirmation (seuil {s} j).", c.id, code,
                          d=dl, s=SEUILS["delai_conf"]))
    mauvais = [s for s in c.ipc if s.statut in ("Non", "Inconnu")]
    if mauvais:
        al.append(_alerte("alerte", "{n} lieu(x) avec PCI « Non » ou inconnue ({sites}).", c.id, code,
                          n=len(mauvais), sites=", ".join(s.site for s in mauvais[:3] if s.site)))
    urg = [a for a in acts if a.priorite == "Urgent" and a.statut != "Fait" and a.echeance
           and (ref - a.echeance).days > SEUILS["retard_crit"]]
    if urg:
        al.append(_alerte("crit", "{n} action(s) urgente(s) en retard de plus de {j} jours.", c.id, code,
                          n=len(urg), j=SEUILS["retard_crit"]))
    if rules.noms_personnes(c):
        al.append(_alerte("alerte", "nom de personne dans un texte libre (n’écrire que des identifiants).", c.id, code))
    if any(a.niveau == "crit" for a in al):
        lc.statut = "Critique"
    elif al or comp < SEUILS["completude"]:
        lc.statut = "À surveiller"
    return lc


# -- tableau complet -------------------------------------------------------------------------------------------------
def _indicateurs(cases: List[Case], ref: date) -> dict:
    lignes = [ligne_cas(c, ref) for c in cases]
    acts = [categorie_action(a, ref)[0] for c in cases for a in c.actions if a.texte.strip()]
    delais = [x.delai for x in lignes if x.delai is not None]
    return {
        "n": len(cases),
        "completude": (sum(x.completude for x in lignes) / len(lignes)) if lignes else None,
        "complets": sum(1 for x in lignes if x.completude >= 90),
        "actions": len(acts), "verifiees": acts.count("verifiee"), "retard": acts.count("retard"),
        "bloquees": acts.count("bloquee"), "sans_preuve": acts.count("sans_preuve"),
        "delai": median(delais) if delais else None, "n_delai": len(delais),
        "delai_ok": sum(1 for d in delais if d <= SEUILS["delai_conf"]),
        "lieux": sum(x.lieux for x in lignes), "lieux_ok": sum(x.lieux_ok for x in lignes),
        "lieux_mauvais": sum(1 for c in cases for s in c.ipc if s.statut in ("Non", "Inconnu")),
    }


def _ton(p: Optional[float], bon: float = 80, moyen: float = 50) -> str:
    if p is None:
        return "nd"
    return "ok" if p >= bon else ("alerte" if p >= moyen else "crit")


def _tuiles(cur: dict, prev: dict) -> List[Tuile]:
    out = []
    # 1. cas mappés
    t = Tuile(tr("Cas mappés"), tr("Axes A, B"), str(cur["n"]),
              (trf("complétude moyenne {p:.0f} % · {n} fiche(s) à 90 % ou plus", p=cur["completude"], n=cur["complets"])
               if cur["completude"] is not None else tr("aucun cas sur la période")),
              cur["completude"], _ton(cur["completude"], 90, 70), onglet="qualite")
    if prev["n"]:
        d = cur["n"] - prev["n"]
        t.delta, t.delta_ton = (trf("{d:+d} vs période précédente", d=d), "") if d else (tr("stable"), "")
    out.append(t)
    # 2. actions vérifiées
    p = _pct(cur["verifiees"], cur["actions"])
    out.append(Tuile(tr("Actions vérifiées"), tr("Axes N, H"), f"{cur['verifiees']} / {cur['actions']}",
                     trf("{p} · {r} en retard · {b} bloquée(s) · {s} sans preuve", p=_fmt_pct(p), r=cur["retard"],
                         b=cur["bloquees"], s=cur["sans_preuve"]) if cur["actions"] else tr("aucune action prescrite"),
                     p, _ton(p, 70, 40), onglet="actions"))
    # 3. délai symptômes → confirmation
    p = _pct(cur["delai_ok"], cur["n_delai"])
    t = Tuile(tr("Délai symptômes → confirmation"), tr("Axes C, F, I"), _num(cur["delai"], "j"),
              trf("médiane · {k} cas renseignés sur {n} · {p} en {s} j ou moins", k=cur["n_delai"], n=cur["n"],
                  p=_fmt_pct(p), s=SEUILS["delai_conf"]), p, _ton(p, 80, 50), onglet="transmission")
    if cur["delai"] is not None and prev["delai"] is not None:
        d = cur["delai"] - prev["delai"]
        if d:
            t.delta = f"{'▲' if d > 0 else '▼'} {_num(abs(d), 'j')}"
            t.delta_ton = "dn" if d > 0 else "up"
    out.append(t)
    # 4. lieux d'exposition sécurisés
    p = _pct(cur["lieux_ok"], cur["lieux"])
    out.append(Tuile(tr("Lieux d'exposition décontaminés"), tr("Axes G, L, O, P"), f"{cur['lieux_ok']} / {cur['lieux']}",
                     trf("{p} · {n} avec PCI « Non » ou inconnue", p=_fmt_pct(p), n=cur["lieux_mauvais"]) if cur["lieux"]
                     else tr("aucun lieu PCI renseigné"), p, _ton(p, 80, 50), onglet="contacts"))
    return out


def _series(cases_perimetre: List[Case], fin: date, province: str, zs: str, ref: date, n: int = 8) -> List[dict]:
    """Indicateurs des tuiles semaine par semaine (lundi → dimanche), sur les n semaines qui finissent avec `fin`."""
    lundi = fin - timedelta(days=fin.weekday())
    out = []
    for k in range(n - 1, -1, -1):
        d = lundi - timedelta(days=7 * k)
        ind = _indicateurs(selection(cases_perimetre, d, d + timedelta(days=6), province, zs), ref)
        out.append({"debut": d, "n": ind["n"], "verif": _pct(ind["verifiees"], ind["actions"]),
                    "delai": ind["delai"], "lieux": _pct(ind["lieux_ok"], ind["lieux"])})
    return out


def _evolution(serie: List[Optional[float]], unite: str, mieux_si_bas: bool = False,
               semaines: Optional[List[date]] = None) -> Tuple[str, str]:
    """Évolution entre les deux dernières semaines renseignées (la semaine en cours est souvent encore vide)."""
    idx = [i for i, v in enumerate(serie) if v is not None]
    if not idx:
        return tr("aucune donnée sur 8 semaines"), ""
    quand = ""
    if idx[-1] != len(serie) - 1 and semaines:
        quand = " " + trf("(semaine du {d})", d=f"{semaines[idx[-1]]:%d/%m}")
    if len(idx) < 2:
        return tr("une seule semaine avec des données") + quand, ""
    d = serie[idx[-1]] - serie[idx[-2]]
    if abs(d) < 1e-9:
        return tr("stable") + quand, ""
    mieux = (d < 0) if mieux_si_bas else (d > 0)
    if unite == "cas":
        return f"{'▲' if d > 0 else '▼'} " + trf("{d:+.0f} vs semaine précédente", d=d) + quand, ""
    val = _num(abs(d), "j") if unite == "j" else trf("{n:.0f} point" + ("s" if abs(d) >= 2 else ""), n=abs(d))
    return (f"{'▲ +' if d > 0 else '▼ −'}{val}{': ' if actuelle() == 'en' else ' : '}{tr('mieux') if mieux else tr('moins bien')}" + quand,
            ("up" if mieux else "dn"))


def sparkline(serie: List[Optional[float]], seuil: Optional[float] = None, w: int = 150, h: int = 38) -> str:
    """Petite courbe : un trait par suite de semaines renseignées ; les semaines sans donnée restent vides."""
    vals = [v for v in serie if v is not None]
    if not vals:
        return f'<svg class="tb-spark-svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true"></svg>'
    lo, hi = min(vals + ([seuil] if seuil is not None else [])), max(vals + ([seuil] if seuil is not None else []))
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    n = len(serie)
    def xy(i, v):
        return 5 + i * (w - 10) / max(1, n - 1), h - 5 - (v - lo) / (hi - lo) * (h - 10)
    o = [f'<svg class="tb-spark-svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">']
    if seuil is not None:
        y = xy(0, seuil)[1]
        o.append(f'<line class="sp-seuil" x1="0" x2="{w}" y1="{y:.1f}" y2="{y:.1f}"/>')
    seg: List[str] = []
    for i, v in enumerate(serie + [None]):
        if v is None:
            if len(seg) > 1:
                o.append(f'<polyline class="sp-l" points="{" ".join(seg)}"/>')
            elif len(seg) == 1:
                x0, y0 = seg[0].split(",")
                o.append(f'<circle class="sp-p" cx="{x0}" cy="{y0}" r="2"/>')
            seg = []
        else:
            x, y = xy(i, v)
            seg.append(f"{x:.1f},{y:.1f}")
    if serie[-1] is not None:
        x, y = xy(n - 1, serie[-1])
        alerte = seuil is not None and serie[-1] > seuil
        o.append(f'<circle class="sp-fin{" sp-mal" if alerte else ""}" cx="{x:.1f}" cy="{y:.1f}" r="3.5"/>')
    o.append("</svg>")
    return "".join(o)


def _semaines(cases: List[Case], debut: date, fin: date) -> List[Tuple[date, int, Optional[float]]]:
    lundi = debut - timedelta(days=debut.weekday())
    sem: Dict[date, List[Case]] = {}
    d = lundi
    while d <= fin:
        sem[d] = []
        d += timedelta(days=7)
    for c in cases:
        n, _ = IND.date_notification(c)
        if n:
            k = n - timedelta(days=n.weekday())
            sem.setdefault(k, []).append(c)
    out = []
    for k in sorted(sem):
        dl = [x for x in (delai_conf(c) for c in sem[k]) if x is not None]
        out.append((k, len(sem[k]), median(dl) if dl else None))
    return out


def construire(cases_perimetre: List[Case], debut: date, fin: date, province: str = "", zs: str = "",
               pilier: str = "", brouillons: int = 0, ref: Optional[date] = None) -> Tableau:
    ref = ref or date.today()          # retards des actions : à la date du jour
    cases = selection(cases_perimetre, debut, fin, province, zs)
    duree = (fin - debut).days + 1
    prev = selection(cases_perimetre, debut - timedelta(days=duree), debut - timedelta(days=1), province, zs)
    lignes = sorted((ligne_cas(c, ref) for c in cases),
                    key=lambda x: ({"Critique": 0, "À surveiller": 1}.get(x.statut, 2), -(x.notif or date.min).toordinal()))

    # actions (filtre pilier)
    acts: List[LigneAction] = []
    for c in cases:
        for a in c.actions:
            if not a.texte.strip():
                continue
            p = pilier_action(a)
            if pilier and p != pilier:
                continue
            cat, r = categorie_action(a, ref)
            acts.append(LigneAction(c, _code(c), a, p, cat, r))
    ordre = {k: i for i, (k, _l, _c) in enumerate(CATEGORIES)}
    acts.sort(key=lambda x: ({"bloquee": 0, "retard": 1, "sans_preuve": 2}.get(x.categorie, 3), -(x.retard or 0),
                             ordre[x.categorie]))
    bilan = Counter(x.categorie for x in acts)
    par_p: Dict[str, Counter] = defaultdict(Counter)
    for x in acts:
        par_p[x.pilier][x.categorie] += 1
    par_pilier = [(p, dict(par_p[p])) for p in theme.PILIERS if p in par_p]
    obstacles = Counter(x.action.obstacle for x in acts if x.action.obstacle and x.action.statut != "Fait").most_common()

    # alertes : critiques d'abord, puis les plus récentes
    alertes = [a for x in lignes for a in x.alertes]
    alertes.sort(key=lambda a: a.niveau != "crit")
    if bilan.get("sans_preuve"):
        alertes.append(_alerte("alerte", "{n} action(s) déclarée(s) réalisée(s) sans preuve.", n=bilan["sans_preuve"]))
    groupes = []
    for x in lignes:
        if not x.alertes:
            continue
        crit = [a for a in x.alertes if a.niveau == "crit"]
        autres = [a for a in x.alertes if a.niveau != "crit"]
        groupes.append({"cid": x.case.id, "code": x.code, "zs": x.case.zs or "?", "province": x.case.province or "?",
                        "notif": x.notif, "crit": len(crit), "alertes": len(autres),
                        "liste": [{"niveau": a.niveau, "texte": a.texte.rstrip(". "),
                                   "texte_fr": (a.texte_fr or a.texte).rstrip(". ")} for a in crit + autres]})
    groupes.sort(key=lambda g: (-g["crit"], -g["alertes"], -(g["notif"] or date.min).toordinal()))
    generales = [a for a in alertes if not a.cid]

    # par zone de santé
    zs_map: Dict[str, List[LigneCas]] = defaultdict(list)
    for x in lignes:
        zs_map[x.case.zs or tr("ZS non renseignée")].append(x)
    par_zs = []
    for nom, xs in sorted(zs_map.items(), key=lambda kv: -len(kv[1])):
        cs = [x.case for x in xs]
        cont = [_contacts(c) for c in cs]
        listes = [l for l, _s, _h, _hs in cont if l is not None]
        suivis = [s for _l, s, _h, _hs in cont if s is not None]
        vacc = [g.vaccines for c in cs for g in c.contacts if g.vaccines is not None]
        ipc = Counter(s.statut for c in cs for s in c.ipc)
        par_zs.append({
            "zs": nom, "province": cs[0].province, "cas": len(cs),
            "completude": round(sum(x.completude for x in xs) / len(xs)),
            "contacts": sum(listes) if listes else None, "hr": sum(h for _l, _s, h, _hs in cont),
            "suivis": sum(suivis) if suivis else None, "vaccines": sum(vacc) if vacc else None,
            "cas_vaccines": sum(1 for c in cs if c.vaccine == "Oui"),
            "ipc": {k: ipc.get(k, 0) for k in theme.IPC_CHOICES}, "ipc_total": sum(ipc.values()),
            "critiques": sum(1 for x in xs if x.statut == "Critique"),
        })

    # parcours et transmission
    lien = Counter(c.contact_connu or "Inconnu" for c in cases)
    expo = Counter()
    for c in cases:
        for ev in c.events:
            if ev.contact_corps:
                expo[tr("Contact avec le corps")] += 1
            if ev.liquides:
                expo[tr("Liquides biologiques")] += 1
            if ev.sans_pci:
                expo[tr("Soins sans PCI")] += 1
            if ev.type in ("Funérailles", "Enterrement"):
                expo[tr("Funérailles ou enterrement")] += 1
            if ev.lieu_arrivee.strip():
                expo[tr("Déplacements")] += 1
    transmission = {
        "lien": [(k, lien.get(k, 0)) for k in ["Contact connu suivi", "Contact connu", "Non contact", "Inconnu"]
                 if lien.get(k)],
        "avec_source": sum(1 for c in cases if c.id_cas_source.strip()),
        "expositions": expo.most_common(),
        "deces_communautaires": sum(1 for c in cases if R.deces_communautaire(c)),
        "agents_sante": sum(1 for c in cases if c.agent_sante == "Oui"),
    }

    # qualité
    manq = Counter(m.split(" :")[0] for c in cases for m in rules.completeness(c)[1])
    incoh = sum(1 for c in cases if any(i.niveau == "erreur" for i in rules.check_consistency(c)))
    qualite = {"manquants": manq.most_common(8), "incoherences": incoh, "brouillons": brouillons,
               "par_zs": [(z["zs"], z["completude"]) for z in par_zs]}

    tuiles = _tuiles(_indicateurs(cases, ref), _indicateurs(prev, ref))
    sem = _series(cases_perimetre, fin, province, zs, ref)
    for t, cle_, unite, bas in zip(tuiles, ("n", "verif", "delai", "lieux"), ("cas", "pct", "j", "pct"),
                                   (False, False, True, False)):
        t.serie = [w_[cle_] for w_ in sem]
        if cle_ == "n":
            t.serie = [float(v) if v else None for v in t.serie]        # semaine sans cas : pas de point
        t.serie_txt, t.serie_ton = _evolution(t.serie, unite, bas, [w_["debut"] for w_ in sem])
        if cle_ == "delai":
            t.seuil = SEUILS["delai_conf"]
    return Tableau(debut, fin, province, zs, pilier, len(cases), len([c for c in cases_perimetre if not c.exemple()]),
                   tuiles, alertes, lignes, acts, dict(bilan),
                   par_pilier, obstacles, _semaines(cases, debut, fin), par_zs, transmission, qualite,
                   groupes=groupes, alertes_generales=generales)


# -- graphique : cas par semaine et délai médian ----------------------------------------------------------------------
def svg_semaines(sem: List[Tuple[date, int, Optional[float]]], width: int = 640, height: int = 230) -> str:
    if not sem:
        return f'<p class="muted">{e(tr("Aucune semaine dans la période."))}</p>'
    ml, mr, mt, mb = 36, 40, 14, 34
    pw, ph = width - ml - mr, height - mt - mb
    n = len(sem)
    vmax = max(1, max(c for _d, c, _m in sem))
    pas = 1 if vmax <= 5 else (2 if vmax <= 10 else (5 if vmax <= 25 else 10))
    top = ((vmax + pas - 1) // pas) * pas
    dmax = max([m for _d, _c, m in sem if m is not None] + [SEUILS["delai_conf"] + 1])
    dtop = ((int(dmax) + 4) // 5) * 5
    bw = pw / n
    o = [f'<svg class="tb-svg" viewBox="0 0 {width} {height}" width="100%" role="img" '
         f'aria-label="{e(tr("Cas par semaine et délai médian"))}">']
    for v in range(0, top + 1, pas):
        y = mt + ph - ph * v / top
        o.append(f'<line class="grille" x1="{ml}" x2="{ml + pw}" y1="{y:.1f}" y2="{y:.1f}"/>'
                 f'<text class="axe" x="{ml - 6}" y="{y + 4:.1f}" text-anchor="end">{v}</text>')
    pts = []
    for i, (d, c, m) in enumerate(sem):
        x = ml + i * bw
        h = ph * c / top
        o.append(f'<rect class="barre-cas" x="{x + bw * .2:.1f}" y="{mt + ph - h:.1f}" width="{bw * .6:.1f}" height="{h:.1f}" '
                 f'rx="3"><title>{e(trf("Semaine du {d} : {n} cas", d=f"{d:%d/%m}", n=c))}</title></rect>')
        if c:
            o.append(f'<text class="val" x="{x + bw / 2:.1f}" y="{mt + ph - h - 4:.1f}" text-anchor="middle">{c}</text>')
        if n <= 16 or i % 2 == 0:
            o.append(f'<text class="axe" x="{x + bw / 2:.1f}" y="{mt + ph + 16}" text-anchor="middle">'
                     f'{trf("S{n}", n=d.isocalendar()[1])}</text>')
        if m is not None:
            pts.append((x + bw / 2, mt + ph - ph * m / dtop, m, d))
    for v in range(0, dtop + 1, 5):
        y = mt + ph - ph * v / dtop
        o.append(f'<text class="axe-d" x="{ml + pw + 6}" y="{y + 4:.1f}">{v} {tr("j")}</text>')
    ys = mt + ph - ph * SEUILS["delai_conf"] / dtop
    o.append(f'<line class="seuil" x1="{ml}" x2="{ml + pw}" y1="{ys:.1f}" y2="{ys:.1f}"/>'
             '')
    if len(pts) > 1:
        o.append('<polyline class="ligne-delai" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y, _m, _d in pts) + '"/>')
    for x, y, m, d in pts:
        o.append(f'<circle class="pt-delai" cx="{x:.1f}" cy="{y:.1f}" r="3.5"><title>'
                 f'{e(trf("Semaine du {d} : délai médian {v}", d=f"{d:%d/%m}", v=_num(m, "j")))}</title></circle>')
    o.append(f'<line class="axe-l" x1="{ml}" x2="{ml + pw}" y1="{mt + ph}" y2="{mt + ph}"/></svg>')
    return "".join(o)


def barre_empilee(compte: Dict[str, int]) -> str:
    tot = sum(compte.values())
    if not tot:
        return ""
    return '<div class="tb-pile">' + "".join(
        f'<i class="{cl}" style="width:{100 * compte[k] / tot:.2f}%" title="{e(lib)}{': ' if actuelle() == 'en' else ' : '}{compte[k]}"></i>'
        for k, lib, cl in CATEGORIES if compte.get(k)) + "</div>"
