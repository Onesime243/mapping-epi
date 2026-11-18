"""Lieux les plus fréquentés par les cas d'une zone ou d'une aire de santé (classement en barres).

Un lieu fréquenté par plusieurs cas oriente l'investigation (source commune possible, site à décontaminer
en priorité, sensibilisation ciblée) ; il ne prouve pas à lui seul une transmission."""
from __future__ import annotations

from typing import List

from config import theme
from core.lieux import LieuFrequente, frequentes
from core.models import Case
from render import svgkit as K
from render.html_renderer import render_svg_page
from render.libelles import cas, titre_zone, tr, trf, val


def _cas(L: LieuFrequente) -> str:
    seen = {}
    for c in L.cas:
        seen[cas(c)] = seen.get(cas(c), 0) + 1
    return ", ".join(f"{k} ×{v}" if v > 1 else k for k, v in seen.items())


def render_svg(cases: List[Case], titre: str = "LIEUX LES PLUS FRÉQUENTÉS", min_cas: int = 2) -> str:
    lieux = frequentes(cases, min_cas=min_cas)
    out = [K.svg_open(), K.header(titre_zone(titre), trf("{n} cas • lieux mentionnés dans les fiches (chronologie et lieux), "
                                                     "fréquentés par au moins {m} cas • couleur = risque le plus élevé observé",
                                                     n=len(cases), m=min_cas))]
    out.append(K.card(16, 66, 1248, 616))
    if not lieux:
        out.append(f'<text x="640" y="370" text-anchor="middle" font-size="15" fill="{theme.MUTED}">'
                   f'{K.esc(trf("Aucun lieu fréquenté par au moins {m} cas dans cette sélection.", m=min_cas))}</text>')
    top = lieux[:14]
    xl, wl = 34, 300          # colonne des noms
    xb, wb = 346, 420         # barres
    xc = 790                  # colonne des cas
    head_y = 96
    for x, t in ((xl, "LIEU"), (xb, "NOMBRE DE CAS"), (xc, "CAS • PÉRIODE • AIRES DE SANTÉ")):
        out.append(f'<text x="{x}" y="{head_y}" font-size="9" font-weight="800" fill="#000000" letter-spacing=".6">{K.esc(tr(t))}</text>')
    nmax = max((L.n_cas for L in top), default=1)
    rh = min(38, (640 - 112) / max(1, len(top)))
    y = 108
    for i, L in enumerate(top, 1):
        col = theme.risk_color(L.risque)
        fill = theme.soft(col)
        if i % 2 == 0:
            out.append(f'<rect x="24" y="{y:.1f}" width="1232" height="{rh:.1f}" fill="#F5F7FA"/>')
        cy = y + rh / 2
        name = K.ellipsize(f"{i}. {L.nom}", wl, 11.5, 800)
        out.append(f'<text x="{xl}" y="{cy + 4:.1f}" font-size="11.5" font-weight="800" fill="{theme.INK}">'
                   f'<title>{K.esc(L.nom)}</title>{K.esc(name)}</text>')
        bw = max(28, wb * L.n_cas / nmax)
        bh = min(22, rh - 10)
        out.append(f'<rect x="{xb}" y="{cy - bh / 2:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="{fill}"/>')
        out.append(f'<text x="{xb + 8}" y="{cy + 4:.1f}" font-size="11" font-weight="800" fill="{theme.ink_on(fill)}">'
                   f'{K.esc(trf("{n} cas", n=L.n_cas))}</text>')
        per = (f"{L.debut:%d/%m}" + (f"→{L.fin:%d/%m}" if L.fin and L.fin != L.debut else "")) if L.debut else tr("dates ?")
        passages = (trf("{n} passages", n=L.visites) if L.visites > 1 else trf("{n} passage", n=L.visites)) if L.visites else ""
        aires = ", ".join(a for a, _ in L.aires.most_common(3))
        out.append(f'<text x="{xc}" y="{cy - 2:.1f}" font-size="10.5" font-weight="700" fill="{theme.INK}">'
                   f'{K.esc(K.ellipsize(_cas(L), 1240 - xc, 10.5, 700))}</text>')
        out.append(f'<text x="{xc}" y="{cy + 11:.1f}" font-size="9" fill="#000000">'
                   f'{K.esc(K.ellipsize((passages + " • " if passages else "") + trf("{per} • AS : {aires} • risque max : {r}", per=per, aires=aires, r=val(L.risque)), 1240 - xc, 9))}</text>')
        y += rh
    if len(lieux) > len(top):
        out.append(f'<text x="{xl}" y="{y + 14:.1f}" font-size="9.5" fill="{theme.MUTED}">… {K.esc(trf("{n} autre(s) lieu(x)", n=len(lieux) - len(top)))}</text>')
    out.append(K.footer(tr("Un lieu commun n'établit pas un lien de transmission : il oriente l'investigation, la décontamination "
                           "et la sensibilisation. Les écritures d'un même lieu sont regroupées (casse, accents, parenthèses).")))
    out.append("</svg>")
    return "".join(out)


def render_html(cases: List[Case], titre: str = "LIEUX LES PLUS FRÉQUENTÉS", min_cas: int = 2) -> str:
    return render_svg_page(render_svg(cases, titre, min_cas), "Lieux fréquentés")
