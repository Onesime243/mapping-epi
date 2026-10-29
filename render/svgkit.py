"""Petits outils SVG partagés par les visualisations complémentaires."""
from __future__ import annotations

from html import escape
from typing import List

from config import theme

W, H = 1280, 720
FONT = "Inter, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"


def esc(s) -> str:
    return escape(str(s if s is not None else ""), quote=True)


def svg_open() -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="{esc(FONT)}">'
            f'<rect width="{W}" height="{H}" fill="{theme.BG}"/>'
            '<defs>'
            '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
            '<feDropShadow dx="0" dy="1" stdDeviation="1.6" flood-color="#14284a" flood-opacity=".14"/></filter>'
            '<pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="8" height="8" fill="{theme.BLUE}" fill-opacity=".08"/>'
            f'<rect width="4" height="8" fill="{theme.BLUE}" fill-opacity=".18"/></pattern>'
            + "".join(
                f'<marker id="arr-{k}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0 0 10 5 0 10z" fill="{c}"/></marker>'
                for k, c in {"navy": theme.NAVY, "red": theme.RED, "orange": theme.ORANGE, "blue": theme.BLUE,
                             "green": theme.GREEN, "muted": theme.MUTED, "teal": theme.TEAL}.items())
            + '</defs>')


def header(title: str, subtitle: str = "") -> str:
    return (f'<rect width="{W}" height="56" fill="{theme.NAVY}"/>'
            f'<text x="{W / 2}" y="27" text-anchor="middle" fill="#fff" font-size="20" font-weight="800">{esc(title)}</text>'
            f'<text x="{W / 2}" y="45" text-anchor="middle" fill="#fff" fill-opacity=".78" font-size="10.5">{esc(subtitle)}</text>')


def footer(text: str) -> str:
    return (f'<rect x="16" y="{H - 30}" width="{W - 32}" height="22" rx="6" fill="#E7EBF0" stroke="{theme.BORDER}"/>'
            f'<text x="28" y="{H - 15.5}" font-size="9.5" fill="{theme.MUTED}">{esc(text)}</text>')


def card(x, y, w, h, rx=9) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="#fff" stroke="{theme.BORDER}" filter="url(#sh)"/>'


def pill(x, y, text) -> str:
    w = 16 + len(text) * 6.6
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="20" rx="5" fill="{theme.NAVY}"/>'
            f'<text x="{x + 10}" y="{y + 13.8}" fill="#fff" font-size="9.5" font-weight="800" letter-spacing=".6">'
            f'{esc(text.upper())}</text>')


def wrap(text: str, max_chars: int, max_lines: int = 3) -> List[str]:
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(0, max_chars - 1)].rstrip() + "…"
    return lines or [""]


def multiline(x, y, lines, size=10, weight=400, fill=None, anchor="middle", lh=1.25) -> str:
    fill = fill or theme.TEXT
    out = [f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">']
    for i, ln in enumerate(lines):
        out.append(f'<tspan x="{x:.1f}" dy="{0 if i == 0 else size * lh:.1f}">{esc(ln)}</tspan>')
    out.append("</text>")
    return "".join(out)


def badge(x, y, text, color, size=9.5, anchor="middle") -> str:
    w = 12 + len(text) * size * 0.62
    bx = x - w / 2 if anchor == "middle" else x
    return (f'<rect x="{bx:.1f}" y="{y:.1f}" width="{w:.1f}" height="{size + 8:.1f}" rx="4" fill="{color}"/>'
            f'<text x="{bx + w / 2:.1f}" y="{y + size + 2.6:.1f}" text-anchor="middle" fill="#fff" font-size="{size}" '
            f'font-weight="800">{esc(text)}</text>')


def legend_item(x, y, color, text, kind="rect", dashed=False) -> str:
    if kind == "line":
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        sym = f'<line x1="{x}" y1="{y}" x2="{x + 20}" y2="{y}" stroke="{color}" stroke-width="3"{dash}/>'
    elif kind == "circle":
        dash = ' stroke-dasharray="3 3" fill="#fff"' if dashed else f' fill="{color}"'
        sym = f'<circle cx="{x + 8}" cy="{y}" r="7" stroke="{color}" stroke-width="2"{dash}/>'
    else:
        sym = f'<rect x="{x}" y="{y - 5}" width="20" height="10" rx="2" fill="{color}"/>'
    return sym + f'<text x="{x + 26}" y="{y + 3.5}" font-size="10" fill="{theme.MUTED}">{esc(text)}</text>'


def risk_marker(level: str) -> str:
    return {"Très élevé": "red", "Élevé": "orange", "Modéré": "green", "Contrôlé": "green"}.get(level, "blue")
