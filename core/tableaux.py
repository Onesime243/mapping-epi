"""Les 12 tableaux de bord de « Tableau de bord ▾ » (vue stratégique, couverture des mappings, dynamique, parcours,
chaînes, contacts, actions, géospatial, mobilité, PCI, profil clinique, qualité des données).

Tout est calculé en direct sur les fiches du périmètre du compte (filtres province, zone, période). Le résultat est un
dictionnaire de nombres et de libellés, sans aucun identifiant de cas ni nom, rendu par web/static/tableaux.js.
Règles : une donnée inconnue reste inconnue (jamais 0) ; les délais négatifs ou supérieurs à 60 jours sont écartés
des médianes et comptés comme anomalies dans « Qualité des données ».
"""
from __future__ import annotations

import statistics as st
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional

from config import theme
from core import riposte as R
from core import rules
from core.models import Case

VUES = [("strategique", "Vue stratégique", "grid"), ("couverture", "Couverture des mappings", "layers"),
        ("dynamique", "Dynamique épidémiologique", "chart"), ("parcours", "Parcours thérapeutique", "bed"),
        ("chaines", "Chaînes de transmission", "net"), ("contacts", "Surveillance et contacts", "users"),
        ("actions", "Suivi des actions", "clip"), ("geo", "Analyse géospatiale", "globe"),
        ("mobilite", "Mobilité et déplacements", "send"), ("pci", "PCI et structures sanitaires", "shield"),
        ("clinique", "Profil clinique et symptômes", "heart"), ("qualite", "Qualité des données", "db")]
CLES = [v[0] for v in VUES]
DELAI_MAX = 60
SYMPTOMES = [("Fièvre", "Fièvre"), ("Asthénie / fatigue", "Asthénie / fatigue"), ("Céphalées", "Céphalées"),
             ("Douleurs musculaires / courbatures", "Courbatures"), ("Anorexie", "Anorexie"), ("Vomissements", "Vomissements"),
             ("Diarrhée", "Diarrhée"), ("Nausées", "Nausées"), ("Dyspnée / détresse respiratoire", "Dyspnée"),
             ("Saignements (non précisés)", "Saignements"), ("Hématémèse", "Hématémèse"), ("Méléna", "Méléna")]
AGES = [(0, 4), (5, 14), (15, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 130)]


def _j(a: Optional[date], b: Optional[date]) -> Optional[int]:
    if not a or not b:
        return None
    d = (b - a).days
    return d if 0 <= d <= DELAI_MAX else None


def _med(v) -> Optional[float]:
    v = [x for x in v if x is not None]
    return round(st.median(v), 1) if v else None


def _iqr(v) -> Optional[list]:
    v = sorted(x for x in v if x is not None)
    if len(v) < 4:
        return [v[0], _med(v), v[-1]] if v else None
    q = st.quantiles(v, n=4)
    return [round(q[0], 1), round(q[1], 1), round(q[2], 1)]


def _issue(c: Case) -> str:
    i = (c.issue or "").strip()
    if i in ("Décès",):
        return "Décès"
    if i in ("En traitement",):
        return "En traitement"
    if i in ("Vivant", "Guéri"):
        return "Vivant"
    return "Inconnu"


def _lien(c: Case) -> str:
    v = (c.contact_connu or "").strip()
    return {"Contact connu suivi": "Contact connu suivi", "Contact connu": "Contact connu (suivi non précisé)",
            "Non contact": "Non contact"}.get(v, "Inconnu")


def _somme(vals) -> Optional[float]:
    v = [x for x in vals if x is not None]
    return sum(v) if v else None


