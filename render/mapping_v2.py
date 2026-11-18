"""Données du mapping repensé : en-tête à trois chiffres, frise à l'échelle du temps, blocs Contacts / PCI / Actions.

Principe : le mapping répond en quelques secondes à « qui est à risque ? », « qu'est-ce qui manque ? » et
« qui doit faire quoi ? ». Le rouge est réservé au danger, l'orange à ce qui manque ; chaque couleur est doublée
d'un symbole ou d'un mot (daltonisme, impression en noir et blanc). Rien n'est inventé : une donnée absente
s'affiche « ? » ou « à compléter ».
"""
from __future__ import annotations

import unicodedata
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from config import theme
from core import rules
from core.models import Case
from render.libelles import en, jour, regle, tr, trf, val

SEUIL_CONFIRMATION = 5          # jours entre premiers signes et confirmation (même seuil que le tableau de bord)

# couleurs franches pour le risque, avec un symbole (lisible sans la couleur)
RISQUE = {
    "Très élevé": ("#B3262C", "▲▲"), "Élevé": ("#C9601C", "▲"), "Modéré": ("#9A7406", "●"),
    "Faible": ("#2E7D4F", "▽"), "Contrôlé": ("#2E7D4F", "✓"), "En cours": ("#3E6FA8", "…"),
    "Inconnu": ("#6B7586", "?"), "À investiguer": ("#6B7586", "?"),
}
CONTACT_RISQUE = {"Très haut": "#B3262C", "Haut": "#C9601C", "Modéré": "#9A7406", "Faible": "#2E7D4F",
                  "Inconnu": "#6B7586"}
PHASE_STYLE = {          # fond, texte
    "infection": ("#DCE3EC", "#2B3A55"), "seche": ("#F1E3B8", "#5A4500"), "humide": ("#EBC9A8", "#5C2E07"),
    "critique": ("#7A2E3A", "#FFFFFF"), "symptomes": ("#F1E3B8", "#5A4500"), "deces": ("#3F1820", "#FFFFFF"),
}
PCI_STYLE = {"Décontaminé": ("#D7EEDF", "#1F5E3A", "✓"), "Partiel": ("#F8E3CC", "#7A3E06", "◐"),
             "Non": ("#F6DADB", "#8E1F24", "✗"), "Inconnu": ("#E6E9EE", "#46505E", "?")}
PRIO = {"Urgent": "#B3262C", "Important": "#C9601C", "Normal": "#3E6FA8"}


def _dm(d: Optional[date]) -> str:
    return f"{d:%d/%m}" if d else "?"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in s).split())


def risque(level: str) -> dict:
    c, sym = RISQUE.get(level, ("#6B7586", "?"))
    return {"t": val(level or "Inconnu"), "c": c, "s": sym}


# -- en-tête ---------------------------------------------------------------------------------------------------------
def _hero(case: Case, ph, grisk: str, why: str) -> List[dict]:
    from core import riposte as R
    r = risque(grisk)
    out = [{"k": tr("Risque"), "v": f"{r['s']} {val(grisk)}", "s": regle(why or "")[:70], "bg": r["c"], "fg": "#FFFFFF"}]
    if case.issue == "Décès":
        rel = rules.relative_day(case.date_deces, case.debut_symptomes) if case.date_deces and case.debut_symptomes else ""
        comm = R.deces_communautaire(case)
        detail = " · ".join(x for x in (jour(rel), tr("hors structure de soins") if comm else (tr("en structure de soins") if comm is False else "")) if x)
        out.append({"k": tr("Issue"), "v": f"† {tr('Décès')} {_dm(case.date_deces)}" if case.date_deces else f"† {tr('Décès')}",
                    "s": detail or tr("date du décès à compléter"), "bg": "#2A3D5F", "fg": "#FFFFFF"})
    else:
        out.append({"k": tr("Issue"), "v": val(case.issue) if case.issue != "Inconnu" else tr("? à compléter"),
                    "s": tr("état du cas"), "bg": "#2A3D5F", "fg": "#FFFFFF"})
    if case.debut_symptomes and case.date_confirmation and case.date_confirmation >= case.debut_symptomes:
        n = (case.date_confirmation - case.debut_symptomes).days
        if n > SEUIL_CONFIRMATION:
            bg, fg = "#F2B705", "#2B2100"
        else:
            bg, fg = "#2E7D4F", "#FFFFFF"
        out.append({"k": tr("Signes → confirmation"), "v": trf("{n} jours", n=n) if n > 1 else trf("{n} jour", n=n),
                    "s": trf("seuil d’alerte : {n} jours", n=SEUIL_CONFIRMATION), "bg": bg, "fg": fg})
    else:
        out.append({"k": tr("Signes → confirmation"), "v": tr("? à compléter"),
                    "s": tr("début des symptômes ou confirmation manquant"), "bg": "#E6E9EE", "fg": "#2B3A55"})
    return out


