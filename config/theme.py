"""Thème central : couleurs, niveaux de risque, types d'étapes, polices.

Toute la charte graphique du mapping est définie ici. Modifier une couleur ici
la modifie partout (aperçu, PNG, PDF, SVG, PPTX).
"""

NAVY = "#1F3A5F"
NAVY_DARK = "#152B47"
BG = "#F3F5F8"
CARD = "#FFFFFF"
BORDER = "#DCE2EA"
TEXT = "#1B2430"
MUTED = "#6B7785"

# Trois couleurs seulement pour ce qui compte (vert / orange / rouge) ; tout le reste en gris ou noir.
# Teinte « appuyée » pour les traits, icônes et textes…
GREEN = "#4F8F58"    # Modéré / Contrôlé / Décontaminé / favorable
ORANGE = "#C77B3A"   # Élevé / Haut / Partiel
RED = "#B4554E"      # Très élevé / Très haut / Non / Décès
GREY = "#6B7785"     # inconnu, neutre, informatif
BLUE = PURPLE = TEAL = YELLOW = GREY      # anciennes teintes : désormais neutres
RED_STRONG = "#B3261E"                    # rouge fort (statut « Contact connu / Non contact »)
NEUTRAL = "#5B6573"                       # étapes de la chronologie (icônes, barres)

# … et teinte « douce » pour les badges et étiquettes (fonds), comme la légende d'une carte
SOFT = {GREEN: "#A6CB91", ORANGE: "#EBAA82", RED: "#CC746C", GREY: "#DCE1E7", NEUTRAL: "#DCE1E7"}
INK = "#111827"      # texte foncé, bien lisible


def soft(color: str) -> str:
    """Teinte douce (fond de badge) correspondant à une couleur du thème."""
    return SOFT.get(color, color)


def ink_on(fill: str) -> str:
    """Couleur du texte lisible sur un fond donné : blanc sur fond sombre, encre foncée sinon."""
    h = (fill or "#FFFFFF").lstrip("#")[:6]
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return INK
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return "#FFFFFF" if lum < 0.3 else INK

FONT_STACK = "'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
PPTX_FONT = "Calibri"

# --- Niveaux de risque des étapes / lieux -----------------------------------
# rang : sert au calcul du risque global (le plus élevé l'emporte)
RISK_LEVELS = {
    "Inconnu":       {"color": BLUE,   "rank": 1, "pattern": "dots"},
    "À investiguer": {"color": BLUE,   "rank": 1, "pattern": "dots"},
    "En cours":      {"color": BLUE,   "rank": 0, "pattern": "none"},
    "Contrôlé":      {"color": GREEN,  "rank": 0, "pattern": "none"},
    "Faible":        {"color": GREEN,  "rank": 1, "pattern": "none"},
    "Modéré":        {"color": GREEN,  "rank": 2, "pattern": "none"},
    "Élevé":         {"color": ORANGE, "rank": 3, "pattern": "stripes"},
    "Très élevé":    {"color": RED,    "rank": 4, "pattern": "cross"},
}
RISK_CHOICES = ["Inconnu", "À investiguer", "En cours", "Contrôlé", "Faible",
                "Modéré", "Élevé", "Très élevé"]

CONTACT_RISKS = {"Modéré": GREEN, "Haut": ORANGE, "Très haut": RED, "Inconnu": BLUE}
CONTACT_RISK_CHOICES = ["Haut", "Très haut", "Modéré", "Inconnu"]

IPC_STATUS = {"Décontaminé": GREEN, "Partiel": ORANGE, "Non": RED, "Inconnu": BLUE}
IPC_CHOICES = ["Non", "Partiel", "Décontaminé", "Inconnu"]

ACTION_PRIORITY = {"Urgent": RED, "Important": ORANGE, "Normal": BLUE}
ACTION_PRIORITY_CHOICES = ["Urgent", "Important", "Normal"]
ACTION_STATUS_CHOICES = ["À faire", "En cours", "Fait"]

# Lien épidémiologique : le cas était-il un contact connu (listé) avant sa confirmation ?
CONTACT_STATUS_CHOICES = ["Inconnu", "Contact connu", "Contact connu suivi", "Non contact"]
CONTACT_STATUS_COLORS = {"Contact connu": RED_STRONG, "Contact connu suivi": RED_STRONG, "Non contact": RED_STRONG,
                         "Inconnu": GREY}

# Phases de la maladie (MVE / Marburg) : point d'infection → incubation → phase sèche → phase humide
PHASES = {
    "infection":  {"label": "Point d'infection", "contag": "période d'exposition estimée", "color": GREY},
    "incubation": {"label": "Incubation", "contag": "non contagieux", "color": GREY},
    "seche":      {"label": "Phase sèche", "contag": "contagieux", "color": GREY},
    "humide":     {"label": "Phase humide", "contag": "encore plus contagieux", "color": ORANGE},
    "deces":      {"label": "Décès", "contag": "le plus contagieux", "color": RED},
    "symptomes":  {"label": "Phase symptomatique", "contag": "contagieux", "color": ORANGE},
}
SIGNES_SECS = "fièvre, fatigue, céphalées, douleurs articulaires et musculaires, mal de dos, mal de gorge"
SIGNES_HUMIDES = "diarrhée, nausées / vomissements, saignements, hoquet, rougeur oculaire"
# mots qui signalent l'entrée en phase humide dans la description d'une étape
MOTS_HUMIDES = ("diarrh", "selles liquides", "vomiss", "nausée", "saign", "hémorrag", "hemorrag", "hoquet",
                "rougeur oculaire", "yeux rouges", "conjonctiv", "méléna", "hématémèse", "gingivorr", "épistaxis")