def _ligne(c: Case, ref: date) -> dict:
    """Variables d'un cas (aucun identifiant ne sort de ce module)."""
    from core import dhis2
    ph = None
    try:
        ph = rules.phases(c)
    except Exception:                                     # une fiche mal formée ne bloque jamais le tableau de bord
        pass
    j0 = ph.j0 if ph else None
    iso = c.date_isolement or R.date_isolement(c)
    labs = sorted([l for l in c.labs if l.prelevement], key=lambda l: l.prelevement)
    l0 = labs[0] if labs else None
    lab_h = round((l0.resultat_le - l0.prelevement).total_seconds() / 3600, 1) if l0 and l0.resultat_le else None
    try:
        risque = c.risque_global or rules.global_risk(c)[0]
    except Exception:
        risque = c.risque_global or "Inconnu"
    rap = dhis2.rapprochement(c)
    ouvertes = sum(1 for a in c.actions if a.texte.strip() and a.statut != "Fait")
    return {
        "prov": c.province or "?", "zs": c.zs or "?", "as": c.aire_sante or "?", "sexe": c.sexe, "issue": _issue(c), "lien": _lien(c),
        "age": (c.age / 12 if (c.age_unite or "").startswith("mois") else c.age) if c.age is not None else None,
        "src": bool((c.id_cas_source or "").strip()), "conf": c.date_confirmation, "notif": c.date_notification, "iso": iso,
        "deces": c.date_deces, "comm": R.deces_communautaire(c), "eds": R.enterrement_securise(c),
        "d_conf": _j(c.debut_symptomes, c.date_confirmation), "d_iso": _j(c.debut_symptomes, iso),
        "d_notif": _j(c.debut_symptomes, c.date_notification), "d_dc": _j(j0, c.date_deces),
        "d_lab": lab_h if lab_h is not None and 0 <= lab_h <= 240 else None, "prel": l0.prelevement.date() if l0 else None,
        "res": l0.resultat_le.date() if l0 and l0.resultat_le else None,
        "cl": _somme(g.nombre for g in c.contacts), "ch": _somme(g.nombre for g in c.contacts if g.risque in ("Haut", "Très haut")),
        "cs": _somme(g.suivis for g in c.contacts), "cv": _somme(g.vaccines for g in c.contacts),
        "dh_ok": rap["trouve"], "dh_n": rap["dhis2"] if rap["source"] == "DHIS2" else None,
        "dh_diff": rap["difference"] if rap["source"] == "DHIS2" else None,
        "risque": risque or "Inconnu", "compl": rules.completeness(c)[0], "id": bool((c.code_cas or "").strip()),
        "etapes": len(c.events), "lieux": len(c.places), "depl": sum(1 for e in c.events if (e.lieu_arrivee or "").strip()),
        "transports": sorted({e.transport for e in c.events if (e.transport or "").strip()}),
        "corps": any(e.contact_corps for e in c.events), "liq": any(e.liquides for e in c.events), "sanspci": any(e.sans_pci for e in c.events),
        "fun": any(e.type in ("Funérailles", "Enterrement") for e in c.events),
        "pci": len([s for s in c.ipc if s.site.strip()]), "pci_ok": sum(1 for s in c.ipc if s.statut == "Décontaminé"),
        "pci_non": sum(1 for s in c.ipc if s.statut in ("Non", "Inconnu")), "ppl": c.agent_sante == "Oui",
        "phase": c.phase_dds, "expo": ph.exposition_source if ph else "estimée", "act": ouvertes,
        "code": (c.code_cas or "").strip(), "code_src": (c.id_cas_source or "").strip(),
        "j0_hors": bool(c.debut_symptomes and (c.debut_symptomes.year < theme.ANNEE_MIN or c.debut_symptomes > ref)),
        "delai_hors": bool(c.debut_symptomes and c.date_confirmation and not (0 <= (c.date_confirmation - c.debut_symptomes).days <= DELAI_MAX)),
        "aberrant": bool(c.aberrants or any(g.aberrants for g in c.contacts) or any(p.aberrants for p in c.places)),
        "issue_libre": (c.issue or "") not in theme.ISSUE_CHOICES, "lien_libre": (c.contact_connu or "") not in theme.CONTACT_STATUS_CHOICES,
    }


def _symptomes(cases: List[Case]) -> dict:
    from core import symptomes as SY
    ph = {p: {"n": 0, "c": Counter()} for p, _l in SY.PHASES}
    for c in cases:
        try:
            ms = SY.mentions(c)
            doc = SY.phases_documentees(c, ms)
        except Exception:
            continue
        par = defaultdict(set)
        for m in ms:
            par[m.phase].add(m.symptome)
        for p in doc:
            if p in ph:
                ph[p]["n"] += 1
                for s in par.get(p, ()):
                    ph[p]["c"][s] += 1
    return {"labels": [l for _k, l in SYMPTOMES],
            "phases": {p: {"n": v["n"], "v": [round(100 * v["c"][k] / v["n"]) if v["n"] else 0 for k, _l in SYMPTOMES]} for p, v in ph.items()}}


