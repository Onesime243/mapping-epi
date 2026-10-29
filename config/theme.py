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

BLUE = "#2E6A8E"     # Inconnu / À investiguer / En cours
GREEN = "#2E8B57"    # Modéré / Contrôlé / Décontaminé
ORANGE = "#E07B00"   # Élevé / Haut / Partiel
RED = "#C0392B"      # Très élevé / Très haut / Non / Décès
PURPLE = "#7D4E9E"
TEAL = "#1E8C8C"

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

ISSUE_CHOICES = ["En traitement", "Vivant", "Guéri", "Décès", "Inconnu"]
ISSUE_COLORS = {"Décès": RED, "Guéri": GREEN, "Vivant": GREEN, "En traitement": ORANGE, "Inconnu": BLUE}

# --- Types d'étapes de la chronologie ---------------------------------------
# color : barre supérieure de la carte ; icon : nom d'icône (render/icons.py)
EVENT_TYPES = {
    "Exposition":               {"color": BLUE,   "icon": "alert"},
    "Investigation":            {"color": BLUE,   "icon": "search"},
    "Période à documenter":     {"color": PURPLE, "icon": "question"},
    "Début maladie":            {"color": GREEN,  "icon": "thermo"},
    "Soins / consultation":     {"color": GREEN,  "icon": "clinic"},
    "Référence":                {"color": ORANGE, "icon": "arrow"},
    "Hospitalisation":          {"color": RED,    "icon": "hospital"},
    "Activité communautaire":   {"color": PURPLE, "icon": "people"},
    "Rassemblement religieux":  {"color": PURPLE, "icon": "church"},
    "Déplacement":              {"color": ORANGE, "icon": "moto"},
    "Décès":                    {"color": RED,    "icon": "cross"},
    "Funérailles":              {"color": ORANGE, "icon": "people"},
    "Enterrement":              {"color": RED,    "icon": "grave"},
    "Prélèvement":              {"color": TEAL,   "icon": "swab"},
    "Laboratoire":              {"color": GREEN,  "icon": "lab"},
    "Riposte":                  {"color": TEAL,   "icon": "shield"},
    "Autre":                    {"color": MUTED,  "icon": "dot"},
}
EVENT_TYPE_CHOICES = list(EVENT_TYPES.keys())

PLACE_TYPES = ["Ménage", "Village / quartier", "Centre de santé", "Hôpital", "Église / lieu de culte",
               "Marché", "École", "Funérailles", "Enterrement", "Transport", "Laboratoire", "Bureau ZS", "Autre"]

TRANSPORTS = ["", "Moto", "Véhicule", "À pied", "Pirogue", "Vélo", "Ambulance", "Inconnu"]

ANNEE_MIN = 2026          # première année proposée par les calendriers

DISEASES = ["MVE", "Marburg", "Mpox", "Choléra", "Rougeole", "Autre"]
SEXES = ["M", "F", "Inconnu"]
CASE_STATUS = ["Confirmé", "Probable", "Suspect"]

SYMPTOMS = ["Fièvre", "Céphalées", "Courbatures", "Douleurs abdominales", "Vomissements", "Diarrhée",
            "Asthénie", "Anorexie", "Hoquet", "Conjonctivite", "Éruption cutanée", "Toux",
            "Méléna", "Hématémèse", "Gingivorragie", "Épistaxis", "Saignements aux points d'injection"]
HEMORRHAGIC = {"Méléna", "Hématémèse", "Gingivorragie", "Épistaxis", "Saignements aux points d'injection"}


def risk_color(level: str) -> str:
    return RISK_LEVELS.get(level, {"color": MUTED})["color"]


def risk_rank(level: str) -> int:
    return RISK_LEVELS.get(level, {"rank": 0})["rank"]
