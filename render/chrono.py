"""Chronologie simplifiée d'un cas : les événements clés seulement (exposition, deux J0, alerte, investigation,
notification, prélèvement, confirmation, isolement, admission au CTE, issue), à intervalles réguliers
(axe non proportionnel au temps), avec les délais clés, la cascade des contacts et les points à vérifier.

Le mapping reste le résumé d'une page ; cette vue est l'aperçu de travail, moins dense.
Une date inconnue n'est jamais inventée : l'événement est listé « non renseigné ».
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Tuple

from config import theme
from core import rules
from core.models import Case
from render import svgkit as K
from render.libelles import cas, jour, regle, tr, trf, val

GRIS = "#8B97A6"


def _jours(a: Optional[date], b: Optional[date]) -> Optional[int]:
    return (b - a).days if a and b else None


def _fd(d: Optional[date]) -> str:
    return f"{d:%d/%m/%Y}" if d else "?"


def evenements(case: Case) -> Tuple[List[Tuple[str, date, str, str]], List[str]]:
    """(libellé, date, couleur, note) des événements clés datés, triés ; et libellés des événements non renseignés."""
    ph = rules.phases(case)
    j0 = ph.j0
    prelev = min((l.prelevement.date() for l in case.labs if l.prelevement), default=None)
    expo = case.date_contact_source if case.contact_connu in theme.CONTACT_AVEC_SOURCE else None
    conf = case.date_confirmation
    iso_retard = bool(conf and case.date_isolement and (case.date_isolement - conf).days > 1)
    cle = [
        (tr("Dernière exposition"), expo, GRIS, "", case.contact_connu in theme.CONTACT_AVEC_SOURCE),
        (tr("J0 retenu"), j0 if j0 != case.debut_symptomes else None, theme.YELLOW, trf("rapporté − {n} j", n=ph.recul), False),
        (tr("J0 rapporté"), case.debut_symptomes, theme.BLUE, "", True),
        (tr("Alerte"), case.date_alerte, theme.BLUE, "", True),
        (tr("Investigation"), case.date_investigation, theme.BLUE, "", True),
        (tr("Notification"), case.date_notification, theme.BLUE, "", True),
        (tr("Prélèvement"), prelev, theme.BLUE, "", False),
        (tr("Confirmation"), conf, theme.NAVY, "", True),
        (tr("Isolement effectif"), case.date_isolement, theme.RED if iso_retard else theme.GREEN,
         trf("{n} j après confirmation", n=(case.date_isolement - conf).days) if iso_retard else "", True),
        (tr("Admission au CTE"), case.date_admission_cte, theme.GREEN, "", True),
        (tr("Décès"), case.date_deces, theme.RED, "", case.issue == "Décès"),
    ]
    dates = [(lab, d, col, note) for lab, d, col, note, _o in cle if d]
    manquants = [lab for lab, d, _c, _n, obligatoire in cle if not d and obligatoire]
    ordre = {lab: i for i, (lab, *_r) in enumerate(cle)}
    dates.sort(key=lambda e: (e[1], ordre[e[0]]))
    return dates, manquants


def _dhis2(case: Case) -> Optional[int]:
    from core import dhis2
    return dhis2.rapprochement(case)["dhis2"]


def cascade(case: Case) -> List[Tuple[str, Optional[int], str]]:
    def som(k):
        v = [getattr(g, k) for g in case.contacts if getattr(g, k) is not None]
        return sum(v) if v else None
    return [(tr("Exposés estimés"), som("exposes"), GRIS), (tr("Listés"), som("nombre"), theme.BLUE),
            (tr("Suivis"), som("suivis"), theme.GREEN), (tr("Devenus symptomatiques"), som("symptomatiques"), theme.ORANGE),
            (tr("Devenus confirmés"), som("confirmes"), theme.RED),
            (tr("Listés dans DHIS2"), _dhis2(case), theme.NAVY),
            (tr("Suivis dans DHIS2"), case.contacts_dhis2_suivis, theme.TEAL)]


def _tuile(x, y, w, h, titre, valeur, note, couleur=theme.NAVY) -> str:
    v = K.ellipsize(valeur, w - 28, 26, 800)
    size = 26
    out = [K.card(x, y, w, h),
           f'<text x="{x + 14}" y="{y + 22}" font-size="10" font-weight="800" letter-spacing=".5" fill="#5D6A79">'
           f'{K.esc(K.ellipsize(titre.upper(), w - 28, 10, 800))}</text>',
           f'<text x="{x + 14}" y="{y + 54}" font-size="{size}" font-weight="800" fill="{couleur}">{K.esc(v)}</text>']
    for i, ligne in enumerate(K.wrap_px(note, w - 28, 10.5, 400, 2)):
        out.append(f'<text x="{x + 14}" y="{y + 72 + 13 * i}" font-size="10.5" fill="#000">{K.esc(ligne)}</text>')
    return "".join(out)


def render_svg(case: Case) -> str:
    ph = rules.phases(case)
    out = [K.svg_open(), K.header(
        trf("CHRONOLOGIE SIMPLIFIÉE – {cas} {maladie} | ZS {zs}", cas=cas(case).upper(), maladie=val(case.maladie),
            zs=(case.zs or '?').upper()),
        tr("Événements clés seulement · J0 rapporté et J0 retenu · axe non proportionnel au temps · le mapping garde le détail"))]

    # -- indicateurs
    grisk, _why = rules.global_risk(case)
    a = _jours(case.debut_symptomes, case.date_confirmation)
    b = _jours(ph.j0, case.date_confirmation) if ph.j0 != case.debut_symptomes else None
    iso = _jours(case.date_confirmation, case.date_isolement)
    casc = cascade(case)
    listes, suivis = casc[1][1], casc[2][1]
    tw, gap, x = 238, 14, 16
    tuiles = [
        (tr("Risque global"), val(grisk), "", theme.risk_color(grisk)),
        (tr("Signes → confirmation"), "?" if a is None else (f"{a} j" + (f" / {b} j" if b is not None else "")),
         tr("J0 rapporté / J0 retenu") if b is not None else tr("depuis le J0 rapporté"), theme.NAVY),
        (tr("Confirmation → isolement"), "?" if iso is None else f"{iso} j",
         tr("seuil 1 j : à expliquer") if iso is not None and iso > 1 else ("" if iso is not None else tr("isolement non renseigné")),
         theme.RED if iso is not None and iso > 1 else theme.NAVY),
        (tr("Contacts listés"), "?" if listes is None else str(listes),
         trf("suivis : {n}", n="?" if suivis is None else suivis) + (tr(" · à réconcilier") if listes and suivis == 0 else ""),
         theme.NAVY),
        (tr("État du cas"), val(case.issue), trf("admission CTE : {d}", d=_fd(case.date_admission_cte)), theme.NAVY),
    ]
    for i, (t, v, n, c) in enumerate(tuiles):
        out.append(_tuile(x + i * (tw + gap), 68, tw, 100, t, v, n, c))

    # -- frise des événements clés
    evs, manquants = evenements(case)
    out.append(K.card(16, 180, 1248, 270))
    out.append(f'<text x="32" y="204" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Événements clés"))}</text>')
    if evs:
        x0, x1, yl = 80, 1200, 318
        pas = (x1 - x0) / max(len(evs) - 1, 1) if len(evs) > 1 else 0
        xs = [x0 + i * pas for i in range(len(evs))] if len(evs) > 1 else [640]
        out.append(f'<line x1="{xs[0]:.0f}" y1="{yl}" x2="{xs[-1]:.0f}" y2="{yl}" stroke="#C9D3DE" stroke-width="4"/>')
        for i, ((lab, d, col, note), xx) in enumerate(zip(evs, xs)):
            haut = i % 2 == 0
            ylab = yl - 62 if haut else yl + 40
            out.append(f'<line x1="{xx:.0f}" y1="{yl}" x2="{xx:.0f}" y2="{yl - 20 if haut else yl + 20}" stroke="#C9D3DE" stroke-width="1.5"/>')
            out.append(f'<circle cx="{xx:.0f}" cy="{yl}" r="10" fill="{col}" stroke="#fff" stroke-width="3"/>')
            lw = max(min(pas - 6, 150), 90) if pas else 150
            out.append(f'<text x="{xx:.0f}" y="{ylab}" text-anchor="middle" font-size="12" font-weight="800" fill="#000">'
                       f'{K.esc(K.ellipsize(lab, lw, 12, 800))}</text>')
            rel = jour(rules.relative_day(d, ph.j0)) if ph.j0 else ""
            out.append(f'<text x="{xx:.0f}" y="{ylab + 15}" text-anchor="middle" font-size="11" fill="#000">'
                       f'{K.esc(f"{d:%d/%m}" + (" · " + rel if rel else ""))}</text>')
            if note:
                out.append(f'<text x="{xx:.0f}" y="{ylab + 29}" text-anchor="middle" font-size="10" font-weight="700" fill="{col}">'
                           f'{K.esc(K.ellipsize(note, lw, 10, 700))}</text>')
    else:
        out.append(f'<text x="640" y="318" text-anchor="middle" font-size="14" fill="#000">'
                   f'{K.esc(tr("Aucune date clé saisie : renseignez les dates (étapes 1 à 3)."))}</text>')
    if manquants:
        txt = tr("Non renseigné : ") + ", ".join(manquants)
        out.append(f'<text x="32" y="436" font-size="11" fill="{theme.RED}" font-weight="700">{K.esc(K.ellipsize(txt, 1210, 11, 700))}</text>')

    # -- cascade des contacts
    out.append(K.card(16, 462, 616, 238))
    out.append(f'<text x="32" y="486" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Cascade des contacts"))}</text>')
    out.append(f'<text x="616" y="486" text-anchor="end" font-size="10" fill="#000">{K.esc(tr("chaque nombre est saisi, jamais déduit"))}</text>')
    vmax = max([n for _l, n, _c in casc if n is not None] + [1])
    for i, (lab, n, col) in enumerate(casc):
        y = 506 + i * 26
        out.append(f'<text x="32" y="{y + 12}" font-size="12" fill="#000">{K.esc(lab)}</text>')
        out.append(f'<rect x="220" y="{y + 2}" width="330" height="13" rx="6" fill="#E8EDF2"/>')
        if n:
            out.append(f'<rect x="220" y="{y + 2}" width="{max(4, 330 * n / vmax):.0f}" height="13" rx="6" fill="{col}"/>')
        out.append(f'<text x="616" y="{y + 13}" text-anchor="end" font-size="12.5" font-weight="800" fill="#000">'
                   f'{"?" if n is None else n}</text>')

    # -- points à vérifier
    out.append(K.card(646, 462, 618, 238))
    out.append(f'<text x="662" y="486" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Points à vérifier"))}</text>')
    pts = [i for i in rules.check_consistency(case) if i.niveau in ("erreur", "alerte")]
    if not pts:
        out.append(f'<text x="662" y="514" font-size="12" fill="{theme.GREEN}" font-weight="700">'
                   f'{K.esc(tr("Aucune incohérence détectée dans les dates et les nombres."))}</text>')
    y = 506
    for it in pts:
        lignes = K.wrap_px(regle(it.message), 560, 11.5, 400, 2)
        if y + 14 * len(lignes) > 694:
            out.append(f'<text x="662" y="{y + 10}" font-size="11" fill="#000">{K.esc(trf("… et {n} autre(s) : voir Contrôles", n=len(pts) - pts.index(it)))}</text>')
            break
        col = theme.RED if it.niveau == "erreur" else theme.ORANGE
        out.append(f'<circle cx="668" cy="{y + 6}" r="4" fill="{col}"/>')
        for k, l in enumerate(lignes):
            out.append(f'<text x="680" y="{y + 10 + 14 * k}" font-size="11.5" fill="#000">{K.esc(l)}</text>')
        y += 14 * len(lignes) + 6
    out.append("</svg>")
    return "".join(out)