def _sous_titre(case: Case) -> str:
    bits = []
    if case.code_cas.strip():
        bits.append(f"ID {case.code_cas.strip()}")
    ident = ", ".join(x for x in (case.sexe if case.sexe != "Inconnu" else "",
                                   f"{case.age} {val(case.age_unite)}" if case.age is not None else "") if x)
    if ident:
        bits.append(ident)
    if case.aire_sante:
        bits.append(f"{tr('AS')} {case.aire_sante}")
    bits.append(tr({"Oui": "Vacciné", "Non": "Non vacciné"}.get(case.vaccine, "Vaccination ?")))
    bits.append(tr({"Oui": "Agent de santé", "Non": "Agent de santé : non"}.get(case.agent_sante, "Agent de santé ?")))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE:
        bits.append(trf("{statut} de {src}", statut=val(case.contact_connu), src=case.id_cas_source.strip() or "?"))
    elif case.contact_connu and case.contact_connu != "Inconnu":
        bits.append(val(case.contact_connu))
    else:
        bits.append(tr("Lien avec un cas connu : inconnu"))
    return " · ".join(bits)


def _dates(case: Case, ph, score: int) -> List[dict]:
    out = []
    if ph.exposition:
        d1, d2 = ph.exposition
        out.append({"k": tr("Exposition"), "v": _dm(d1) if d1 == d2 else f"{_dm(d1)}→{_dm(d2)}"})
    out.append({"k": jour(tr("J0 rapporté")), "v": _dm(case.debut_symptomes)})
    if ph.j0 and ph.j0 != case.debut_symptomes:
        out.append({"k": jour(tr("J0 retenu")), "v": _dm(ph.j0), "x": trf("(−{n} j)", n=ph.recul) if ph.recul else tr("(estimé)")})
    if case.date_notification:
        x = rules.relative_day(case.date_notification, case.debut_symptomes) if case.debut_symptomes else ""
        out.append({"k": tr("Notifié"), "v": _dm(case.date_notification), "x": f"({jour(x)})" if x else ""})
    prel = [l.prelevement.date() for l in case.labs if l.prelevement]
    if prel:
        out.append({"k": tr("Prélevé"), "v": _dm(min(prel))})
    out.append({"k": val(case.statut), "v": _dm(case.date_confirmation)})
    ent = [e for e in case.events if e.type == "Enterrement" and e.date_debut]
    if ent:
        e = ent[0]
        out.append({"k": tr("Enterré"), "v": _dm(e.date_debut), "x": tr("(sécurisé)") if e.securise else tr("(non sécurisé)")})
    out.append({"k": tr("Complétude"), "v": f"{score} %"})
    return out


def _a_completer(case: Case, cards) -> List[str]:
    out = []
    n = sum(1 for g in case.contacts if g.nombre is None)
    if n:
        out.append(trf("{n} groupe de contacts à dénombrer", n=n) if n == 1 else trf("{n} groupes de contacts à dénombrer", n=n))
    n = sum(1 for c in cards if any(ch.get("todo") for ch in c.chips))
    if n:
        out.append(trf("{n} étapes sans personnes", n=n) if n > 1 else trf("{n} étape sans personnes", n=n))
    if case.contact_connu in theme.CONTACT_AVEC_SOURCE and not case.id_cas_source.strip():
        out.append(tr("ID du cas source"))
    if not case.events:
        out.append(tr("chronologie vide"))
    return out