def _chaines(lignes: List[dict], ref: date) -> tuple:
    from core.dhis2 import cle_epid
    idx = {cle_epid(l["code"]): i for i, l in enumerate(lignes) if l["code"]}
    E = []
    for i, l in enumerate(lignes):
        k = cle_epid(l["code_src"]) if l["code_src"] else ""
        if k and k in idx and idx[k] != i:
            E.append((idx[k], i))
    par = list(range(len(lignes)))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for a, b in E:
        par[f(a)] = f(b)
    comp = defaultdict(list)
    for a, b in E:
        comp[f(a)].append((a, b))
    out = []
    for es in comp.values():
        noeuds = sorted({x for e in es for x in e})
        der = max([lignes[x]["conf"] for x in noeuds if lignes[x]["conf"]], default=None)
        out.append({"n": len(noeuds), "zs": Counter(lignes[x]["zs"] for x in noeuds).most_common(1)[0][0],
                    "dc": sum(1 for x in noeuds if lignes[x]["issue"] == "Décès"), "der": der.isoformat() if der else None,
                    "ouverte": bool(der) and (ref - der).days <= 21,
                    "edges": [[noeuds.index(a), noeuds.index(b)] for a, b in es], "etat": [lignes[x]["issue"] for x in noeuds]})
    out.sort(key=lambda c: (-c["n"], c["der"] or ""))
    return out, len(E)


