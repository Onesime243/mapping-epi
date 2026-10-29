"""Frise temporelle (type Gantt) en jours relatifs au début des symptômes (J0) :
durée de chaque étape, fenêtres d'exposition et de contagiosité, décès,
circuit laboratoire et période de suivi des contacts."""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from config import theme
from core import rules
from core.models import Case
from render import svgkit as K
from render.html_renderer import date_label, render_svg_page


def render_svg(case: Case) -> str:
    w = rules.windows(case)
    p = rules.disease_params(case.maladie)
    rows = []   # (label, sublabel, start, end, color, kind)
    for ev in case.events:
        if not ev.date_debut:
            continue
        risk = rules.event_risk(ev, case, w)
        rows.append((ev.titre or ev.type, f"{date_label(ev)} • {ev.lieu}{' → ' + ev.lieu_arrivee if ev.lieu_arrivee else ''}",
                     ev.date_debut, ev.date_fin or ev.date_debut, theme.risk_color(risk), "event", ev.date_incertaine))
    for lab in case.labs:
        if lab.prelevement:
            end = (lab.resultat_le or lab.reception or lab.envoi or lab.prelevement).date()
            d = rules.lab_delay_hours(case)
            rows.append((f"Laboratoire ({lab.type})", f"délai prélèvement → résultat : {d:.0f} h" if d is not None else "délai non documenté",
                         lab.prelevement.date(), end, theme.TEAL, "lab", False))
    last_contacts = [g.dernier_contact for g in case.contacts if g.dernier_contact]
    follow_end: Optional[date] = None
    if last_contacts:
        first, last = min(last_contacts), max(last_contacts)
        follow_end = last + timedelta(days=int(p["suivi_contacts"]))
        rows.append((f"Suivi des contacts ({p['suivi_contacts']} j)", f"jusqu'au {follow_end:%d/%m/%Y}",
                     first, follow_end, theme.NAVY, "follow", False))

    dates: List[date] = [r[2] for r in rows] + [r[3] for r in rows]
    if w.exposition:
        dates += list(w.exposition)
    if w.contagiosite:
        dates += list(w.contagiosite)
    out = [K.svg_open(), K.header(
        f"FRISE TEMPORELLE – CAS {case.rang or ''} {case.maladie} | ZS {(case.zs or '?').upper()}",
        f"Jours relatifs au début des symptômes (J0) • incubation {p['incubation_min']}–{p['incubation_max']} j • "
        f"suivi des contacts {p['suivi_contacts']} j")]
    out.append(K.card(16, 66, 1248, 616))
    if not dates:
        out.append(f'<text x="640" y="380" text-anchor="middle" font-size="14" fill="{theme.MUTED}">'
                   'Aucune étape datée : renseignez les dates de la chronologie.</text></svg>')
        return "".join(out)
    d0, d1 = min(dates) - timedelta(days=1), max(dates) + timedelta(days=2)
    ndays = max((d1 - d0).days, 1)
    lx, x0, x1 = 30, 250, 1240
    top, bottom = 118, 640
    px = (x1 - x0) / ndays

    def X(d: date) -> float:
        return x0 + (d - d0).days * px

    # bandes
    if w.exposition:
        a, b = w.exposition
        out.append(f'<rect x="{X(a):.1f}" y="{top - 22}" width="{(X(b) - X(a) + px):.1f}" height="{bottom - top + 22}" fill="url(#hatch)"/>')
        out.append(f'<text x="{X(a) + 6:.1f}" y="{top - 9}" font-size="9" font-weight="800" fill="{theme.BLUE}">'
                   f'FENÊTRE D\'EXPOSITION</text>')
    if w.contagiosite:
        a, b = w.contagiosite
        out.append(f'<rect x="{X(a):.1f}" y="{top - 22}" width="{(X(b) - X(a) + px):.1f}" height="{bottom - top + 22}" '
                   f'fill="{theme.RED}" fill-opacity=".08"/>')
        out.append(f'<text x="{X(a) + 6:.1f}" y="{top - 9}" font-size="9" font-weight="800" fill="{theme.RED}">PÉRIODE CONTAGIEUSE</text>')
    # graduations
    step = 1 if ndays <= 25 else (2 if ndays <= 50 else (7 if ndays <= 150 else 14))
    d = d0
    i = 0
    while d <= d1:
        x = X(d)
        major = (i % step == 0)
        out.append(f'<line x1="{x:.1f}" y1="{top - 22}" x2="{x:.1f}" y2="{bottom}" stroke="{theme.BORDER}" '
                   f'stroke-width="{1 if major else .5}"/>')
        if major:
            out.append(f'<text x="{x + 2:.1f}" y="{bottom + 14}" font-size="8.5" fill="{theme.MUTED}">{d:%d/%m}</text>')
            if w.j0:
                out.append(f'<text x="{x + 2:.1f}" y="{bottom + 26}" font-size="8.5" font-weight="700" fill="{theme.NAVY}">'
                           f'{rules.relative_day(d, w.j0)}</text>')
        d += timedelta(days=1)
        i += 1
    # lignes repères
    marks = []
    if w.j0:
        marks.append((w.j0, "J0 début symptômes", theme.GREEN))
    if case.date_deces:
        marks.append((case.date_deces, "Décès", theme.RED))
    if case.date_confirmation:
        marks.append((case.date_confirmation, "Confirmation", theme.TEAL))
    if follow_end:
        marks.append((follow_end, "Fin du suivi", theme.NAVY))
    for k, (dd, lab, col) in enumerate(marks):
        x = X(dd) + px / 2
        out.append(f'<line x1="{x:.1f}" y1="{top - 22}" x2="{x:.1f}" y2="{bottom}" stroke="{col}" stroke-width="2" stroke-dasharray="5 3"/>')
        anchor, tx = ("end", x - 4) if x > x1 - 90 else ("start", x + 4)
        out.append(f'<text x="{tx:.1f}" y="{bottom - 4 - 12 * (k % 2)}" text-anchor="{anchor}" font-size="9" '
                   f'font-weight="800" fill="{col}">{K.esc(lab)}</text>')

    # lignes
    n = len(rows)
    rh = min(34, (bottom - top - 24) / max(n, 1))
    y = top
    for label, sub, a, b, col, kind, unc in rows:
        if kind == "follow":
            y += 8
        out.append(f'<text x="{lx}" y="{y + rh * .45:.1f}" font-size="{min(11, rh * .38):.1f}" font-weight="800" fill="{theme.TEXT}">{K.esc(label[:42])}</text>')
        out.append(f'<text x="{lx}" y="{y + rh * .45 + min(10, rh * .32):.1f}" font-size="{min(9, rh * .3):.1f}" fill="{theme.MUTED}">{K.esc(sub[:58])}</text>')
        bx, bw = X(a), max((b - a).days + 1, 1) * px
        h = rh * .58
        style = f'fill="{col}"'
        if kind == "follow":
            style = f'fill="{col}" fill-opacity=".18" stroke="{col}" stroke-width="1.5"'
        if unc:
            style += f' stroke="{col}" stroke-width="1.5" stroke-dasharray="4 3" fill-opacity=".45"'
        out.append(f'<rect x="{bx + 1:.1f}" y="{y + (rh - h) / 2:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" rx="{min(5, h / 2):.1f}" {style}>'
                   f'<title>{K.esc(label)} : {a:%d/%m} → {b:%d/%m}</title></rect>')
        y += rh
    out.append(K.footer("Barres pointillées = dates incertaines. Les bandes indiquent la fenêtre d'exposition probable "
                        "et la période contagieuse calculées à partir de J0 (paramètres dans config/diseases.yaml)."))
    out.append("</svg>")
    return "".join(out)


def render_html(case: Case) -> str:
    return render_svg_page(render_svg(case), "Frise temporelle")