# -- frise à l'échelle du temps -------------------------------------------------------------------------------------
def _frise(case: Case, ph, cards) -> Optional[dict]:
    evs = [(e, c) for e, c in zip(case.events, cards) if e.date_debut]
    jours = [e.date_debut for e, _ in evs] + [e.date_fin for e, _ in evs if e.date_fin]
    for d in (ph.exposition[0] if ph.exposition else None, ph.j0, case.date_confirmation, ph.deces):
        if d:
            jours.append(d)
    if not jours:
        return None
    d0, d1 = min(jours) - timedelta(days=1), max(jours) + timedelta(days=1)
    nb = (d1 - d0).days + 1
    if nb > 400:                      # dates aberrantes : pas de frise plutôt qu'une frise illisible
        return None
    # échelle adaptée : un jour sans étape vaut 1, un jour chargé est agrandi (jusqu'à 7)
    par_jour: Dict[date, int] = {}
    for e, _ in evs:
        par_jour[e.date_debut] = par_jour.get(e.date_debut, 0) + 1
    poids = [1 + 2 * min(par_jour.get(d0 + timedelta(days=i), 0), 3) for i in range(nb)]
    total = float(sum(poids))
    cumul = [0.0]
    for p in poids:
        cumul.append(cumul[-1] + p)

    def x(d: date, fin_de_jour: bool = False) -> float:
        i = max(0, min(nb, (d - d0).days + (1 if fin_de_jour else 0)))
        return round(100 * cumul[i] / total, 3)

    def xc(d: date) -> float:          # milieu du jour
        i = max(0, min(nb - 1, (d - d0).days))
        return round(100 * (cumul[i] + poids[i] / 2) / total, 3)

    adapte = max(poids) > 1 and nb > 7
    # bandes de phases
    bandes = []
    def bande(cle, a, b, libelle):
        if a and b and b >= a:
            bg, fg = PHASE_STYLE.get(cle, ("#E6E9EE", "#2B3A55"))
            w_ = max(0.6, x(b, True) - x(a))
            court = tr({"infection": "Exposition", "seche": "Sèche", "humide": "Humide", "critique": "Critique",
                        "symptomes": "Contagieux", "deces": "Corps contagieux"}.get(cle, libelle))
            libelle = tr(libelle)
            bandes.append({"l": x(a), "w": w_, "bg": bg, "fg": fg, "t": libelle if w_ * 12.8 > len(libelle) * 6.2 else court})
    fin_vie = ph.deces or max(jours)
    if ph.exposition:
        e1, e2 = ph.exposition
        bande("infection", max(e1, d0), min(e2, d1), trf("Exposition {d1}→{d2}", d1=_dm(e1), d2=_dm(e2)))
    if ph.j0:
        # phases successives : chacune s'arrête la veille de la suivante (deux phases le même jour : la plus grave)
        suite = []
        if ph.deux_phases:
            suite = [("seche", ph.j0, "Phase sèche · contagieux dès la fièvre"),
                     ("humide", ph.humide, "Phase humide · très contagieux"),
                     ("critique", ph.critique, "Phase critique")]
        else:
            suite = [("symptomes", ph.j0, "Période contagieuse")]
        suite = [s_ for s_ in suite if s_[1]]
        propre = []
        for s_ in suite:
            if propre and s_[1] <= propre[-1][1]:
                propre[-1] = s_ if s_[1] == propre[-1][1] else propre[-1]
                continue
            propre.append(s_)
        for i, (cle, debut, lib) in enumerate(propre):
            fin_b = (propre[i + 1][1] - timedelta(days=1)) if i + 1 < len(propre) else (
                (ph.deces - timedelta(days=1)) if ph.deces else fin_vie)
            bande(cle, debut, fin_b, lib)
    if ph.deces:
        ent = [e.date_debut for e in case.events if e.type == "Enterrement" and e.date_debut]
        bande("deces", ph.deces, max(ent) if ent else ph.deces, "Corps très contagieux")
    # trou le plus long sans information, après le J0 (une « période à documenter » ne compte pas comme information)
    couvert = set()
    for e, _ in evs:
        if e.type == "Période à documenter":
            continue
        f = e.date_fin or e.date_debut
        for i in range((f - e.date_debut).days + 1):
            couvert.add(e.date_debut + timedelta(days=i))
    trou = None
    depart = ph.j0 or min(jours)
    fin = max(e.date_debut for e, _ in evs) if evs else depart
    d, run = depart, None
    while d <= fin:
        if d not in couvert:
            run = (run[0], d) if run else (d, d)
        else:
            if run and (not trou or (run[1] - run[0]) > (trou[1] - trou[0])):
                trou = run
            run = None
        d += timedelta(days=1)
    if run and (not trou or (run[1] - run[0]) > (trou[1] - trou[0])):
        trou = run
    trou_v = None
    if trou and (trou[1] - trou[0]).days + 1 >= 4:
        n = (trou[1] - trou[0]).days + 1
        trou_v = {"l": x(trou[0]), "w": x(trou[1], True) - x(trou[0]), "t": "? " + trf("{n} jours sans information", n=n)}
    # points des étapes (décalés quand plusieurs le même jour)
    points, vus = [], {}
    for e, c in evs:
        k = e.date_debut
        i = vus.get(k, 0)
        vus[k] = i + 1
        n = par_jour.get(k, 1)
        largeur = 100 * poids[(k - d0).days] / total
        pos = x(k) + largeur * (i + 0.5) / n
        points.append({"x": round(pos, 3), "c": risque(c.risk)["c"], "t": f"{c.date} · {c.title}"})
    # graduations : chaque jour s'il y a la place, sinon chaque lundi
    ticks = []
    for i in range(nb):
        d = d0 + timedelta(days=i)
        if poids[i] > 1 or d.weekday() == 0 or i in (0, nb - 1) or nb <= 14:
            ticks.append({"x": xc(d), "t": _dm(d)})
    filtres, dernier = [], -100.0
    for t in ticks:                   # pas deux étiquettes à moins de 4,2 % l'une de l'autre
        if t["x"] - dernier >= 4.2:
            filtres.append(t)
            dernier = t["x"]
    reperes = []
    if case.date_confirmation and d0 <= case.date_confirmation <= d1:
        reperes.append({"x": xc(case.date_confirmation), "t": tr("Confirmation")})
    return {"bandes": bandes, "trou": trou_v, "points": points, "ticks": filtres, "reperes": reperes,
            "adapte": adapte}