def construire(cases: List[Case], ref: Optional[date] = None) -> dict:
    ref = ref or date.today()
    L = [_ligne(c, ref) for c in cases]
    n = len(L)
    D: Dict = {"n": n, "ref": ref.isoformat()}
    if not n:
        return D
    dc = [l for l in L if l["issue"] == "Décès"]
    cas7 = sum(1 for l in L if l["conf"] and l["conf"] > ref - timedelta(days=7))
    cas7p = sum(1 for l in L if l["conf"] and ref - timedelta(days=14) < l["conf"] <= ref - timedelta(days=7))
    D["kpi"] = {"cas": n, "deces": len(dc), "comm": sum(1 for l in dc if l["comm"]), "zs": len({(l["prov"], l["zs"]) for l in L}),
                "prov": len({l["prov"] for l in L if l["prov"] != "?"}), "as": len({(l["zs"], l["as"]) for l in L}),
                "cas7": cas7, "cas7p": cas7p, "cas28": sum(1 for l in L if l["conf"] and l["conf"] > ref - timedelta(days=28)),
                "ppl": sum(1 for l in L if l["ppl"]), "d_iso": _med(l["d_iso"] for l in L), "d_conf": _med(l["d_conf"] for l in L),
                "d_notif": _med(l["d_notif"] for l in L), "d_lab": _med(l["d_lab"] for l in L), "d_dc": _med(l["d_dc"] for l in L),
                "compl": round(st.mean(l["compl"] for l in L), 1)}
    # semaines ISO : les 13 dernières jusqu'à la semaine de référence
    lundi = ref - timedelta(days=ref.weekday())
    sem = [lundi - timedelta(weeks=12 - i) for i in range(13)]
    def dans(d, s): return d and s <= d < s + timedelta(days=7)
    D["semaines"] = [s.isocalendar()[1] for s in sem]
    D["cas_sem"] = [sum(1 for l in L if dans(l["conf"], s)) for s in sem]
    D["dc_sem"] = [sum(1 for l in dc if dans(l["deces"], s)) for s in sem]
    jours = [ref - timedelta(days=27 - i) for i in range(28)]
    D["jours"] = [f"{d:%d/%m}" for d in jours]
    D["cas_j"] = [sum(1 for l in L if l["conf"] == d) for d in jours]
    D["notif_j"] = [sum(1 for l in L if l["notif"] == d) for d in jours]
    D["prov"] = Counter(l["prov"] for l in L).most_common()
    s_der, s_avant = sem[-1], sem[-2]
    zsd = defaultdict(list)
    for l in L:
        zsd[(l["prov"], l["zs"])].append(l)
    Z = []
    for (p, z), ls in zsd.items():
        der = max([l["conf"] for l in ls if l["conf"]], default=None)
        Z.append({"zs": z, "prov": p, "n": len(ls), "dc": sum(1 for l in ls if l["issue"] == "Décès"),
                  "s47": sum(1 for l in ls if dans(l["conf"], s_avant)), "s48": sum(1 for l in ls if dans(l["conf"], s_der)),
                  "n7": sum(1 for l in ls if l["conf"] and l["conf"] > ref - timedelta(days=7)),
                  "jours": (ref - der).days if der else None, "d_iso": _med(l["d_iso"] for l in ls),
                  "compl": round(st.mean(l["compl"] for l in ls)), "cl": int(sum(l["cl"] or 0 for l in ls)),
                  "cs": int(sum(l["cs"] or 0 for l in ls)), "as": len({l["as"] for l in ls}),
                  "pci": sum(l["pci"] for l in ls), "pci_ok": sum(l["pci_ok"] for l in ls),
                  "dh_ok": sum(1 for l in ls if l["dh_ok"]), "dh_tot": sum(1 for l in ls if l["dh_ok"] is not None),
                  "actions": sum(l["act"] for l in ls)})
    Z.sort(key=lambda z: -z["n"])
    D["zs"] = Z
    D["sem_lib"] = [f"S{D['semaines'][-2]}", f"S{D['semaines'][-1]}"]
    D["lien"] = Counter(l["lien"] for l in L).most_common()
    D["issue"] = Counter(l["issue"] for l in L).most_common()
    D["risque"] = Counter(l["risque"] for l in L).most_common(6)
    D["expo"] = Counter(l["expo"] for l in L).most_common()
    pyr = {"H": [0] * 8, "F": [0] * 8, "dH": [0] * 8, "dF": [0] * 8}
    for l in L:
        if l["age"] is None:
            continue
        t = next((i for i, (lo, hi) in enumerate(AGES) if lo <= l["age"] <= hi), 7)
        k = "F" if l["sexe"] == "F" else "H"
        pyr[k][t] += 1
        if l["issue"] == "Décès":
            pyr["d" + k][t] += 1
    D["pyr"] = pyr
    D["age_med"] = _med(l["age"] for l in L)
    D["femmes"] = sum(1 for l in L if l["sexe"] == "F")
    D["let_age"] = [round(100 * (pyr["dH"][i] + pyr["dF"][i]) / (pyr["H"][i] + pyr["F"][i])) if pyr["H"][i] + pyr["F"][i] else 0 for i in range(8)]
    D["funnel"] = [["Cas confirmés (fiches)", n], ["Notification datée", sum(1 for l in L if l["notif"])],
                   ["Prélèvement daté", sum(1 for l in L if l["prel"])], ["Résultat daté", sum(1 for l in L if l["res"])],
                   ["Isolement daté", sum(1 for l in L if l["iso"])]]
    D["delais"] = [[lab, _iqr(l[k] for l in L)] for lab, k in (("J0 → notification", "d_notif"), ("J0 → isolement", "d_iso"),
                                                             ("J0 → confirmation", "d_conf"), ("J0 → décès", "d_dc"))]
    D["delais"] = [d for d in D["delais"] if d[1]]
    D["lab_iqr"] = _iqr(l["d_lab"] for l in L)
    D["iso_zs"] = sorted([[z["zs"], z["d_iso"]] for z in Z if z["n"] >= 5 and z["d_iso"] is not None], key=lambda x: x[1])
    D["eds"] = [sum(1 for l in dc if l["eds"] is True), sum(1 for l in dc if l["eds"] is False), sum(1 for l in dc if l["eds"] is None)]
    v = lambda k: [l[k] for l in L if l[k] is not None]   # noqa: E731
    D["ct"] = {"listes": int(sum(v("cl"))), "haut": int(sum(v("ch"))), "suivis": int(sum(v("cs"))), "vaccines": int(sum(v("cv"))),
               "fiches_cl": len(v("cl")), "fiches_cs": len(v("cs")), "med": _med(v("cl")), "sans": sum(1 for l in L if l["cl"] is None),
               "dh_ok": sum(1 for l in L if l["dh_ok"]), "dh_tot": sum(1 for l in L if l["dh_ok"] is not None),
               "dh_n": int(sum(v("dh_n"))), "dh_cl": int(sum(l["cl"] for l in L if l["dh_n"] is not None and l["cl"] is not None)),
               "dh_diff": v("dh_diff")}
    D["chaines"], D["src_base"] = _chaines(L, ref)
    D["src_total"] = sum(1 for l in L if l["src"])
    tr = Counter(t for l in L for t in l["transports"])
    D["transports"] = tr.most_common(7)
    D["mob"] = {"depl": sum(1 for l in L if l["depl"]), "moy": round(st.mean(l["depl"] for l in L), 1), "fun": sum(1 for l in L if l["fun"]),
                "lieux": int(sum(l["lieux"] for l in L)), "etapes_med": _med(l["etapes"] for l in L)}
    D["depl_zs"] = sorted([[z, round(st.mean(l["depl"] for l in ls), 1)] for (p, z), ls in zsd.items() if len(ls) >= 5], key=lambda x: -x[1])[:8]
    D["pci"] = {"sites": sum(l["pci"] for l in L), "ok": sum(l["pci_ok"] for l in L), "non": sum(l["pci_non"] for l in L),
                "sans_site": sum(1 for l in L if not l["pci"]), "sanspci": sum(1 for l in L if l["sanspci"]),
                "corps": sum(1 for l in L if l["corps"]), "liq": sum(1 for l in L if l["liq"]), "ppl": D["kpi"]["ppl"]}
    D["pci_zs"] = [[z["zs"], z["pci"], z["pci_ok"]] for z in Z if z["pci"] >= 5][:9]
    D["sympt"] = _symptomes(cases)
    D["actions"] = {"total": sum(l["act"] for l in L), "fiches": sum(1 for l in L if l["act"]),
                    "dist": [sum(1 for l in L if l["act"] == k) for k in range(6)] + [sum(1 for l in L if l["act"] >= 6)]}
    D["risque_actions"] = [[r, sum(l["act"] for l in L if l["risque"] == r)] for r, _n in D["risque"]]
    champs = [("ID du cas", sum(1 for l in L if l["id"])), ("Date de notification", sum(1 for l in L if l["notif"])),
              ("Date d'isolement", sum(1 for l in L if l["iso"])), ("Prélèvement", sum(1 for l in L if l["prel"])),
              ("Contacts listés", len(v("cl"))), ("Contacts suivis", len(v("cs"))),
              ("Phase des premiers signes", sum(1 for l in L if l["phase"] in ("Phase sèche", "Phase humide", "Phase critique"))),
              ("Lien épidémiologique", sum(1 for l in L if l["lien"] != "Inconnu"))]
    D["champs"] = [[lab, round(100 * k / n)] for lab, k in champs]
    D["compl_dist"] = [sum(1 for l in L if lo <= l["compl"] < hi) for lo, hi in ((0, 50), (50, 70), (70, 90), (90, 101))]
    D["qualite"] = {"sans_id": sum(1 for l in L if not l["id"]), "nombre_impossible": sum(1 for l in L if l["aberrant"]),
                    "delai_aberrant": sum(1 for l in L if l["delai_hors"]), "date_aberrante": sum(1 for l in L if l["j0_hors"]),
                    "etat_non_harmonise": sum(1 for l in L if l["issue_libre"]), "lien_non_harmonise": sum(1 for l in L if l["lien_libre"]),
                    "zs_non_harmonisee": 0, "province_non_harmonisee": 0}
    D["dh_prov"] = [[p, sum(1 for l in L if l["prov"] == p and l["dh_ok"]), sum(1 for l in L if l["prov"] == p and l["dh_ok"] is not None)]
                    for p, _n in D["prov"][:5]]
    return D


def cartes(cases: List[Case], ref: Optional[date] = None, province: str = "", lien=None) -> dict:
    """Cartes SVG (délai depuis le dernier cas) : la RDC et les 3 provinces les plus touchées (ou la province filtrée)."""
    import re
    from core import carte
    ref = ref or date.today()
    cr = carte.construire(cases)
    def propre(s):
        s = re.sub(r'<text x="18" y="24"[^>]*>.*?</text><text x="18" y="40"[^>]*>.*?</text>', "", s, count=1, flags=re.S)
        return re.sub(r"(<title>[^<\n]*)\n[^<]*(</title>)", r"\1\2", s)      # info-bulles : nombres seulement, aucun ID de cas
    provs = [province] if province else [p for p, _n in Counter(c.province for c in cases if c.province).most_common(3)]
    out = {"nat": propre(carte.svg_niveau(cr, "national", ref=ref, width=900, height=760, lien=lien)), "prov": []}
    for p in provs:
        try:
            out["prov"].append([p, propre(carte.svg_niveau(cr, "province", province=p, ref=ref, width=900, height=660, lien=lien))])
        except Exception:
            continue
    return out
