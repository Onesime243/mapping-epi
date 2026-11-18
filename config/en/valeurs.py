"""Choix des listes (config/theme.py, config/diseases.yaml, core/schema.py) : enregistrés en français, affichés
traduits (voir core/langue.py). Ne jamais traduire la valeur enregistrée, seulement son affichage.
"""

EN = {
    # --- niveaux de risque (RISK_CHOICES)
    "Inconnu": "Unknown", "Inconnue": "Unknown", "À investiguer": "To investigate", "En cours": "In progress",
    "Contrôlé": "Controlled", "Faible": "Low", "Modéré": "Moderate", "Élevé": "High", "Très élevé": "Very high",
    # --- risque des contacts (CONTACT_RISK_CHOICES)
    "Très haut": "Very high", "Haut": "High",
    # --- statut PCI des sites (IPC_CHOICES)
    "Non": "No", "Partiel": "Partial", "Décontaminé": "Decontaminated", "Oui": "Yes",
    # --- actions (priorité, statut, piliers, blocages)
    "Urgent": "Urgent", "Important": "Important", "Normal": "Normal",
    "À faire": "To do", "Fait": "Done",
    "Surveillance": "Surveillance", "Suivi des contacts": "Contact follow-up", "Vaccination": "Vaccination",
    "PCI": "IPC", "Laboratoire": "Laboratory", "Prise en charge": "Case management",
    "Engagement communautaire": "Community engagement", "Coordination": "Coordination",
    "Réticence communautaire": "Community resistance", "Sécurité ou accès": "Security or access",
    "Rupture d'intrants ou de vaccins": "Stock-out of supplies or vaccines",
    "Coordination interzones": "Inter-zone coordination", "Logistique ou transport": "Logistics or transport",
    "Ressources humaines": "Human resources", "Fiche non synchronisée": "Record not synchronised", "Autre": "Other",
    # --- lien épidémiologique (CONTACT_STATUS_CHOICES)
    "Contact connu": "Known contact", "Contact connu suivi": "Known contact under follow-up",
    "Non contact": "Not a contact",
    # --- vaccination et agent de santé (affichage des choix Oui / Non)
    "Non vacciné": "Not vaccinated", "Vacciné": "Vaccinated", "Agent de santé": "Health worker",
    # --- phases (PHASES, PHASE_DDS_CHOICES, groupes de symptômes)
    "Point d'infection": "Point of infection", "Avant symptômes": "Before symptoms", "Phase sèche": "Dry phase",
    "Phase humide": "Wet phase", "Phase critique": "Critical phase", "Décès": "Death",
    "Phase symptomatique": "Symptomatic phase", "exposition": "exposure", "non contagieux": "not contagious",
    "contagieux dès la fièvre": "contagious from fever onset", "très contagieux": "highly contagious",
    "le plus contagieux": "most contagious", "contagieux": "contagious",
    # --- état du cas (ISSUE_CHOICES)
    "En traitement": "Under treatment", "Vivant": "Alive", "Guéri": "Recovered",
    # --- types d'étapes (EVENT_TYPES)
    "Exposition": "Exposure", "Investigation": "Investigation", "Période à documenter": "Period to document",
    "Début maladie": "Illness onset", "Soins / consultation": "Care / consultation", "Référence": "Referral",
    "Hospitalisation": "Hospitalisation", "Activité communautaire": "Community activity",
    "Rassemblement religieux": "Religious gathering", "Déplacement": "Travel", "Funérailles": "Funeral",
    "Enterrement": "Burial", "Prélèvement": "Sample", "Riposte": "Response",
    # --- résultats de laboratoire et échantillons
    "Positif": "Positive", "Négatif": "Negative", "En attente": "Pending",
    "Swab": "Swab", "Sang total": "Whole blood", "Plasma": "Plasma", "Urine": "Urine",
    # --- types de lieux (PLACE_TYPES)
    "Ménage": "Household", "Village / quartier": "Village / neighbourhood", "Centre de santé": "Health centre",
    "Hôpital": "Hospital", "Église / lieu de culte": "Church / place of worship", "Marché": "Market",
    "École": "School", "Transport": "Transport", "Bureau ZS": "HZ office",
    # --- transports (TRANSPORTS)
    "Moto": "Motorbike", "Véhicule": "Vehicle", "À pied": "On foot", "Pirogue": "Canoe", "Vélo": "Bicycle",
    "Ambulance": "Ambulance",
    # --- catégories de contacts (core/schema.py)
    "Famille & amis": "Family & friends", "Prestataires de soins": "Care providers", "Co-patients": "Fellow patients",
    "PPL / garde-malades": "HCW / patient attendants", "Motard(s)": "Motorcycle rider(s)",
    "Équipe pastorale": "Pastoral team", "Fidèles": "Worshippers", "Participants funérailles": "Funeral participants",
    "Voisins": "Neighbours", "Collègues": "Colleagues",
    # --- maladies (DISEASES, config/diseases.yaml)
    "MVE": "EVD", "Marburg": "Marburg", "Mpox": "Mpox", "Choléra": "Cholera", "Rougeole": "Measles",
    "Maladie à virus Ebola": "Ebola virus disease", "Maladie à virus Marburg": "Marburg virus disease",
    "Autre maladie": "Other disease",
    # --- identité (SEXES, CASE_STATUS, unités d'âge)
    "M": "M", "F": "F", "Confirmé": "Confirmed", "Probable": "Probable", "Suspect": "Suspected",
    "ans": "years", "mois": "months",
    # --- symptômes (SYMPTOM_GROUPS)
    "Signes hémorragiques": "Haemorrhagic signs", "Autres signes": "Other signs",
    "Fièvre": "Fever", "Fatigue / asthénie": "Fatigue / asthenia", "Céphalées (maux de tête)": "Headache",
    "Douleurs articulaires": "Joint pain", "Douleurs musculaires": "Muscle pain", "Courbatures": "Body aches",
    "Mal au dos": "Back pain", "Mal de gorge": "Sore throat",
    "Diarrhée": "Diarrhoea", "Nausées": "Nausea", "Vomissements": "Vomiting", "Saignements": "Bleeding",
    "Hoquet": "Hiccups", "Rougeur oculaire": "Red eyes",
    "Méléna": "Melena", "Hématémèse": "Haematemesis", "Gingivorragie": "Gum bleeding", "Épistaxis": "Epistaxis",
    "Saignements aux points d'injection": "Bleeding at injection sites",
    "Anorexie": "Anorexia", "Douleurs abdominales": "Abdominal pain", "Toux": "Cough", "Éruption cutanée": "Skin rash",
    # anciens libellés de symptômes (fiches anciennes)
    "Asthénie": "Asthenia", "Céphalées": "Headache", "Conjonctivite": "Conjunctivitis", "Myalgies": "Myalgia",
    "Arthralgies": "Arthralgia", "Polyarthralgie": "Polyarthralgia",
}