# -- blocs du bas -----------------------------------------------------------------------------------------------------
def _contacts(case: Case) -> dict:
    connus = [g.nombre for g in case.contacts if g.nombre is not None]
    m = max(connus) if connus else 1
    lignes = []
    for g in case.contacts:
        lignes.append({"t": val(g.categorie) or "?", "n": g.nombre, "s": g.suivis,
                       "w": 0 if g.nombre is None else round(100 * g.nombre / m), "c": CONTACT_RISQUE.get(g.risque, "#6B7586")})
    cs = rules.contact_summary(case)
    suivis = sum(g.suivis for g in case.contacts if g.suivis is not None)
    a_suivi = any(g.suivis is not None for g in case.contacts)
    resume = trf("{n} à haut risque · suivis : {s}", n=cs.haut_risque_connu, s=suivis if a_suivi else tr("non renseigné"))
    return {"lignes": lignes, "resume": resume}


def _pci(case: Case) -> dict:
    sites = [{"t": s.site or "?", "st": s.statut, "bg": PCI_STYLE.get(s.statut, PCI_STYLE["Inconnu"])[0],
              "fg": PCI_STYLE.get(s.statut, PCI_STYLE["Inconnu"])[1],
              "lib": f"{PCI_STYLE.get(s.statut, PCI_STYLE['Inconnu'])[2]} "
                     + tr({"Décontaminé": "Décontaminé", "Partiel": "Partiel", "Non": "Non fait"}.get(s.statut, "Inconnu"))}
             for s in case.ipc]
    noms = [_norm(s.site) for s in case.ipc if s.site.strip()]
    sans = []
    for p in case.places:
        n = _norm(p.nom)
        if n and not any(n in s or s in n for s in noms):
            sans.append(p.nom)
    ok = sum(1 for s in case.ipc if s.statut == "Décontaminé")
    return {"sites": sites, "sans": sans,
            "resume": (trf("{ok} sur {n} décontaminés", ok=ok, n=len(case.ipc)) if ok > 1
                       else trf("{ok} sur {n} décontaminé", ok=ok, n=len(case.ipc)))
            if case.ipc else tr("aucun site renseigné")}


