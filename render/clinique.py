"""Parcours clinique d'un cas : du premier symptôme au suivi du survivant, indépendant de la chronologie
épidémiologique. Étapes datées, délais cliniques, laboratoire successif et besoins du cas (statuts seulement).
Une date inconnue reste « ND » (jamais 0, jamais inventée)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from config import theme
from core.models import Case
from render import svgkit as K
from render.libelles import cas, tr, trf, val

GRIS = "#8B97A6"


def _j(a: Optional[date], b: Optional[date]) -> Optional[int]:
    return (b - a).days if a and b else None


def etapes(case: Case):
    pcr_neg = sorted([(l.resultat_le or l.prelevement).date() for l in case.labs
                      if l.resultat == "Négatif" and (l.resultat_le or l.prelevement)])
    deces = case.issue == "Décès"
    fin = [(tr("Décès"), case.date_deces, theme.RED)] if deces else [
        (tr("PCR négatives"), pcr_neg[-1] if len(pcr_neg) >= 2 else None, theme.GREEN),
        (tr("Sortie"), case.date_sortie, theme.GREEN),
        (tr("Suivi du survivant"), case.date_rdv_post_guerison, theme.GREEN)]
    return [(tr("Symptômes"), case.debut_symptomes, theme.BLUE),
            (tr("1re consultation"), case.date_premiere_consultation, theme.BLUE),
            (tr("Référence"), case.date_reference, theme.BLUE),
            (tr("Décision de transfert"), case.date_decision_transfert, theme.BLUE),
            (tr("Admission CTE"), case.date_admission_cte, theme.NAVY),
            (tr("Traitement"), case.date_debut_traitement, theme.NAVY)] + fin


def delais(case: Case):
    return [(tr("Symptômes → 1re consultation"), _j(case.debut_symptomes, case.date_premiere_consultation), 2),
            (tr("Confirmation → isolement"), _j(case.date_confirmation, case.date_isolement), 1),
            (tr("Décision de transfert → admission CTE"), _j(case.date_decision_transfert, case.date_admission_cte), 1),
            (tr("Admission → début du traitement"), _j(case.date_admission_cte, case.date_debut_traitement), 1),
            (tr("Durée de séjour au CTE"), _j(case.date_admission_cte, case.date_sortie or case.date_deces), None)]


def render_svg(case: Case) -> str:
    out = [K.svg_open(), K.header(
        trf("PARCOURS CLINIQUE – {cas} {maladie} | ZS {zs}", cas=cas(case).upper(), maladie=val(case.maladie),
            zs=(case.zs or '?').upper()),
        trf("État du cas : {etat} · bleu = documenté, vert/bleu foncé = pris en charge, gris = non documenté (ND)",
            etat=val(case.issue)))]
    # -- étapes
    et = etapes(case)
    out.append(K.card(16, 68, 1248, 170))
    out.append(f'<text x="32" y="92" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Du premier symptôme au suivi du survivant"))}</text>')
    n = len(et)
    w = (1216 - (n - 1) * 8) / n
    for i, (lab, d, col) in enumerate(et):
        x = 32 + i * (w + 8)
        c = col if d else GRIS
        out.append(f'<rect x="{x:.1f}" y="108" width="{w:.1f}" height="74" rx="9" fill="{c}"/>')
        lignes = K.wrap_px(lab, w - 10, 12, 800, 2)
        for k, l in enumerate(lignes):
            out.append(f'<text x="{x + w / 2:.1f}" y="{132 + 14 * k}" text-anchor="middle" font-size="12" font-weight="800" fill="#fff">{K.esc(l)}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="172" text-anchor="middle" font-size="12" fill="#fff">{K.esc(f"{d:%d/%m/%Y}" if d else "ND")}</text>')
    out.append(f'<text x="32" y="222" font-size="11" fill="#000">{K.esc(tr("ND = non documenté : à compléter à l'étape 2 Clinique (parcours de prise en charge) ou à l'étape 3 (dates clés)."))}</text>')

    # -- délais cliniques
    out.append(K.card(16, 250, 410, 450))
    out.append(f'<text x="32" y="274" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Délais cliniques"))}</text>')
    y = 300
    for lab, v, seuil in delais(case):
        out.append(f'<text x="32" y="{y}" font-size="12" fill="#000">{K.esc(K.ellipsize(lab, 260, 12))}</text>')
        if v is None:
            txt, col = "ND", GRIS
        else:
            txt = f"{v} j"
            col = theme.RED if seuil is not None and v > seuil else (theme.GREEN if seuil is not None else theme.NAVY)
        out.append(f'<text x="410" y="{y}" text-anchor="end" font-size="13" font-weight="800" fill="{col}">{K.esc(txt)}</text>')
        y += 30
    out.append(f'<text x="32" y="{y + 6}" font-size="10.5" fill="#000">{K.esc(tr("Rouge = au-delà du seuil (consultation 2 j, autres 1 j)."))}</text>')

    # -- laboratoire successif
    out.append(K.card(436, 250, 410, 450))
    out.append(f'<text x="452" y="274" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Laboratoire successif"))}</text>')
    labs = sorted([l for l in case.labs if (l.resultat_le or l.prelevement)], key=lambda l: l.resultat_le or l.prelevement)
    y = 300
    if not labs:
        out.append(f'<text x="452" y="{y}" font-size="12" fill="#000">{K.esc(tr("Aucun prélèvement saisi."))}</text>')
    for l in labs[:12]:
        d = (l.resultat_le or l.prelevement)
        col = {"Positif": theme.RED, "Négatif": theme.GREEN}.get(l.resultat, GRIS)
        out.append(f'<text x="452" y="{y}" font-size="12" fill="#000">{d:%d/%m/%Y} · {K.esc(val(l.type))}</text>')
        out.append(f'<text x="830" y="{y}" text-anchor="end" font-size="12.5" font-weight="800" fill="{col}">{K.esc(val(l.resultat) or "?")}</text>')
        y += 26
    out.append(f'<text x="452" y="680" font-size="10.5" fill="#000">{K.esc(tr("Deux PCR négatives ne changent pas l'état du cas : sortie validée par l'équipe."))}</text>')

    # -- besoins du cas
    out.append(K.card(856, 250, 408, 450))
    out.append(f'<text x="872" y="274" font-size="14" font-weight="800" fill="{theme.NAVY}">{K.esc(tr("Besoins du cas"))}</text>')
    y = 302
    coul = {"Documenté": theme.GREEN, "Satisfait": theme.GREEN, "Sans objet": GRIS, "À vérifier": theme.ORANGE,
            "À planifier": theme.ORANGE, "Besoin identifié": theme.ORANGE, "Évaluation en cours": theme.BLUE,
            "Soutien en cours": theme.BLUE, "Référé": theme.BLUE, "Non évalué": GRIS}
    for k, lab in theme.BESOINS_CSSE + theme.BESOINS_PSY:
        v = getattr(case, k) or ""
        out.append(f'<text x="872" y="{y}" font-size="12" fill="#000">{K.esc(K.ellipsize(tr(lab), 220, 12))}</text>')
        t = val(v) if v else tr("Non renseigné")
        out.append(f'<text x="1248" y="{y}" text-anchor="end" font-size="12" font-weight="800" fill="{coul.get(v, GRIS)}">{K.esc(t)}</text>')
        y += 30
    out.append(f'<text x="872" y="680" font-size="10.5" fill="#000">{K.esc(tr("Statuts seulement : le détail reste chez chaque pilier."))}</text>')
    out.append("</svg>")
    return "".join(out)
