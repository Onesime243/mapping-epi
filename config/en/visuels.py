"""Visuels : mapping (fiche du parcours), réseau, carte du parcours, frise, multi-cas, chaînes de transmission,
lieux communs, lieux fréquentés (voir core/langue.py et render/libelles.py).

Glossaire : MVE → EVD, PCI → IPC, ZS → HZ, AS → HA, J0 → D0, J±n → D±n. Les valeurs de listes affichées dans les
visuels sont reprises ici (mêmes traductions que valeurs.py) pour qu'aucune ne manque.
"""

EN = {
    # ------------------------------------------------------------------ glossaire et valeurs affichées
    "MVE": "EVD", "PCI": "IPC", "ZS": "HZ", "AS": "HA", "J0": "D0", "ZS ?": "HZ ?", "AS ?": "HA ?",
    "cas confirmé": "confirmed case", "parcours thérapeutique": "care pathway",
    "Chaînes de transmission": "Transmission chains", "Réseau de contacts": "Contact network",
    "Réseau de transmission": "Transmission network", "Réseau": "Network", "Parcours": "Pathway", "Frise": "Timeline",
    "Carte du parcours": "Pathway map", "Frise temporelle": "Timeline", "Multi-cas": "Multi-case",
    "Lieux communs": "Shared places", "Lieux fréquentés": "Places visited", "Tableau de bord multi-cas": "Multi-case dashboard",
    "Visuels": "Visuals", "Rapport complet": "Full report",
    "Point d'infection": "Point of infection", "Avant symptômes": "Before symptoms", "Phase sèche": "Dry phase",
    "Phase humide": "Wet phase", "Phase critique": "Critical phase", "Phase symptomatique": "Symptomatic phase",
    "très contagieux": "highly contagious", "contagieux dès la fièvre": "contagious from fever onset",
    "le plus contagieux": "most contagious", "contagieux": "contagious", "non contagieux": "not contagious",
    "exposition": "exposure", "hors fenêtres": "outside windows",
    "Début maladie": "Illness onset", "Hospitalisation": "Hospitalisation", "Isolement / prise en charge": "Isolation / care",
    "Résultat positif": "Positive result", "Exposition probable": "Probable exposure",
    # titres d'étapes proposés par l'outil (core/narratif.py)
    "Garde-malade auprès d'un malade": "Attending a patient", "Funérailles (exposition)": "Funeral (exposure)",
    "Prélèvement / envoi": "Sample / shipment", "Résultat de laboratoire": "Laboratory result",
    "Automédication": "Self-medication", "Aggravation des signes": "Worsening of signs",
    "Élevé": "High", "Très élevé": "Very high", "Modéré": "Moderate", "Faible": "Low", "À investiguer": "To investigate",
    "Inconnu": "Unknown", "Inconnue": "Unknown", "Contrôlé": "Controlled", "En cours": "In progress",
    "Très haut": "Very high", "Haut": "High",
    "Décès": "Death", "Vivant": "Alive", "En traitement": "Under treatment", "Guéri": "Recovered",
    "Contact connu": "Known contact", "Contact connu suivi": "Known contact under follow-up", "Non contact": "Not a contact",
    "Non vacciné": "Not vaccinated", "Vacciné": "Vaccinated", "Agent de santé": "Health worker",
    "Urgent": "Urgent", "Important": "Important", "Normal": "Normal",
    "Non": "No", "Oui": "Yes", "Partiel": "Partial", "Décontaminé": "Decontaminated", "Non fait": "Not done",
    "Lister tous les contacts": "List all contacts", "à dénombrer": "to be counted", "personnes présentes": "people present",
    "suggérées, à valider": "suggested, to be validated", "Source hors périmètre": "Source outside scope",
    "Génération": "Generation", "Synthèse": "Summary", "Cas sans lien saisi": "Cases without an entered link",
    "Pistes : lieux communs": "Leads: shared places", "Contact connu (non suivi)": "Known contact (not followed up)",
    "Statut de contact non précisé": "Contact status not specified", "Bord rouge : décès": "Red edge: death",
    "Bord : risque / décès": "Edge: risk / death",
    # types d'étapes, lieux, transports, statuts, maladies, unités
    "Exposition": "Exposure", "Investigation": "Investigation", "Période à documenter": "Period to document",
    "Soins / consultation": "Care / consultation", "Référence": "Referral", "Activité communautaire": "Community activity",
    "Rassemblement religieux": "Religious gathering", "Déplacement": "Travel", "Funérailles": "Funeral",
    "Enterrement": "Burial", "Prélèvement": "Sample", "Laboratoire": "Laboratory", "Riposte": "Response", "Autre": "Other",
    "Ménage": "Household", "Village / quartier": "Village / neighbourhood", "Centre de santé": "Health centre",
    "Hôpital": "Hospital", "Église / lieu de culte": "Church / place of worship", "Marché": "Market", "École": "School",
    "Transport": "Transport", "Bureau ZS": "HZ office",
    "Moto": "Motorbike", "Véhicule": "Vehicle", "À pied": "On foot", "Pirogue": "Canoe", "Vélo": "Bicycle",
    "Ambulance": "Ambulance",
    "Confirmé": "Confirmed", "Probable": "Probable", "Suspect": "Suspected",
    "Positif": "Positive", "Négatif": "Negative", "En attente": "Pending",
    "Marburg": "Marburg", "Mpox": "Mpox", "Choléra": "Cholera", "Rougeole": "Measles",
    "ans": "years", "mois": "months", "jours": "days", "listés": "listed",
    "Participants funérailles": "Funeral participants",
    # symptômes
    "Fièvre": "Fever", "Fatigue / asthénie": "Fatigue / asthenia", "Céphalées (maux de tête)": "Headache",
    "Douleurs articulaires": "Joint pain", "Douleurs musculaires": "Muscle pain", "Courbatures": "Body aches",
    "Mal au dos": "Back pain", "Mal de gorge": "Sore throat", "Diarrhée": "Diarrhoea", "Nausées": "Nausea",
    "Vomissements": "Vomiting", "Saignements": "Bleeding", "Hoquet": "Hiccups", "Rougeur oculaire": "Red eyes",
    "Méléna": "Melena", "Hématémèse": "Haematemesis", "Gingivorragie": "Gum bleeding", "Épistaxis": "Epistaxis",
    "Saignements aux points d'injection": "Bleeding at injection sites", "Anorexie": "Anorexia",
    "Douleurs abdominales": "Abdominal pain", "Toux": "Cough", "Éruption cutanée": "Skin rash",
    "Asthénie": "Asthenia", "Céphalées": "Headache",
    "fièvre, fatigue, céphalées, douleurs articulaires et musculaires, mal de dos, mal de gorge":
        "fever, fatigue, headache, joint and muscle pain, back pain, sore throat",
    "diarrhée, nausées / vomissements, saignements, hoquet, rougeur oculaire":
        "diarrhoea, nausea / vomiting, bleeding, hiccups, red eyes",
    "défaillance des organes, confusion, convulsions, choc, saignements":
        "organ failure, confusion, seizures, shock, bleeding",
    # sources des dates (phases, J0 estimé)
    "saisie": "entered", "rapportée": "reported", "estimée": "estimated",
    "début maladie": "illness onset", "phase humide": "wet phase", "décès": "death", "soins": "care",

    # ------------------------------------------------------------------ mapping (fiche du parcours)
    "Chronologie du parcours": "Pathway chronology", "ID du cas source : à compléter": "Source case ID: to be completed",
    "J±n : jours depuis le J0 retenu (date rapportée − {n} j)": "D±n: days since the retained D0 (reported date − {n} d)",
    "J±n : jours depuis le J0 retenu ou estimé": "D±n: days since the retained or estimated D0",
    "jours chargés agrandis": "busy days enlarged",
    "Aucune date dans la chronologie : renseigner les dates des étapes pour afficher la frise.":
        "No dates in the chronology: enter the step dates to display the timeline.",
    "Aucune étape dans la chronologie.": "No steps in the chronology.",
    "Contacts à identifier / suivre": "Contacts to identify / follow up",
    "{n} suivis": "{n} followed up", "Aucun groupe de contacts renseigné.": "No contact group entered.",
    "PCI / décontamination": "IPC / decontamination",
    "{n} lieux d’exposition sans statut PCI :": "{n} exposure places without IPC status:",
    "{n} lieu d’exposition sans statut PCI :": "{n} exposure place without IPC status:",
    "Priorité : fermer les sites non décontaminés ; noter date, équipe et produit.":
        "Priority: close the sites not decontaminated; record date, team and product.",
    "Actions": "Actions", "responsable · échéance": "responsible · deadline",
    "À réaliser immédiatement": "To do immediately", "à désigner": "to be assigned", "Déjà réalisées": "Already done",
    "Aucune action.": "No actions.", "(en cours)": "(in progress)",
    # en-tête et chiffres clés
    "Risque": "Risk", "Issue": "Outcome", "date du décès à compléter": "date of death to be completed",
    "? à compléter": "? to be completed", "état du cas": "case status",
    "hors structure de soins": "outside a health facility", "en structure de soins": "in a health facility",
    "Signes → confirmation": "Signs → confirmation", "{n} jours": "{n} days", "{n} jour": "{n} day",
    "seuil d’alerte : {n} jours": "alert threshold: {n} days",
    "début des symptômes ou confirmation manquant": "symptom onset or confirmation missing",
    "Vaccination ?": "Vaccination ?", "Agent de santé : non": "Health worker: no", "Agent de santé ?": "Health worker ?",
    "{statut} de {src}": "{statut} of {src}", "Lien avec un cas connu : inconnu": "Link with a known case: unknown",
    "J0 rapporté": "Reported D0", "J0 retenu": "Retained D0", "J0 estimé": "Estimated D0",
    "J0 retenu (−{n} j)": "Retained D0 (−{n} d)", "(−{n} j)": "(−{n} d)", "(estimé)": "(estimated)",
    "Notifié": "Notified", "Notifié le": "Notified on", "Notifié (J0{n} j)": "Notified (D0{n} d)",
    "Notifié (J0 ~{n} j)": "Notified (D0 ~{n} d)",
    "{n} jour(s) entre le début des symptômes rapporté et la notification":
        "{n} day(s) between the reported symptom onset and notification",
    "Prélevé": "Sampled", "Enterré": "Buried", "(sécurisé)": "(safe)", "(non sécurisé)": "(unsafe)",
    "Complétude": "Completeness",
    "{n} groupe de contacts à dénombrer": "{n} contact group to be counted",
    "{n} groupes de contacts à dénombrer": "{n} contact groups to be counted",
    "{n} étape sans personnes": "{n} step without people", "{n} étapes sans personnes": "{n} steps without people",
    "ID du cas source": "source case ID", "chronologie vide": "empty chronology",
    # bandeau d'identité
    "Sexe": "Sex", "Âge": "Age", "État": "Status", "Confirmation": "Confirmation",
    "Dernier contact": "Last contact", "Exposition estimée": "Estimated exposure", "Expo. (cas source)": "Expo. (source case)",
    "à rechercher": "to be investigated",
    "Date rapportée par l'équipe d'investigation": "Date reported by the investigation team",
    "Pas de date rapportée : J0 remonté depuis la phase où le cas a été trouvé":
        "No reported date: D0 worked back from the phase in which the case was found",
    "Premiers signes rapportés en {p} : J0 = date rapportée − {n} j": "First signs reported in the {p}: D0 = reported date − {n} d",
    "Phase des premiers signes non précisée : J0 = date rapportée − {n} j (phase sèche)":
        "Phase of first signs not specified: D0 = reported date − {n} d (dry phase)",
    "Contact connu : renseigner la date du dernier contact avec le cas source":
        "Known contact: enter the date of last contact with the source case",
    "Date du dernier contact avec le cas source": "Date of last contact with the source case",
    "Période contagieuse du cas source dans la fenêtre d'incubation du cas":
        "Contagious period of the source case within the incubation window of the case",
    "Calculée depuis le J0 retenu ou estimé (J-21 → J-2 pour la MVE), quelle que soit la phase du cas":
        "Calculated from the retained or estimated D0 (D-21 → D-2 for EVD), whatever the phase of the case",
    # badges et pastilles
    "Vacciné le {d}": "Vaccinated on {d}", "NON VACCINÉ": "NOT VACCINATED",
    "Vaccination : à compléter": "Vaccination: to be completed", "PPL : oui": "HCW: yes", "PPL : NON": "HCW: NO",
    "PPL : à compléter": "HCW: to be completed", "de {src}": "of {src}",
    "Contact corps": "Body contact", "Liquides biol.": "Body fluids", "Sans PCI": "No IPC",
    "Personnes : à compléter": "People: to be completed",
    "Saisi": "Entered", "Suggéré": "Suggested",
    # bandeau des phases et frise
    "contact connu : dates du cas source à rechercher": "known contact: source case dates to be investigated",
    "renseigner la date du dernier contact avec le cas source (pas d'estimation pour un contact connu)":
        "enter the date of last contact with the source case (no estimate for a known contact)",
    "{quand} (dernier contact avec le cas source)": "{quand} (last contact with the source case)",
    "contact connu de {src} : exposition datée par l'investigation": "known contact of {src}: exposure dated by the investigation",
    "cas source ?": "source case ?",
    "{quand} (cas source contagieux)": "{quand} (source case contagious)",
    "période contagieuse de {src} dans la fenêtre d'incubation": "contagious period of {src} within the incubation window",
    "J0 estimé depuis : {src}": "D0 estimated from: {src}",
    "{d1} → {d2} (date estimée)": "{d1} → {d2} (estimated date)",
    "exposition à un malade ou un corps, J-{a} → J-{b} du J0 retenu": "exposure to a patient or a body, D-{a} → D-{b} of the retained D0",
    "exposition à un malade ou un corps, J-{a} → J-{b} du J0 estimé depuis : {src}":
        "exposure to a patient or a body, D-{a} → D-{b} of the D0 estimated from: {src}",
    "guérison ou aggravation ; ": "recovery or worsening; ",
    "? (aucune date pour estimer)": "? (no date to estimate from)",
    "renseigner le début des symptômes, la phase humide ou le décès": "enter the symptom onset, the wet phase or the death",
    "signes habituels : {s}": "usual signs: {s}", "signes rapportés : {s}": "reported signs: {s}",
    "(estimé, {src})": "(estimated, {src})", "(rapporté {d})": "(reported {d})", "(rapporté)": "(reported)",
    "dès le {d} ({rel}, {src})": "from {d} ({rel}, {src})", "guérison ou aggravation": "recovery or worsening",
    "période contagieuse": "contagious period",
    "charge virale maximale : corps très contagieux": "maximum viral load: body highly contagious",
    "exposition J-{a} → J-{b}": "exposure D-{a} → D-{b}",
    "Phase sèche · contagieux dès la fièvre": "Dry phase · contagious from fever onset",
    "Phase humide · très contagieux": "Wet phase · highly contagious", "Période contagieuse": "Contagious period",
    "Corps très contagieux": "Body highly contagious", "Sèche": "Dry", "Humide": "Wet", "Critique": "Critical",
    "Contagieux": "Contagious", "Corps contagieux": "Contagious body", "Exposition {d1}→{d2}": "Exposure {d1}→{d2}",
    "{n} jours sans information": "{n} days without information",
    # blocs du bas
    "{n} à haut risque · suivis : {s}": "{n} high risk · followed up: {s}", "non renseigné": "not entered",
    "{ok} sur {n} décontaminés": "{ok} of {n} decontaminated", "{ok} sur {n} décontaminé": "{ok} of {n} decontaminated",
    "aucun site renseigné": "no site entered", "DÉCONTAMINÉ": "DECONTAMINATED",
    "Priorité : fermer les sites non décontaminés et documenter la date / équipe / produit.":
        "Priority: close the sites not decontaminated and document the date / team / product.",
    "Tous les sites sont décontaminés : vérifier la traçabilité (date / équipe / produit).":
        "All sites are decontaminated: check traceability (date / team / product).",
    "Aucun site renseigné.": "No site entered.",
    "Généré le {d} à {h} • Complétude de la fiche : {score} % • Mapping Épi v{v}":
        "Generated on {d} at {h} • Record completeness: {score} % • Mapping Épi v{v}",
    "Lecture décisionnelle : chronologie • lieux • contacts • risque • PCI • laboratoire • actions":
        "Decision reading: chronology • places • contacts • risk • IPC • laboratory • actions",
    "TASK FORCE PRÉSIDENTIELLE EBOLA 17 - Système de Gestion de l'Incident MVE 17":
        "PRESIDENTIAL TASK FORCE EBOLA 17 - EVD 17 Incident Management System",
    # règles affichées (raisons du risque, synthèse des contacts, actions suggérées)
    "Saisi par l'investigateur": "Entered by the investigator", "Aucune étape documentée": "No step documented",
    "Décès suivi d'un enterrement non sécurisé": "Death followed by an unsafe burial",
    "non connu comme contact : chaîne de transmission non identifiée (+1 niveau)":
        "not known as a contact: transmission chain not identified (+1 level)",
    "contact connu et suivi": "known contact under follow-up",
    "Aucun contact à haut risque dénombré à ce stade.": "No high-risk contact counted at this stage.",
    "Les « ? » restent à compléter.": "The « ? » remain to be completed.",
    "Source d'exposition à confirmer": "Source of exposure to be confirmed",
    "Informations encore manquantes": "Information still missing", "Période non documentée": "Undocumented period",
    "Début des symptômes : contagiosité débutante": "Symptom onset: contagiousness beginning",
    "Soins d'un cas symptomatique": "Care of a symptomatic case", "Transport d'un cas symptomatique": "Transport of a symptomatic case",
    "Hospitalisation d'un cas symptomatique": "Hospitalisation of a symptomatic case",
    "Contacts communautaires d'un cas symptomatique": "Community contacts of a symptomatic case",
    "Rassemblement avec un cas symptomatique": "Gathering with a symptomatic case",
    "Déplacement d'un cas symptomatique": "Travel of a symptomatic case",
    "Décès : charge virale maximale, corps contagieux": "Death: maximum viral load, contagious body",
    "Funérailles : contacts rapprochés avec le corps": "Funeral: close contact with the body",
    "Enterrement non sécurisé": "Unsafe burial", "Manipulation d'échantillon / corps": "Handling of sample / body",
    "Circuit laboratoire encadré": "Supervised laboratory circuit", "Riposte en cours": "Response in progress",
    "Type d'étape non précisé": "Step type not specified",
    "Avant le début des symptômes (incubation) : non contagieux": "Before symptom onset (incubation): not contagious",
    "phase humide : très contagieux (liquides biologiques) +1 niveau": "wet phase: highly contagious (body fluids) +1 level",
    "phase humide probable (estimée) : vérifier les signes": "probable wet phase (estimated): check the signs",
    "phase critique : saignements / défaillances, très contagieux": "critical phase: bleeding / organ failure, highly contagious",
    "phase critique probable (estimée)": "probable critical phase (estimated)",
    "Enterrement digne et sécurisé": "Safe and dignified burial", "Prise en charge sécurisée du corps": "Safe handling of the body",
    "liquides biologiques : +1 niveau": "body fluids: +1 level", "absence de PCI : +1 niveau": "no IPC: +1 level",
    "contact avec le corps": "contact with the body",
    "Reconstituer la source d'exposition": "Reconstruct the source of exposure",
    "Sensibiliser la communauté (EDS) et suivre les participants aux funérailles":
        "Sensitise the community (SDB) and follow up funeral participants",
    "Documenter les délais de laboratoire": "Document laboratory delays",
    "Identifier et suivre les motards": "Identify and follow up motorcycle riders",
    "Documenter les périodes manquantes de la chronologie": "Document the missing periods of the chronology",
    "Boucler tous les contacts": "Close all contacts",

    # ------------------------------------------------------------------ réseau
    "RÉSEAU DE TRANSMISSION ET DE CONTACTS – {cas} {maladie} | ZS {zs}": "TRANSMISSION AND CONTACT NETWORK – {cas} {maladie} | HZ {zs}",
    "Cas index au centre • lieux d'exposition dans l'ordre du parcours • catégories de contacts à identifier / suivre":
        "Index case in the centre • exposure places in pathway order • contact categories to identify / follow up",
    "Cas {n}": "Case {n}", "Cas index": "Index case", "Cas ?": "Case ?",
    "Contacts listés": "Contacts listed", "À haut risque": "High risk", "Catégories « ? »": "« ? » categories",
    "Suivis": "Followed up", "Lieux d'exposition": "Exposure places", "Légende": "Legend",
    "Très élevé / très haut": "Very high", "Élevé / haut": "High", "Contrôlé / faible": "Controlled / low",
    "Nombre inconnu": "Unknown number", "Taille ∝ nombre": "Size ∝ number", "de contacts": "of contacts",

    # ------------------------------------------------------------------ carte du parcours
    "géographique (GPS)": "geographic (GPS)", "schématique (sans GPS)": "schematic (no GPS)",
    "CARTE DU PARCOURS – {cas} {maladie} | ZS {zs}": "PATHWAY MAP – {cas} {maladie} | HZ {zs}",
    "Déplacements du cas dans l'ordre chronologique • vue {mode} • fonctionne hors ligne":
        "Movements of the case in chronological order • {mode} view • works offline",
    "Étapes du parcours": "Pathway steps", "transport du corps": "transport of the body",
    "{n} autre(s) étape(s)": "{n} other step(s)", "Aucun déplacement documenté.": "No movement documented.",
    "Sites PCI · adresses": "IPC sites · addresses", "Déplacement du cas": "Movement of the case",
    "Transport du corps": "Transport of the body", "Couleur = niveau de risque": "Colour = risk level",
    "Les étapes laboratoire / investigation / riposte ne sont pas des déplacements du cas et ne figurent pas sur la carte. ":
        "Laboratory / investigation / response steps are not movements of the case and are not shown on the map. ",
    "Ajoutez la latitude/longitude des lieux pour une carte géographique.":
        "Add the latitude/longitude of the places for a geographic map.",

    # ------------------------------------------------------------------ frise temporelle
    "Laboratoire ({t})": "Laboratory ({t})", "délai prélèvement → résultat : {d} h": "delay sample → result: {d} h",
    "délai non documenté": "delay not documented", "Suivi des contacts ({n} j)": "Contact follow-up ({n} d)",
    "jusqu'au {d}": "until {d}",
    "FRISE TEMPORELLE – {cas} {maladie} | ZS {zs}": "TIMELINE – {cas} {maladie} | HZ {zs}",
    "Jours relatifs au J0 retenu • exposition estimée J-{a} → J-{b} • suivi des contacts {n} j":
        "Days relative to the retained D0 • estimated exposure D-{a} → D-{b} • contact follow-up {n} d",
    "Aucune étape datée : renseignez les dates de la chronologie.": "No dated step: enter the dates of the chronology.",
    "POINT D'INFECTION (EXPOSITION ESTIMÉE)": "POINT OF INFECTION (ESTIMATED EXPOSURE)",
    "PHASE SÈCHE": "DRY PHASE", "PHASE HUMIDE": "WET PHASE", "PÉRIODE CONTAGIEUSE": "CONTAGIOUS PERIOD",
    "Fin du suivi": "End of follow-up",
    "Barres pointillées = dates incertaines. Les bandes indiquent la fenêtre d'exposition probable et les phases sèche / "
    "humide calculées à partir de J0 (paramètres dans config/diseases.yaml).":
        "Dotted bars = uncertain dates. The bands show the probable exposure window and the dry / wet phases "
        "calculated from D0 (parameters in config/diseases.yaml).",

    # ------------------------------------------------------------------ multi-cas et lieux fréquentés
    "TABLEAU DE BORD MULTI-CAS": "MULTI-CASE DASHBOARD",
    "CAS RELIÉS PAR LES LIEUX FRÉQUENTÉS": "CASES LINKED BY PLACES VISITED",
    "Cas reliés lorsqu'ils ont fréquenté un même lieu • épaisseur ∝ nombre de lieux communs":
        "Cases linked when they visited the same place • thickness ∝ number of shared places",
    "Aucun cas enregistré.": "No case recorded.", "risque {r}": "risk {r}",
    "Lieux les plus fréquentés": "Most visited places", "Aucun lieu commun entre les cas.": "No shared place between the cases.",
    "{n} cas": "{n} cases", "{n} autre(s) lieu(x)": "{n} other place(s)",
    "{n} cas • {total} contacts dénombrés • {l} lieu(x) fréquenté(s) par au moins 2 cas. ":
        "{n} cases • {total} contacts counted • {l} place(s) visited by at least 2 cases. ",
    "Un lieu commun n'établit pas un lien de transmission : il oriente l'investigation.":
        "A shared place does not establish a transmission link: it guides the investigation.",
    "LIEUX LES PLUS FRÉQUENTÉS": "MOST VISITED PLACES",
    "{n} cas • lieux mentionnés dans les fiches (chronologie et lieux), fréquentés par au moins {m} cas • couleur = risque "
    "le plus élevé observé":
        "{n} cases • places mentioned in the records (chronology and places), visited by at least {m} cases • "
        "colour = highest risk observed",
    "Aucun lieu fréquenté par au moins {m} cas dans cette sélection.": "No place visited by at least {m} cases in this selection.",
    "LIEU": "PLACE", "NOMBRE DE CAS": "NUMBER OF CASES", "CAS • PÉRIODE • AIRES DE SANTÉ": "CASES • PERIOD • HEALTH AREAS",
    "dates ?": "dates ?", "{n} passages": "{n} visits", "{n} passage": "{n} visit",
    "{per} • AS : {aires} • risque max : {r}": "{per} • HA: {aires} • max risk: {r}",
    "Un lieu commun n'établit pas un lien de transmission : il oriente l'investigation, la décontamination et la "
    "sensibilisation. Les écritures d'un même lieu sont regroupées (casse, accents, parenthèses).":
        "A shared place does not establish a transmission link: it guides investigation, decontamination and "
        "awareness-raising. Spellings of the same place are grouped (case, accents, brackets).",

    # ------------------------------------------------------------------ lieux communs
    "LIEUX COMMUNS FRÉQUENTÉS PAR LES CAS": "SHARED PLACES VISITED BY THE CASES",
    "Lieux partagés par la fiche ouverte et les autres cas": "Places shared by the open record and the other cases",
    "Lieux fréquentés par au moins deux cas": "Places visited by at least two cases",
    "date du passage et période du cas à ce moment": "date of the visit and phase of the case at that time",
    "Aucun lieu commun entre les cas de votre périmètre.": "No shared place between the cases in your scope.",
    "Les lieux sont comparés à partir de la chronologie (Lieu / Arrivée) et de l'onglet Lieux":
        "Places are compared using the chronology (Place / Arrival) and the Places tab",
    "(casse, accents et précisions entre parenthèses ignorés).": "(case, accents and details in brackets ignored).",
    "LECTURE": "READING", "Transmission possible": "Possible transmission",
    "{a} contagieux → {b} exposé": "{a} contagious → {b} exposed", "Lieu commun à vérifier": "Shared place to be checked",
    "+ {n} lieu(x)": "+ {n} place(s)", "+ {n} cas": "+ {n} cases", "{x} non affichés : filtrez par zone": "{x} not shown: filter by zone",
    "{n} lieu(x) commun(s) • {p} avec transmission possible. ": "{n} shared place(s) • {p} with possible transmission. ",
    "Comparaison sur le nom du lieu (casse et accents ignorés). Un lieu commun oriente l'investigation, il ne prouve pas "
    "la transmission.":
        "Comparison on the place name (case and accents ignored). A shared place guides the investigation, it does not "
        "prove transmission.",
    "Cas contagieux lors du passage": "Case contagious during the visit",
    "Dans sa fenêtre d'exposition": "Within its exposure window", "Autre période / date inconnue": "Other period / unknown date",

    # ------------------------------------------------------------------ chaînes de transmission
    "CHAÎNES DE TRANSMISSION": "TRANSMISSION CHAINS",
    "Cas source → cas secondaires, par génération • trait : statut de contact • +n j : jours entre les J0 rapportés":
        "Source case → secondary cases, by generation • line: contact status • +n d: days between reported D0s",
    "Source / 1re génération": "Source / 1st generation", "Source / G1": "Source / G1", "Source": "Source",
    "Génération {n}": "Generation {n}", "Gén. {n}": "Gen. {n}", "{n} j": "{n} d", "issue": "outcome",
    "Aucun lien de transmission saisi.": "No transmission link entered.",
    "Dans chaque fiche (onglet Identité), renseignez « ID du cas source » :":
        "In each record (Identity tab), fill in « Source case ID »:",
    "l'ID (N° EPID) du cas dont ce cas est le contact.": "the ID (EPID No.) of the case this case is a contact of.",
    "Lien = ID du cas source saisi dans la fiche ; une « piste » (cas contagieux et cas exposé au même lieu) oriente "
    "l'investigation mais n'établit pas la transmission.":
        "Link = source case ID entered in the record; a « lead » (contagious case and exposed case at the same place) "
        "guides the investigation but does not establish transmission.",
    "{n} cas dans le périmètre": "{n} cases in scope", "{c} chaîne(s) • {n} cas reliés": "{c} chain(s) • {n} linked cases",
    "Chaîne la plus longue : {n} génération(s)": "Longest chain: {n} generation(s)", "Aucune chaîne": "No chain",
    "Intervalle moyen entre J0 : {m} j (n = {n})": "Mean interval between D0s: {m} d (n = {n})",
    "Intervalle entre J0 : ? (dates manquantes)": "Interval between D0s: ? (missing dates)",
    "+ {n} autre(s) chaîne(s) non affichée(s) : filtrez par province / zone.":
        "+ {n} other chain(s) not shown: filter by province / zone.",
    "Tous les cas sont rattachés.": "All cases are linked.", "et {n} autre(s)": "and {n} other(s)",
    "Aucune piste non reliée détectée.": "No unlinked lead detected.", "{a} → {b} ?": "{a} → {b} ?", "à {lieu}": "at {lieu}",
    "ID source « {src} » porté par {n} fiches : lien de {cas} ignoré": "Source ID « {src} » held by {n} records: link of {cas} ignored",
    "{cas} : boucle dans les cas sources (lien ignoré)": "{cas}: loop in the source cases (link ignored)",
}