def _actions(case: Case) -> dict:
    if case.actions and any(a.texte.strip() for a in case.actions):
        ordre = {k: i for i, k in enumerate(theme.ACTION_PRIORITY_CHOICES)}
        acts = sorted((a for a in case.actions if a.texte.strip()),
                      key=lambda a: (a.statut == "Fait", ordre.get(a.priorite, 9)))
        lignes = [{"p": val(a.priorite), "c": PRIO.get(a.priorite, "#3E6FA8"), "t": val(a.texte), "fait": a.statut == "Fait",
                   "cours": a.statut == "En cours", "resp": a.responsable.strip(),
                   "ech": _dm(a.echeance) if a.echeance else ""} for a in acts]
        return {"lignes": lignes, "auto": False}
    lignes = [{"p": val(s.priorite), "c": PRIO.get(s.priorite, "#3E6FA8"), "t": regle(s.texte), "fait": False, "cours": False,
               "resp": "", "ech": ""} for s in rules.suggest_actions(case)[:6]]
    return {"lignes": lignes, "auto": True}


def _icone_personnes() -> str:
    from render.icons import icon_svg
    return icon_svg("people", 10, "#8A4B00", 2.2)


def vue(case: Case, ph, cards, grisk: str, why: str, score: int) -> dict:
    statut = {"Confirmé": "cas confirmé", "Probable": "cas probable", "Suspect": "cas suspect"}.get(case.statut, case.statut.lower())
    rang = f"{'1er' if case.rang == 1 else f'{case.rang}e'} " if case.rang else ""
    titre = f"Parcours thérapeutique · {rang}{statut} {case.maladie} · ZS {case.zs or '?'}"
    if en():
        from render.html_renderer import ordinal
        st_en = {"Confirmé": "confirmed", "Probable": "probable", "Suspect": "suspected"}.get(case.statut, val(case.statut).lower())
        titre = (f"Care pathway · {ordinal(case.rang) + ' ' if case.rang else ''}{st_en} {val(case.maladie)} case"
                 f" · HZ {case.zs or '?'}")
    return {
        "titre": titre,
        "sous": _sous_titre(case),
        "hero": _hero(case, ph, grisk, why),
        "dates": _dates(case, ph, score),
        "manque": _a_completer(case, cards),
        "frise": _frise(case, ph, cards),
        "cartes": [{"date": c.date, "rel": jour(c.rel), "lieu": c.place, "titre": c.title, "desc": c.desc,
                    "icon": c.icon, "tc": c.type_color,                  # icône et couleur du type d'étape
                    "r": risque(c.risk), "personnes": any(ch.get("todo") for ch in c.chips),
                    "chips": [ch for ch in c.chips if not ch.get("todo")][:3], "incertain": c.uncertain}
                   for c in cards],
        "icone_personnes": _icone_personnes(),
        "contacts": _contacts(case),
        "pci": _pci(case),
        "actions": _actions(case),
    }