SYMPTOMES_HUMIDES = {"Vomissements", "Nausées", "Diarrhée", "Hoquet", "Rougeur oculaire", "Saignements", "Méléna",
                     "Hématémèse", "Gingivorragie", "Épistaxis", "Saignements aux points d'injection"}

ISSUE_CHOICES = ["En traitement", "Vivant", "Guéri", "Décès", "Inconnu"]
ISSUE_COLORS = {"Décès": RED, "Guéri": GREEN, "Vivant": GREEN, "En traitement": ORANGE, "Inconnu": BLUE}

# --- Types d'étapes de la chronologie ---------------------------------------
# color : barre supérieure de la carte ; icon : nom d'icône (render/icons.py)
EVENT_TYPES = {
    "Exposition":               {"color": NEUTRAL,   "icon": "alert"},
    "Investigation":            {"color": NEUTRAL,   "icon": "search"},
    "Période à documenter":     {"color": NEUTRAL, "icon": "question"},
    "Début maladie":            {"color": NEUTRAL,  "icon": "thermo"},
    "Soins / consultation":     {"color": NEUTRAL,  "icon": "clinic"},
    "Référence":                {"color": NEUTRAL, "icon": "arrow"},
    "Hospitalisation":          {"color": NEUTRAL,    "icon": "hospital"},
    "Activité communautaire":   {"color": NEUTRAL, "icon": "people"},
    "Rassemblement religieux":  {"color": NEUTRAL, "icon": "church"},
    "Déplacement":              {"color": NEUTRAL, "icon": "moto"},
    "Décès":                    {"color": NEUTRAL,    "icon": "cross"},
    "Funérailles":              {"color": NEUTRAL, "icon": "people"},
    "Enterrement":              {"color": NEUTRAL,    "icon": "grave"},
    "Prélèvement":              {"color": NEUTRAL,   "icon": "swab"},
    "Laboratoire":              {"color": NEUTRAL,  "icon": "lab"},
    "Riposte":                  {"color": NEUTRAL,   "icon": "shield"},
    "Autre":                    {"color": NEUTRAL,  "icon": "dot"},
}
EVENT_TYPE_CHOICES = list(EVENT_TYPES.keys())

PLACE_TYPES = ["Ménage", "Village / quartier", "Centre de santé", "Hôpital", "Église / lieu de culte",
               "Marché", "École", "Funérailles", "Enterrement", "Transport", "Laboratoire", "Bureau ZS", "Autre"]

TRANSPORTS = ["", "Moto", "Véhicule", "À pied", "Pirogue", "Vélo", "Ambulance", "Inconnu"]

ANNEE_MIN = 2026          # première année proposée par les calendriers

DISEASES = ["MVE", "Marburg", "Mpox", "Choléra", "Rougeole", "Autre"]
SEXES = ["M", "F", "Inconnu"]
CASE_STATUS = ["Confirmé", "Probable", "Suspect"]

# Symptômes groupés selon les phases de la maladie (schéma « phase sèche / phase humide »)
SYMPTOM_GROUPS = {
    "Phase sèche": ["Fièvre", "Fatigue / asthénie", "Céphalées (maux de tête)", "Douleurs articulaires",
                    "Douleurs musculaires", "Courbatures", "Mal au dos", "Mal de gorge"],
    "Phase humide": ["Diarrhée", "Nausées", "Vomissements", "Saignements", "Hoquet", "Rougeur oculaire"],
    "Signes hémorragiques": ["Méléna", "Hématémèse", "Gingivorragie", "Épistaxis", "Saignements aux points d'injection"],
    "Autres signes": ["Anorexie", "Douleurs abdominales", "Toux", "Éruption cutanée"],
}
SYMPTOMS = [s for g in SYMPTOM_GROUPS.values() for s in g]
HEMORRHAGIC = set(SYMPTOM_GROUPS["Signes hémorragiques"]) | {"Saignements"}
SYMPTOMES_SECS = set(SYMPTOM_GROUPS["Phase sèche"])
# anciens libellés → libellés actuels (fiches enregistrées avant cette version)
SYMPTOM_ALIASES = {"Asthénie": "Fatigue / asthénie", "Céphalées": "Céphalées (maux de tête)",
                   "Conjonctivite": "Rougeur oculaire", "Myalgies": "Douleurs musculaires",
                   "Arthralgies": "Douleurs articulaires", "Polyarthralgie": "Douleurs articulaires"}


def risk_color(level: str) -> str:
    return RISK_LEVELS.get(level, {"color": MUTED})["color"]


def risk_rank(level: str) -> int:
    return RISK_LEVELS.get(level, {"rank": 0})["rank"]
