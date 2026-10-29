"""Icônes vectorielles sobres (24×24, trait), dessinées pour l'outil — aucune dépendance externe."""

ICONS = {
    "alert": '<path d="M12 3 2.5 20h19L12 3z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.2" r=".6"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5.5 5.5"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.3 9.4a2.8 2.8 0 1 1 3.9 2.6c-.8.4-1.2 1-1.2 1.9v.6"/><circle cx="12" cy="17.3" r=".6"/>',
    "thermo": '<path d="M10 4a2 2 0 1 1 4 0v9.3a4 4 0 1 1-4 0z"/><path d="M12 9v6.5"/>',
    "clinic": '<path d="M4 20V9l8-5 8 5v11z"/><path d="M12 10v6M9 13h6"/>',
    "arrow": '<path d="M4 12h15"/><path d="m14 6 6 6-6 6"/>',
    "hospital": '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M12 8v8M8 12h8"/>',
    "people": '<circle cx="8.5" cy="8" r="3"/><circle cx="16.5" cy="9" r="2.5"/><path d="M3 20c0-3.3 2.5-5.5 5.5-5.5S14 16.7 14 20"/><path d="M14.5 14.3c3 0 6.5 1.4 6.5 5.7"/>',
    "church": '<path d="M12 2v5M10 4h4"/><path d="M6 21v-9l6-5 6 5v9z"/><path d="M10 21v-4a2 2 0 0 1 4 0v4"/>',
    "moto": '<circle cx="5.5" cy="16.5" r="3"/><circle cx="18.5" cy="16.5" r="3"/><path d="M8.5 16.5h5l3-6h-4l-2 3H6"/><path d="M15 7h3l1.5 3.5"/>',
    "cross": '<path d="M12 3v18M7 8h10"/>',
    "grave": '<path d="M6 21V10a6 6 0 0 1 12 0v11z"/><path d="M12 9v6M9.5 11.5h5"/><path d="M3 21h18"/>',
    "swab": '<path d="m5 19 10-10"/><path d="M14 6.5c1.4-1.4 3.6-1.4 4.6-.4s1 3.2-.4 4.6l-1.6 1.6-4.2-4.2z"/>',
    "lab": '<path d="M9 3h6M10 3v6l-5.5 9.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3"/><path d="M7.5 15h9"/>',
    "shield": '<path d="M12 3 4.5 6v6c0 4.5 3.2 7.8 7.5 9 4.3-1.2 7.5-4.5 7.5-9V6z"/><path d="m8.8 12 2.2 2.2 4.3-4.4"/>',
    "dot": '<circle cx="12" cy="12" r="4"/>',
    "home": '<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h12V9.5"/>',
    "pin": '<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
}


def icon_svg(name: str, size: int = 14, color: str = "#fff", stroke: float = 2.0) -> str:
    body = ICONS.get(name, ICONS["dot"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def icon_group(name: str, x: float, y: float, size: float, color: str = "#fff", stroke: float = 2.0) -> str:
    """Icône positionnée dans un SVG parent (centre x,y)."""
    s = size / 24
    body = ICONS.get(name, ICONS["dot"])
    return (f'<g transform="translate({x - size / 2:.1f},{y - size / 2:.1f}) scale({s:.3f})" fill="none" '
            f'stroke="{color}" stroke-width="{stroke / s:.2f}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</g>')
