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
    size = 20.0
    while size > 12 and text_width(title, size, 800) > W - 40:
        size -= 0.5
    title = ellipsize(title, W - 40, size, 800)
    subtitle = ellipsize(subtitle, W - 40, 10.5, 400)
    return (f'<rect width="{W}" height="56" fill="{theme.NAVY}"/>'
            f'<text x="{W / 2}" y="27" text-anchor="middle" fill="#fff" font-size="{size}" font-weight="800">{esc(title)}</text>'
            f'<text x="{W / 2}" y="45" text-anchor="middle" fill="#fff" fill-opacity=".78" font-size="10.5">{esc(subtitle)}</text>')


def footer(text: str) -> str:
    return (f'<rect x="16" y="{H - 30}" width="{W - 32}" height="22" rx="6" fill="#E7EBF0" stroke="{theme.BORDER}"/>'
            f'<text x="28" y="{H - 15.5}" font-size="9.5" fill="#3A4654">{esc(ellipsize(text, W - 60, 9.5))}</text>')


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


# ---------------------------------------------------------------------------
# Mesure du texte (police Inter réelle via Pillow) et ajustement au cadre
# ---------------------------------------------------------------------------
from functools import lru_cache  # noqa: E402
from pathlib import Path  # noqa: E402

_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_WEIGHT_FILE = {400: "Inter-Regular.otf", 500: "Inter-Medium.otf", 600: "Inter-SemiBold.otf",
                700: "Inter-Bold.otf", 800: "Inter-ExtraBold.otf"}


@lru_cache(maxsize=64)
def _font(weight: int, size10: int):
    try:
        from PIL import ImageFont
        w = min(_WEIGHT_FILE, key=lambda k: abs(k - weight))
        return ImageFont.truetype(str(_FONTS / _WEIGHT_FILE[w]), size10)
    except Exception:
        return None


def text_width(text: str, size: float, weight: int = 400) -> float:
    """Largeur (px) d'un texte SVG en police Inter."""
    text = str(text or "")
    f = _font(int(weight), 100)
    if f is not None:
        try:
            return f.getlength(text) * size / 100.0
        except Exception:
            pass
    return len(text) * size * (0.56 if weight >= 600 else 0.52)


def ellipsize(text: str, max_w: float, size: float, weight: int = 400) -> str:
    text = str(text or "")
    if text_width(text, size, weight) <= max_w:
        return text
    while text and text_width(text + "…", size, weight) > max_w:
        text = text[:-1]
    return text.rstrip(" ,;•–-") + "…"


def wrap_px(text: str, max_w: float, size: float, weight: int = 400, max_lines: int = 2) -> List[str]:
    """Coupe un texte en lignes qui tiennent dans max_w pixels ; la dernière ligne finit par « … » si besoin."""
    words, lines, cur = str(text or "").split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if not cur or text_width(cand, size, weight) <= max_w:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        rest = " ".join(lines[max_lines - 1:])
        lines = lines[:max_lines - 1] + [ellipsize(rest, max_w, size, weight)]
    return [ellipsize(ln, max_w, size, weight) for ln in lines] or [""]


def split_first(text: str, max_w: float, size: float, weight: int = 400):
    """Première ligne qui tient dans max_w (mots entiers) et le reste du texte."""
    words = str(text or "").split()
    cur = ""
    for i, w in enumerate(words):
        cand = f"{cur} {w}".strip()
        if cur and text_width(cand, size, weight) > max_w:
            return cur, " ".join(words[i:])
        cur = cand
    if text_width(cur, size, weight) > max_w:
        return ellipsize(cur, max_w, size, weight), ""
    return cur, ""


def fit_block(text: str, max_w: float, max_lines: int, size: float, weight: int = 400, min_size: float = 7.5):
    """Plus grande taille (≤ size) à laquelle le texte tient en max_lines lignes de max_w px, et les lignes."""
    s = size
    while s > min_size:
        lines = wrap_px(text, max_w, s, weight, max_lines + 1)
        if len(lines) <= max_lines and not lines[-1].endswith("…"):
            return s, lines
        s -= 0.5
    return min_size, wrap_px(text, max_w, min_size, weight, max_lines)


class LabelPlacer:
    """Placement glouton d'étiquettes : pour chaque nœud, essaie plusieurs positions autour du cercle et
    garde celle qui chevauche le moins les nœuds et étiquettes déjà posés, sans sortir du cadre."""

    def __init__(self, bounds):
        self.x0, self.y0, self.x1, self.y1 = bounds
        self.boxes: List[tuple] = []

    def block(self, x, y, w, h):
        self.boxes.append((x, y, x + w, y + h))

    def circle(self, cx, cy, r):
        self.block(cx - r, cy - r, 2 * r, 2 * r)

    def _cost(self, b):
        x0, y0, x1, y1 = b
        out = max(0, self.x0 - x0) + max(0, x1 - self.x1) + max(0, self.y0 - y0) + max(0, y1 - self.y1)
        cost = out * 1000
        for (a0, b0, a1, b1) in self.boxes:
            ix, iy = min(x1, a1) - max(x0, a0), min(y1, b1) - max(y0, b0)
            if ix > 0 and iy > 0:
                cost += ix * iy
        return cost

    def place(self, cx, cy, r, lines_sizes, prefer=None, gap=6):
        """lines_sizes : [(texte, taille, graisse, couleur)]. Renvoie le SVG de l'étiquette."""
        lh = [s * 1.22 for _, s, _, _ in lines_sizes]
        w = max((text_width(t, s, wt) for t, s, wt, _ in lines_sizes), default=0) + 4
        h = sum(lh)
        cands = {
            "below": (cx - w / 2, cy + r + gap), "above": (cx - w / 2, cy - r - gap - h),
            "right": (cx + r + gap, cy - h / 2), "left": (cx - r - gap - w, cy - h / 2),
            "below-right": (cx + r * .6, cy + r * .6 + gap), "below-left": (cx - r * .6 - w, cy + r * .6 + gap),
            "above-right": (cx + r * .6, cy - r * .6 - gap - h), "above-left": (cx - r * .6 - w, cy - r * .6 - gap - h),
        }
        order = list(prefer or []) + [k for k in cands if k not in (prefer or [])]
        best, best_cost = None, None
        for i, k in enumerate(order):
            x, y = cands[k]
            # rester dans le cadre en glissant horizontalement
            x = min(max(x, self.x0 + 2), self.x1 - w - 2)
            c = self._cost((x, y, x + w, y + h)) + i * 3
            if best_cost is None or c < best_cost:
                best, best_cost = (x, y), c
            if c == i * 3 and i < 2:
                break
        x, y = best
        self.block(x, y, w, h)
        out, yy = [], y
        for (t, s, wt, col), l in zip(lines_sizes, lh):
            yy += l
            out.append(f'<text x="{x + w / 2:.1f}" y="{yy - l * 0.25:.1f}" text-anchor="middle" font-size="{s}" '
                       f'font-weight="{wt}" fill="{col}">{esc(t)}</text>')
        return "".join(out)
