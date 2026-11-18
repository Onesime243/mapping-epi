"""Exports : PowerPoint (mapping et rapport), rapports par pilier Word / PowerPoint, liste des cas Excel, rapport de
situation Word, PCI Excel, symptômes, doublons, chaînes, tableau de bord et riposte (voir core/langue.py).

Les choix de listes (config/theme.py, core/rules.py) affichés dans les exports sont repris ici avec la même traduction
que config/en/valeurs.py. « ZS » / « AS » ne sont pas traduits ici (config/en/ui.py dit « Zone » / « Area ») : les
exports utilisent les sigles HZ / HA directement (core/indicateurs.sigle, core/echanges._zs, core/piliers._zs).
"""

# -- liste des cas Excel, rapport de situation Word, PCI Excel, symptômes, doublons, chaînes -------------------------
_LISTES = {
    # -- choix de listes affichés dans les exports (config/theme.py, core/rules.py) ----------------------------------
    "Oui": "Yes", "Non": "No", "Inconnu": "Unknown", "Inconnue": "Unknown", "ans": "years", "mois": "months",
    "Contact connu": "Known contact", "Contact connu suivi": "Known contact under follow-up", "Non contact": "Not a contact",
    "Phase sèche": "Dry phase", "Phase humide": "Wet phase", "Phase critique": "Critical phase",
    "Phase symptomatique": "Symptomatic phase", "Avant J0": "Before D0", "Non datée": "Undated",
    "En traitement": "Under treatment", "Vivant": "Alive", "Guéri": "Recovered", "Décès": "Death",
    "À investiguer": "To investigate", "En cours": "In progress", "Contrôlé": "Controlled", "Faible": "Low",
    "Modéré": "Moderate", "Élevé": "High", "Très élevé": "Very high", "Haut": "High", "Très haut": "Very high",
    "Urgent": "Urgent", "Important": "Important", "Normal": "Normal", "À faire": "To do", "Fait": "Done",
    "Partiel": "Partial", "Décontaminé": "Decontaminated",
    "Positif": "Positive", "Négatif": "Negative", "En attente": "Pending",
    "Moto": "Motorbike", "Véhicule": "Vehicle", "À pied": "On foot", "Pirogue": "Canoe", "Vélo": "Bicycle",
    "Ambulance": "Ambulance",
    "estimée": "estimated", "dernier contact": "last contact", "cas source": "source case", "à rechercher": "to be investigated",
    "saisie": "entered", "rapportée": "reported",
    "ZS": "HZ", "AS": "HA",          # ui.py dit « Zone » / « Area » : les exports utilisent _zs() (core/echanges.py)
    # types d'étapes
    "Exposition": "Exposure", "Investigation": "Investigation", "Période à documenter": "Period to document",
    "Début maladie": "Illness onset", "Soins / consultation": "Care / consultation", "Référence": "Referral",
    "Hospitalisation": "Hospitalisation", "Activité communautaire": "Community activity",
    "Rassemblement religieux": "Religious gathering", "Déplacement": "Travel", "Funérailles": "Funeral",
    "Enterrement": "Burial", "Prélèvement": "Sample", "Laboratoire": "Laboratory", "Riposte": "Response",
    "Autre": "Other",
    # symptômes (liste de la fiche et noms de l'analyse par phase)
    "Fièvre": "Fever", "Fatigue / asthénie": "Fatigue / asthenia", "Céphalées (maux de tête)": "Headache",
    "Douleurs articulaires": "Joint pain", "Douleurs musculaires": "Muscle pain", "Courbatures": "Body aches",
    "Mal au dos": "Back pain", "Mal de gorge": "Sore throat", "Diarrhée": "Diarrhoea", "Nausées": "Nausea",
    "Vomissements": "Vomiting", "Saignements": "Bleeding", "Hoquet": "Hiccups", "Rougeur oculaire": "Red eyes",
    "Méléna": "Melena", "Hématémèse": "Haematemesis", "Gingivorragie": "Gum bleeding", "Épistaxis": "Epistaxis",
    "Saignements aux points d'injection": "Bleeding at injection sites", "Anorexie": "Anorexia",
    "Douleurs abdominales": "Abdominal pain", "Toux": "Cough", "Éruption cutanée": "Skin rash",
    "Céphalées": "Headache", "Asthénie / fatigue": "Asthenia / fatigue",
    "Douleurs musculaires / courbatures": "Muscle pain / body aches", "Mal de dos": "Back pain",
    "Mal de gorge / dysphagie": "Sore throat / dysphagia", "Douleur thoracique": "Chest pain",
    "Dyspnée / détresse respiratoire": "Dyspnoea / respiratory distress", "Tuméfaction / œdème": "Swelling / oedema",
    "Saignements (non précisés)": "Bleeding (unspecified)", "Hématurie": "Haematuria",
    "Confusion / trouble de conscience": "Confusion / altered consciousness", "Convulsions": "Seizures",
    "Hypotension / choc": "Hypotension / shock", "Anurie / oligurie": "Anuria / oliguria",
    "liste de la fiche": "record checklist", "étape {date} · {titre}": "step {date} · {titre}",
    "étape · {titre}": "step · {titre}",

    # -- paquet de fiches -------------------------------------------------------------------------------------------
    "{n} fiche(s) ajoutée(s)": "{n} record(s) added", "{n} mise(s) à jour": "{n} updated",
    "{n} déjà à jour": "{n} already up to date",
    "{n} plus ancienne(s) que la version présente (ignorée(s))": "{n} older than the current version (ignored)",
    "{n} conflit(s) de N° EPID non importé(s) : ": "{n} EPID number conflict(s) not imported: ",
    "{n} hors de vos droits (ignorée(s))": "{n} outside your access rights (ignored)",
    "{n} fichier(s) illisible(s)": "{n} unreadable file(s)", "illisible ({e})": "unreadable ({e})",
    "Ce fichier n'est pas un paquet de fiches (.zip) Mapping Épi.": "This file is not a Mapping Épi record package (.zip).",
    "Paquet non reconnu : manifeste.json absent.": "Package not recognised: manifeste.json missing.",
    "Paquet non reconnu (format inattendu).": "Package not recognised (unexpected format).",
    "Paquet trop volumineux.": "Package too large.",

    # -- liste des cas (Excel) --------------------------------------------------------------------------------------
    "Liste des cas": "Case list", "Liste des cas Mapping Épi": "Mapping Épi case list",
    " · {n} cas · extraite le {quand}": " · {n} case(s) · extracted on {quand}",
    "N° EPID": "EPID number", "Province": "Province", "Zone de santé": "Health zone", "Aire de santé": "Health area",
    "Sexe": "Sex", "Âge": "Age", "Profession": "Occupation", "Agent de santé (PPL)": "Health worker (HCW)",
    "Vacciné": "Vaccinated", "Date de vaccination": "Vaccination date", "ID du cas source": "source case ID",
    "Dernier contact avec la source": "Last contact with the source",
    "Début des symptômes (rapporté)": "Symptom onset (reported)", "Phase des premiers signes": "Phase of first signs",
    "J0 retenu": "Retained D0", "Notification": "Notification", "Confirmation": "Confirmation",
    "Isolement (1re hospitalisation)": "Isolation (1st hospitalisation)", "Début → isolement (j)": "Onset → isolation (d)",
    "État": "Status", "Date de décès": "Date of death", "Décès communautaire": "Community death",
    "Enterrement sécurisé": "Safe burial", "Contacts listés": "Contacts listed", "Contacts suivis": "Contacts followed up",
    "Risque global": "Overall risk", "Complétude (%)": "Completeness (%)", "Actions ouvertes": "Open actions",
    "Modifiée le": "Modified", "Modifiée par": "Modified by",
    # feuilles
    "Modélisation": "Modelling", "Variables": "Variables", "Variable": "Variable", "Description": "Description",
    "Symptômes par phase": "Symptoms by phase", "Symptômes par date": "Symptoms by date",
    "Symptômes (détail)": "Symptoms (detail)", "Fréquence par phase": "Frequency by phase", "Règle": "Rule",
    "Symptômes les plus fréquents par phase (cas dont la phase est documentée dans la fiche)":
        "Most frequent symptoms by phase (cases whose phase is documented in the record)",
    "{phase} · {n} cas documentés": "{phase} · {n} documented case(s)", "Nombre de cas": "Number of cases",
    "% des cas documentés": "% of documented cases",
    "Aucun symptôme rapporté dans cette phase.": "No symptom reported in this phase.",
    "Pour chaque étape du parcours qui cite des symptômes : date_n = date de l'étape, "
    "symptomes_n = symptômes cités ce jour-là, jour_n = jour depuis le J0 retenu (J±n), phase_n et etape_n.":
        "For each care pathway step that mentions symptoms: date_n = date of the step, symptomes_n = symptoms mentioned "
        "that day, jour_n = day since the retained D0 (D±n), phase_n and etape_n (step).",
    "Colonnes <phase>_<symptôme> : 1 = rapporté dans la phase, 0 = phase documentée sans ce symptôme, vide = phase non "
    "documentée. Sources : symptômes cochés dans la fiche et texte des étapes du parcours (« Symptômes (détail) » donne "
    "la source).":
        "Columns <phase>_<symptom> (seche = dry, humide = wet, critique = critical): 1 = reported in the phase, "
        "0 = phase documented without this symptom, empty = phase not documented. Sources: symptoms checked in the "
        "record and text of the care pathway steps (\"Symptoms (detail)\" gives the source).",
    "Une case vide = information non renseignée (jamais 0). Dates au format jj/mm/aaaa. Les phases sèche, humide et "
    "critique viennent de la fiche (dates saisies ou rapportées), sinon de l'estimation de l'outil (colonne « origine »). "
    "Exemples fictifs exclus.":
        "An empty cell = information not provided (never 0). Dates in dd/mm/yyyy format. The dry, wet and critical "
        "phases come from the record (entered or reported dates), otherwise from the tool's estimate (\"origine\" "
        "column). Fictitious examples excluded.",
    # descriptions des variables (feuille Variables)
    "N° EPID du cas": "Case EPID number", "Âge en années (mois convertis)": "Age in years (months converted)",
    "Agent de santé / prestataire (PPL)": "Health worker / provider (HCW)",
    "Vacciné (Oui / Non / Inconnu)": "Vaccinated (Yes / No / Unknown)",
    "Statut de contact (connu, connu suivi, non contact)": "Contact status (known, known and followed up, not a contact)",
    "Dernier contact avec le cas source": "Last contact with the source case",
    "Début de la fenêtre d'exposition": "Start of the exposure window", "Fin de la fenêtre d'exposition": "End of the exposure window",
    "Origine de la fenêtre (estimée, dernier contact, cas source)": "Origin of the window (estimated, last contact, source case)",
    "Début des symptômes rapporté par l'équipe": "Symptom onset reported by the team",
    "Phase des premiers signes rapportés": "Phase of the first reported signs",
    "Jours retirés pour obtenir le J0 retenu": "Days subtracted to obtain the retained D0",
    "J0 retenu (début réel estimé)": "Retained D0 (estimated actual onset)",
    "Début de la phase sèche (= J0 retenu)": "Start of the dry phase (= retained D0)",
    "Symptômes de la phase sèche rapportés": "Reported dry phase symptoms",
    "Début de la phase humide": "Start of the wet phase",
    "Origine de la date (saisie, rapportée, estimée)": "Origin of the date (entered, reported, estimated)",
    "Symptômes de la phase humide rapportés": "Reported wet phase symptoms",
    "Début de la phase critique": "Start of the critical phase", "Origine de la date": "Origin of the date",
    "Signes de la phase critique (hémorragiques) rapportés": "Reported critical phase signs (haemorrhagic)",
    "Autres symptômes": "Other symptoms", "Durée de la phase sèche (jours)": "Duration of the dry phase (days)",
    "Durée de la phase humide (jours)": "Duration of the wet phase (days)",
    "Durée de la phase critique jusqu'au décès (jours)": "Duration of the critical phase until death (days)",
    "Date de notification": "Notification date", "Date de confirmation": "Confirmation date",
    "J0 rapporté → notification (jours)": "Reported D0 → notification (days)",
    "J0 rapporté → confirmation (jours)": "Reported D0 → confirmation (days)",
    "Notification → confirmation (jours)": "Notification → confirmation (days)",
    "J0 rapporté → isolement (jours)": "Reported D0 → isolation (days)", "Premier prélèvement": "First sample",
    "Premier résultat": "First result", "Prélèvement → résultat (heures)": "Sample → result (hours)",
    "Résultat du laboratoire": "Laboratory result", "Début de la vaccination en anneau": "Start of ring vaccination",
    "Confirmation → anneau (jours)": "Confirmation → ring (days)", "État du cas": "Case status",
    "J0 retenu → décès (jours)": "Retained D0 → death (days)", "Décès hors structure de soins": "Death outside a health facility",
    "Enterrement digne et sécurisé": "Safe and dignified burial", "Date de l'enterrement": "Date of burial",
    "Contacts listés (catégories dénombrées)": "Contacts listed (counted categories)",
    "Contacts à haut ou très haut risque": "High or very high risk contacts", "Contacts vaccinés": "Contacts vaccinated",
    "Catégories de contacts non dénombrées": "Contact categories not counted",
    "Nombre d'étapes de la chronologie": "Number of timeline steps", "Nombre de lieux d'exposition": "Number of exposure places",
    "Nombre de déplacements": "Number of trips", "Moyens de transport utilisés": "Means of transport used",
    "Étapes avec contact avec le corps": "Steps with body contact", "Étapes avec liquides biologiques": "Steps with body fluids",
    "Étapes de soins sans PCI": "Care steps without IPC", "Funérailles ou enterrements": "Funerals or burials",
    "Sites PCI renseignés": "IPC sites entered", "Sites décontaminés": "Decontaminated sites",
    "Sites PCI « Non » ou inconnu": "IPC sites \"No\" or unknown", "Résultat du séquençage": "Sequencing result",
    "Complétude de la fiche (%)": "Record completeness (%)",

    # -- rapport de situation (Word) --------------------------------------------------------------------------------
    "RAPPORT DE SITUATION : MALADIE À VIRUS EBOLA": "SITUATION REPORT: EBOLA VIRUS DISEASE",
    "{n} derniers jours": "last {n} days", "depuis le début": "since the start", "Depuis le début": "Since the start",
    "Périmètre : {p}": "Scope: {p}", "tous les cas": "all cases", " · province {p}": " · province {p}",
    " · situation au {d} · indicateurs : {lib}": " · situation as of {d} · indicators: {lib}",
    "Généré automatiquement par Mapping Épi à partir des fiches de cas. À valider avant diffusion.":
        "Generated automatically by Mapping Épi from the case records. To be validated before distribution.",
    "1. Situation générale": "1. General situation", "Cas confirmés": "Confirmed cases",
    "Létalité (décès / cas)": "Case fatality (deaths / cases)", "Zones de santé touchées": "Health zones affected",
    "Agents de santé (PPL) parmi les cas": "Health workers (HCW) among the cases",
    "2. Courbe épidémique (cas par semaine de début de la maladie)": "2. Epidemic curve (cases by week of illness onset)",
    "Total": "Total", "dont décès": "of which deaths",
    "Semaines commençant le lundi indiqué ; {n} dernières semaines affichées.":
        "Weeks starting on the Monday shown; last {n} weeks displayed.",
    " {n} cas sans date de début placé(s) à la date de notification.":
        " {n} case(s) without an onset date placed at the notification date.",
    " {n} cas sans aucune date non représenté(s).": " {n} case(s) without any date not shown.",
    "Aucun cas daté.": "No dated case.", "3. Catégories des zones de santé": "3. Health zone categories",
    "Cat.": "Cat.", "Cas": "Cases", "7 derniers j": "Last 7 d", "21 derniers j": "Last 21 d", "Dernier cas": "Last case",
    "Jours sans cas": "Days without a case",
    "4. Indicateurs clés de la riposte ({lib})": "4. Key response indicators ({lib})",
    "Domaine": "Area", "Indicateur": "Indicator", "Résultat": "Result", "Cible": "Target", "Non renseigné": "Not provided",
    "Cibles indicatives, à valider par la coordination. Les informations non renseignées sont exclues du pourcentage "
    "et comptées à part.":
        "Indicative targets, to be validated by the coordination. Information not provided is excluded from the "
        "percentage and counted separately.",
    "5. Alertes : nouveau foyer possible (21 derniers jours)": "5. Alerts: possible new outbreak focus (last 21 days)",
    "Notifié le": "Notified on", "Lieu": "Place", "Lecture": "Interpretation",
    "Aucune alerte sur la période.": "No alert over the period.",
    "6. Actions ouvertes sur les fiches de cas": "6. Open actions on the case records",
    "{o} action(s) ouverte(s), dont {r} en retard et {u} urgente(s) ; {s} sans responsable.":
        "{o} open action(s), of which {r} overdue and {u} urgent; {s} without a person in charge.",
    "Action": "Action", "Priorité": "Priority", "Responsable": "Responsible", "Échéance": "Due date",
    "Retard": "Delay", "{n} j": "{n} d", "7. Points d'attention": "7. Points of attention",

    # -- PCI : lieux et adresses (Excel) ----------------------------------------------------------------------------
    "Lieux et adresses": "Places and addresses", "PCI : lieux fréquentés et adresses": "IPC: places visited and addresses",
    " · {cas} cas · {lieux} lieux ({adr} avec adresse) · extrait le {quand}":
        " · {cas} case(s) · {lieux} place(s) ({adr} with address) · extracted on {quand}",
    "ID du cas": "Case ID", "Lieu fréquenté": "Place visited", "Origine": "Source", "Première date": "First date",
    "Étape(s) du parcours": "Care pathway step(s)", "Adresse": "Address",
    "Statut PCI / décontamination": "IPC / decontamination status", "Date PCI": "IPC date", "Équipe PCI": "IPC team",
    "Résumé par cas": "Summary by case", "Lieux fréquentés": "Places visited", "Avec adresse": "With address",
    "Sans adresse": "Without address", "Pas de site PCI saisi": "No IPC site entered",
    "Parcours": "Pathway", "Lieu saisi": "Entered place", "Site PCI": "IPC site",
    "Parcours + Lieu saisi": "Care pathway + Place entered", "Parcours + Site PCI": "Care pathway + IPC site",
    "Lieu saisi + Site PCI": "Place entered + IPC site",
    "Parcours + Lieu saisi + Site PCI": "Care pathway + Place entered + IPC site",

    # -- doublons et chaînes -----------------------------------------------------------------------------------------
    "même N° EPID ({code})": "same EPID number ({code})",
    "même ZS, sexe, âge et début des symptômes, mais N° EPID différents":
        "same HZ, sex, age and symptom onset, but different EPID numbers",
    "même ZS, sexe, âge et début des symptômes": "same HZ, sex, age and symptom onset",
    "{cas} · ZS {zs}": "{cas} · HZ {zs}",
    "ID source « {src} » porté par {n} fiches : lien de {cas} ignoré":
        "Source ID « {src} » held by {n} records: link of {cas} ignored",
    "{cas} : boucle dans les cas sources (lien ignoré)": "{cas}: loop in the source cases (link ignored)",
}

# -- tableau de bord, riposte (indicateurs, courbe, actions), catégories des ZS et délais ------------------------------
_TABLEAU_RIPOSTE = {
    # unités et mots courts
    "j": "d", "%": "%", "non renseigné": "not entered", "stable": "stable", "mieux": "better",
    "moins bien": "worse", "décès": "death", "cible": "target", "ZS ?": "HZ ?",
    "Autres ZS": "Other HZ", "ZS non renseignée": "HZ not specified", "S{n}": "W{n}",
    "{n:.0f} point": "{n:.0f} point", "{n:.0f} points": "{n:.0f} points",
    # valeurs de listes affichées (theme / rules)
    "Urgent": "Urgent", "Important": "Important", "Normal": "Normal", "À faire": "To do", "En cours": "In progress",
    "Fait": "Done", "Critique": "Critical", "À surveiller": "To monitor", "À jour": "Up to date",
    "Contact connu": "Known contact", "Contact connu suivi": "Known contact under follow-up", "Non contact": "Not a contact",
    "Inconnu": "Unknown",

    # -- tableau de bord : catégories d'actions
    "Vérifiées": "Verified", "Réalisées, à vérifier": "Done, to verify", "Réalisées sans preuve": "Done without proof",
    "En cours ou à faire": "In progress or to do", "En retard": "Overdue", "Bloquées": "Blocked",
    # alertes par cas
    "{n} contacts à haut risque listés, aucun en suivi.": "{n} high-risk contacts listed, none followed up.",
    "{n} contacts à haut risque listés, suivi non renseigné.": "{n} high-risk contacts listed, follow-up not specified.",
    "{s} sur {n} contacts à haut risque suivis ({p:.0f} %).": "{s} of {n} high-risk contacts followed up ({p:.0f} %).",
    "aucun contact listé.": "no contact listed.",
    "{d} jours entre début des symptômes et confirmation (seuil {s} j).":
        "{d} days between symptom onset and confirmation (threshold {s} d).",
    "{n} lieu(x) avec PCI « Non » ou inconnue ({sites}).": "{n} place(s) with IPC \"No\" or unknown ({sites}).",
    "{n} action(s) urgente(s) en retard de plus de {j} jours.": "{n} urgent action(s) overdue by more than {j} days.",
    "nom de personne dans un texte libre (n’écrire que des identifiants).":
        "person name in a free text (write identifiers only).",
    "{n} action(s) déclarée(s) réalisée(s) sans preuve.": "{n} action(s) reported as done without proof.",
    # tuiles
    "Cas mappés": "Mapped cases", "Axes A, B": "Axes A, B",
    "complétude moyenne {p:.0f} % · {n} fiche(s) à 90 % ou plus":
        "average completeness {p:.0f} % · {n} record(s) at 90 % or more",
    "aucun cas sur la période": "no case in the period", "{d:+d} vs période précédente": "{d:+d} vs previous period",
    "Actions vérifiées": "Verified actions", "Axes N, H": "Axes N, H",
    "{p} · {r} en retard · {b} bloquée(s) · {s} sans preuve": "{p} · {r} overdue · {b} blocked · {s} without proof",
    "aucune action prescrite": "no action prescribed",
    "Délai symptômes → confirmation": "Delay symptoms → confirmation", "Axes C, F, I": "Axes C, F, I",
    "médiane · {k} cas renseignés sur {n} · {p} en {s} j ou moins":
        "median · {k} of {n} cases with data · {p} within {s} d or less",
    "Lieux d'exposition décontaminés": "Exposure places decontaminated", "Axes G, L, O, P": "Axes G, L, O, P",
    "{p} · {n} avec PCI « Non » ou inconnue": "{p} · {n} with IPC \"No\" or unknown",
    "aucun lieu PCI renseigné": "no IPC place recorded",
    # évolution sur 8 semaines
    "aucune donnée sur 8 semaines": "no data over 8 weeks", "(semaine du {d})": "(week of {d})",
    "une seule semaine avec des données": "only one week with data",
    "{d:+.0f} vs semaine précédente": "{d:+.0f} vs previous week",
    # expositions
    "Contact avec le corps": "Contact with the body", "Liquides biologiques": "Body fluids",
    "Soins sans PCI": "Care without IPC", "Funérailles ou enterrement": "Funeral or burial", "Déplacements": "Travel",
    # graphique des semaines
    "Aucune semaine dans la période.": "No week in the period.",
    "Cas par semaine et délai médian": "Cases per week and median delay",
    "Semaine du {d} : {n} cas": "Week of {d}: {n} cases",
    "Semaine du {d} : délai médian {v}": "Week of {d}: median delay {v}",

    # -- riposte : indicateurs clés
    "Détection": "Detection", "Délais": "Delays", "Décès": "Death", "Contacts": "Contacts",
    "Vaccination en anneau": "Ring vaccination", "Populations": "Populations", "Laboratoire": "Laboratory",
    "Qualité des données": "Data quality",
    "Nouveaux cas déjà connus comme contacts": "New cases already known as contacts",
    "part des cas qui figuraient sur une liste de contacts : mesure si la riposte devance l'épidémie":
        "share of cases who were on a contact list: shows whether the response is ahead of the epidemic",
    "Parmi eux, contacts suivis au moment de la maladie": "Among them, contacts followed up when they fell ill",
    "contact connu ET suivi quotidiennement avant le début des signes":
        "known contact AND followed up daily before symptom onset",
    "Cas sans lien épidémiologique connu": "Cases with no known epidemiological link",
    "chaînes de transmission invisibles : investigation approfondie de la source":
        "invisible transmission chains: in-depth investigation of the source",
    "Délai médian début des symptômes → isolement": "Median delay symptom onset → isolation",
    "{n} cas avec une hospitalisation datée dans la chronologie": "{n} case(s) with a dated hospitalisation in the timeline",
    "Cas isolés dans les 3 jours suivant le début des symptômes": "Cases isolated within 3 days of symptom onset",
    "plus l'isolement est tardif, plus le cas a eu de contacts dans la communauté":
        "the later the isolation, the more contacts the case had in the community",
    "Délai médian début des symptômes → notification": "Median delay symptom onset → notification",
    "Décès survenus dans la communauté": "Community deaths",
    "décès sans hospitalisation : cas non détectés à temps, risque élevé aux funérailles":
        "deaths without hospitalisation: cases not detected in time, high risk at funerals",
    "Enterrements dignes et sécurisés": "Safe and dignified burials",
    "étape « Enterrement » de la chronologie, case « sécurisé » cochée":
        "\"Burial\" step of the timeline, \"safe\" box ticked",
    "Contacts suivis parmi les contacts listés": "Contacts followed up among listed contacts",
    "groupes de contacts dont le nombre listé et le nombre suivi sont renseignés":
        "contact groups with both the listed and followed-up numbers recorded",
    "Cas avec au moins un groupe de contacts listé": "Cases with at least one contact group listed",
    "Contacts vaccinés parmi les contacts listés": "Contacts vaccinated among listed contacts",
    "colonne « Vaccinés » des groupes de contacts": "\"Vaccinated\" column of the contact groups",
    "Délai médian confirmation → début de l'anneau": "Median delay confirmation → ring start",
    "date « Début de la vaccination de l'anneau » de la fiche": "\"Ring vaccination start\" date of the record",
    "Cas avec un anneau vacciné": "Cases with a vaccinated ring",
    "Cas parmi les agents de santé (PPL)": "Cases among health workers (HCW)",
    "infection d'un agent de santé : signal d'alerte sur la PCI dans la structure":
        "infection of a health worker: warning sign about IPC in the facility",
    "Cas vaccinés": "Vaccinated cases", "statut vaccinal renseigné dans la fiche": "vaccination status recorded in the record",
    "Cas confirmés avec un résultat de séquençage": "Confirmed cases with a sequencing result",
    "confirme ou corrige les chaînes de transmission": "confirms or corrects the transmission chains",
    "Fiches complètes à 80 % ou plus": "Records 80 % complete or more",
    "100 %": "100 %", "0 %": "0 %", "≤ 3 j": "≤ 3 d", "≥ 80 %": "≥ 80 %", "≥ 90 %": "≥ 90 %",
    # nombre de reproduction
    "aucun cas avec un début de maladie de plus de {j} jours": "no case with illness onset more than {j} days ago",
    "{s} cas secondaires reliés à {n} cas de plus de {j} jours ; sous-estimé si des liens (ID du cas source) ne sont pas saisis":
        "{s} secondary cases linked to {n} cases older than {j} days; underestimated if links (source case ID) are not entered",
    # courbe épidémique
    "Aucun cas daté : la courbe ne peut pas être tracée.": "No dated case: the curve cannot be drawn.",
    "Courbe épidémique": "Epidemic curve", "{n} cas (semaine du {d})": "{n} case(s) (week of {d})",
    # points d'attention
    "{nom} : {v} (cible {c}).": "{nom}: {v} (target {c}).",
    "Transmission active (catégorie 1) : ZS {zs}.": "Active transmission (category 1): HZ {zs}.",
    "{n} alerte(s) de nouveau foyer possible à investiguer.": "{n} possible new outbreak alert(s) to investigate.",
    "{n} action(s) en retard sur les fiches de cas.": "{n} overdue action(s) on case records.",
    "Aucun indicateur en alerte sur la période.": "No indicator on alert in the period.",
    # vues HTML
    "atteint": "achieved", "à surveiller": "to monitor", "alerte": "warning", "information": "information",
    "{n} non renseigné(s)": "{n} not specified", "{n} cas concerné(s)": "{n} case(s) concerned",
    "Aucune action ouverte dans ce périmètre.": "No open action in this scope.", "{n} j de retard": "{n} d overdue",
    "à désigner": "to be assigned", "Cas": "Cases", "Action": "Action", "Priorité": "Priority",
    "Responsable": "Responsible", "Échéance": "Due date", "Statut": "Status",

    # -- indicateurs : catégories des ZS, alertes de foyer, délais
    "Aucun cas daté": "No dated case", "Transmission active": "Active transmission",
    "Notification espacée": "Spaced notification", "21 à 42 jours sans cas": "21 to 42 days without cases",
    "Plus de 42 jours sans cas": "More than 42 days without cases",
    "premier cas notifié dans la ZS : nouveau foyer possible": "first case notified in the HZ: possible new outbreak",
    "reprise après {n} jours sans cas dans la ZS": "resurgence after {n} days without cases in the HZ",
    "première aire touchée : AS {a} (ZS {z})": "first area affected: HA {a} (HZ {z})",
    "médiane {m:g} j (moyenne {moy:.1f} ; {a} à {b} j)": "median {m:g} d (mean {moy:.1f}; {a} to {b} d)",
    "Début des symptômes → notification": "Symptom onset → notification",
    "délai de détection : plus il est court, moins le cas a eu de contacts non suivis":
        "detection delay: the shorter it is, the fewer unmonitored contacts the case had",
    "Notification → confirmation": "Notification → confirmation",
    "circuit d'alerte, prélèvement et laboratoire": "alert circuit, sampling and laboratory",
    "Incubation observée": "Observed incubation",
    "contacts connus : début des symptômes − dernier contact avec le cas source":
        "known contacts: symptom onset − last contact with the source case",
    "Intervalle sériel": "Serial interval",
    "début des symptômes du cas − celui de son cas source enregistré dans l'outil":
        "symptom onset of the case − that of its source case recorded in the tool",
}

# -- mapping PowerPoint, rapports par pilier (Word / PowerPoint) -------------------------------------------------------
_RAPPORTS = {
    # -- mapping PowerPoint (render/pptx_v2.py, render/pptx_exporter.py) ------------------------------------------------
    "CHRONOLOGIE DU PARCOURS": "PATHWAY CHRONOLOGY", "Chronologie du parcours": "Pathway chronology",
    "ID DU CAS SOURCE : À COMPLÉTER": "SOURCE CASE ID: TO BE COMPLETED",
    "ID du cas source : à compléter": "Source case ID: to be completed",
    "J±n : jours depuis le J0 retenu (date rapportée − {n} j)": "D±n: days since the retained D0 (reported date − {n} d)",
    "J±n : jours depuis le J0 retenu ou estimé": "D±n: days since the retained or estimated D0",
    " · jours chargés agrandis": " · busy days enlarged",
    "Aucune date dans la chronologie : renseigner les dates des étapes pour afficher la frise.":
        "No dates in the chronology: enter the step dates to display the timeline.",
    "? personnes présentes": "? people present", "Aucune étape dans la chronologie.": "No steps in the chronology.",
    "Contacts à identifier / suivre": "Contacts to identify / follow up", "PCI / décontamination": "IPC / decontamination",
    "Lieux & expositions": "Places & exposures", "Actions": "Actions",
    "? à dénombrer": "? to count", " · {n} suivis": " · {n} followed up",
    "Aucun groupe de contacts renseigné.": "No contact group entered.",
    "? {n} lieux d’exposition sans statut PCI :": "? {n} exposure places without IPC status:",
    "? {n} lieu d’exposition sans statut PCI :": "? {n} exposure place without IPC status:",
    "Priorité : fermer les sites non décontaminés ; noter date, équipe et produit.":
        "Priority: close the sites not decontaminated; record date, team and product.",
    "Aucun site renseigné.": "No site entered.", "suggérées, à valider": "suggested, to be validated",
    "responsable · échéance": "responsible · deadline", "À réaliser immédiatement": "To do immediately",
    "À RÉALISER IMMÉDIATEMENT": "TO DO IMMEDIATELY", "DÉJÀ RÉALISÉES": "ALREADY DONE", "Déjà réalisées": "Already done",
    "à désigner": "to be assigned", " (en cours)": " (in progress)", "Aucune action.": "No actions.",
    "Actions suggérées automatiquement, à valider.": "Actions suggested automatically, to be validated.",

    # -- rapport par pilier : Word et PowerPoint (core/rapport_rendu.py) ------------------------------------------------
    "Aucune donnée sur la période.": "No data for the period.",
    "Mapping Épi · rapport par pilier · page ": "Mapping Épi · report by pillar · page ",
    "RÉPUBLIQUE DÉMOCRATIQUE DU CONGO": "DEMOCRATIC REPUBLIC OF THE CONGO",
    "Système de gestion de l'incident (SGI) : riposte à la Maladie à Virus Ebola":
        "Incident Management System (IMS): Ebola Virus Disease response",
    "RAPPORT D'ANALYSE PAR PILIER": "ANALYSIS REPORT BY PILLAR",
    "Suivi des mappings épidémiologiques des cas de MVE": "Monitoring of the epidemiological mappings of EVD cases",
    "Période": "Period", "du {debut} au {fin}": "from {debut} to {fin}", "Périmètre": "Scope",
    "Cas analysés": "Cases analysed", "{n} cas notifiés sur la période ({total} au total)":
        "{n} cases notified in the period ({total} in total)",
    "Piliers": "Pillars", "Généré le": "Generated on", "{date} à {heure}": "{date} at {heure}",
    "Généré automatiquement par Mapping Épi à partir des fiches de cas enregistrées. "
    "À valider par les responsables des piliers avant diffusion.":
        "Generated automatically by Mapping Épi from the saved case records. "
        "To be validated by the pillar leads before distribution.",
    "Résumé exécutif": "Executive summary", "Pilier": "Pillar", "Indicateur clé": "Key indicator", "Valeur": "Value",
    "Points d'attention": "Points of attention", "Méthode": "Method",
    "Période : cas dont la date de notification (à défaut de confirmation, puis de début des symptômes) tombe "
    "entre les deux dates choisies. Les exemples fictifs et les brouillons sont exclus.":
        "Period: cases whose notification date (failing that the confirmation date, then the symptom onset date) falls "
        "between the two chosen dates. Fictitious examples and drafts are excluded.",
    "Source : fiches de cas enregistrées dans Mapping Épi, dans le périmètre du compte.":
        "Source: case records saved in Mapping Épi, within the account's scope.",
    "Règle : une information non renseignée n'est jamais remplacée par zéro ; elle est exclue du calcul et "
    "le dénominateur est indiqué entre parenthèses.":
        "Rule: missing information is never replaced by zero; it is excluded from the calculation and "
        "the denominator is shown in brackets.",
    "Questions : sélection du cadre d'analyse des mappings MVE (UMIE-INRB) ; celles qui demandent des données "
    "absentes de l'outil sont listées en annexe.":
        "Questions: selection from the EVD mapping analysis framework (UMIE-INRB); those needing data "
        "not in the tool are listed in the appendix.",
    "Figure": "Figure", "Questions d'analyse": "Analysis questions", "Question": "Question", "Réponse": "Answer",
    "Aucun point d'attention majeur sur la période.": "No major point of attention in the period.",
    "Annexe : questions non couvertes faute de données": "Appendix: questions not covered for lack of data",
    "Ces questions du cadre d'analyse demandent des informations que l'outil ne recueille pas encore. "
    "Les ajouter permettrait d'y répondre dans les prochains rapports.":
        "These framework questions need information the tool does not collect yet. "
        "Adding it would allow them to be answered in future reports.",
    "Axe": "Axis", "Donnée nécessaire": "Data needed", "{debut} au {fin}": "{debut} to {fin}",
    "Rapport d'analyse par pilier": "Analysis report by pillar",
    "Riposte à la Maladie à Virus Ebola · suivi des mappings épidémiologiques":
        "Ebola Virus Disease response · monitoring of epidemiological mappings",
    "Période : du {debut} au {fin}": "Period: from {debut} to {fin}", "Périmètre : {p}": "Scope: {p}",
    "{n} cas analysés": "{n} cases analysed", "Messages clés": "Key messages",
    "Généré à partir des fiches enregistrées ; à valider en réunion": "Generated from the saved records; to be validated in a meeting",
    "Questions non couvertes et prochaines étapes": "Questions not covered and next steps",
    "Données à ajouter dans l'outil pour répondre au cadre complet": "Data to add to the tool to answer the full framework",
    "Suivis": "Followed up", "Vaccinés": "Vaccinated", "Décontaminé": "Decontaminated", "Partiel": "Partial",

    # -- rapport par pilier : contenu (core/piliers.py) ---------------------------------------------------------------
    "Surveillance et investigation": "Surveillance and investigation", "Contacts et vaccination": "Contacts and vaccination",
    "Prévention et contrôle des infections (PCI)": "Infection prevention and control (IPC)",
    "Laboratoire et prise en charge": "Laboratory and case management", "Actions et coordination": "Actions and coordination",
    "Qualité des données": "Data quality",
    # piliers des actions (config/theme.py PILIERS) et types / catégories affichés
    "Surveillance": "Surveillance", "Suivi des contacts": "Contact follow-up", "Vaccination": "Vaccination", "PCI": "IPC",
    "Laboratoire": "Laboratory", "Prise en charge": "Case management", "Engagement communautaire": "Community engagement",
    "Coordination": "Coordination", "Autre": "Other",
    "ZS ?": "HZ ?",
    "Vérifier que chaque cas est investigué vite et à fond : délais, parcours, sources et chaînes.":
        "Check that each case is investigated quickly and thoroughly: delays, pathway, sources and chains.",
    "Cas notifiés": "Cases notified", "Zones de santé touchées": "Health zones affected",
    "Délai médian début → notification": "Median delay onset → notification",
    "Cas sans lien épidémiologique": "Cases without an epidemiological link",
    "Combien de cas confirmés ont été notifiés durant la période ?": "How many confirmed cases were notified in the period?",
    "{n} cas dans {z} zone(s) de santé.": "{n} case(s) in {z} health zone(s).",
    "Quel est le délai entre la notification et la création du mapping ?":
        "What is the delay between notification and creation of the mapping?",
    "Médiane {med} ; créés le jour même ou le lendemain : {a} ; dans les 48 h : {b} ; après plus de 72 h : {c}.":
        "Median {med}; created the same or the next day: {a}; within 48 h: {b}; after more than 72 h: {c}.",
    "Combien de mappings sont restés au statut brouillon ?": "How many mappings remained as drafts?",
    "{n} brouillon(s) non enregistré(s) dans le périmètre, champs obligatoires manquants.":
        "{n} unsaved draft(s) in the scope, required fields missing.",
    "Quel est le délai entre le début des symptômes et la première consultation ?":
        "What is the delay between symptom onset and the first consultation?",
    "Médiane {med} ({n} cas avec une consultation datée).": "Median {med} ({n} case(s) with a dated consultation).",
    "Quel est le délai entre le début des symptômes et la notification ?":
        "What is the delay between symptom onset and notification?",
    "Médiane {med} ({n} cas).": "Median {med} ({n} case(s)).",
    "Quel est le délai entre la notification et la confirmation ?": "What is the delay between notification and confirmation?",
    "Combien de lieux ont été fréquentés par chaque cas ?": "How many places did each case visit?",
    "Médiane {med} par cas ; {n} lieux au total.": "Median {med} per case; {n} places in total.",
    "Quels types de lieux sont les plus fréquemment visités ?": "Which types of places are visited most often?",
    "Aucun lieu renseigné.": "No place entered.",
    "Combien de cas ont fréquenté des établissements de soins ?": "How many cases visited health facilities?",
    "Combien ont utilisé un moyen de transport (déplacement documenté) ?": "How many used transport (documented travel)?",
    "Quels lieux sont fréquentés par plusieurs cas ?": "Which places were visited by several cases?",
    "{lieu} ({n} cas)": "{lieu} ({n} cases)", "Aucun lieu commun détecté.": "No shared place detected.",
    "Quelle proportion des cas possède une source probable d'infection identifiée ?":
        "What proportion of cases have an identified probable source of infection?",
    "{p} avec un ID de cas source renseigné.": "{p} with a source case ID entered.",
    "Combien de cas restent sans lien épidémiologique identifié ?": "How many cases remain without an identified epidemiological link?",
    "{a} cas « non contact » ; {b} cas au statut inconnu.": "{a} \"not a contact\" case(s); {b} case(s) with unknown status.",
    "Combien de chaînes de transmission ont pu être reconstruites ?": "How many transmission chains could be reconstructed?",
    "{a} chaîne(s) d'au moins deux cas ; jusqu'à {g} génération(s) ; {b} cas isolé(s) sans lien dans l'outil.":
        "{a} chain(s) of at least two cases; up to {g} generation(s); {b} isolated case(s) with no link in the tool.",
    "Cas notifiés par jour": "Notified cases per day", "Cas notifiés par semaine": "Notified cases per week",
    "cas": "case(s)", "Jours": "Days", "jours": "days", "Lieux": "Places", "lieux": "places",
    "Délai médian début des symptômes → notification par zone de santé":
        "Median delay symptom onset → notification by health zone",
    "0 = délai non calculable (dates manquantes)": "0 = delay cannot be calculated (missing dates)",
    "Types de lieux fréquentés": "Types of places visited",
    "Délai médian de notification de {med} : au-delà de 3 jours, le cas a eu le temps d'exposer de nombreux contacts.":
        "Median notification delay of {med}: beyond 3 days, the case has had time to expose many contacts.",
    "{n} cas sans lien épidémiologique : chaînes invisibles à investiguer.":
        "{n} case(s) without an epidemiological link: hidden chains to investigate.",
    "{n} fiche(s) encore en brouillon : investigations non finalisées.": "{n} record(s) still in draft: investigations not finalised.",
    "Mesurer l'exhaustivité du listage, la part suivie et la protection des contacts par la vaccination.":
        "Measure how complete the listing is, the share followed up and the protection of contacts by vaccination.",
    "Contacts listés": "Contacts listed", "Médiane par cas": "Median per case", "Contacts suivis": "Contacts followed up",
    "Contacts vaccinés": "Contacts vaccinated",
    "Combien de contacts ont été identifiés par cas ?": "How many contacts were identified per case?",
    "Médiane {med} contact(s) par cas ; {n} contacts listés au total.": "Median {med} contact(s) per case; {n} contacts listed in total.",
    "Combien de contacts sont classés à haut risque ?": "How many contacts are classified as high risk?",
    "{n} contacts dans des groupes à risque haut ou très haut.": "{n} contacts in high or very high risk groups.",
    "Combien de groupes de contacts n'ont pas encore de classification de risque ?":
        "How many contact groups do not have a risk classification yet?",
    "{n} groupe(s).": "{n} group(s).",
    "Combien de catégories de contacts restent non dénombrées ?": "How many contact categories remain uncounted?",
    "{n} groupe(s) au nombre inconnu (« ? »).": "{n} group(s) with an unknown number (\"?\").",
    "Où les contacts ont-ils été identifiés (ménages, soins, transports, lieux communautaires) ?":
        "Where were the contacts identified (households, care, transport, community places)?",
    "Aucun contact dénombré.": "No contact counted.",
    "Quel pourcentage des contacts listés est suivi ?": "What percentage of listed contacts is followed up?",
    "{p} (groupes où le nombre listé et le nombre suivi sont renseignés).":
        "{p} (groups where both the listed and the followed-up numbers are entered).",
    "Quel est le taux de vaccination parmi les contacts listés ?": "What is the vaccination rate among listed contacts?",
    "{p} (colonne « Vaccinés »).": "{p} (\"Vaccinated\" column).",
    "Quel est le délai entre la confirmation et le début de la vaccination de l'anneau ?":
        "What is the delay between confirmation and the start of ring vaccination?",
    "Médiane {med} ; {p} des cas ont un anneau daté.": "Median {med}; {p} of cases have a dated ring.",
    "Combien de cas étaient vaccinés ?": "How many cases were vaccinated?",
    "{p} parmi les cas au statut renseigné.": "{p} among cases with a known status.",
    "Contacts listés par catégorie": "Listed contacts by category", "Contacts": "Contacts", "contacts": "contacts",
    "Contacts suivis et vaccinés par zone de santé (%)": "Contacts followed up and vaccinated by health zone (%)",
    "Moins de 90 % des contacts listés sont suivis : risque de cas secondaires non détectés.":
        "Less than 90% of listed contacts are followed up: risk of undetected secondary cases.",
    "{n} groupe(s) de contacts non dénombré(s) : listage incomplet.": "{n} uncounted contact group(s): incomplete listing.",
    "Vérifier que chaque site à risque est évalué, décontaminé et documenté, et que les enterrements sont sécurisés.":
        "Check that each risk site is assessed, decontaminated and documented, and that burials are safe.",
    "Sites PCI documentés": "Documented IPC sites", "Décontaminés": "Decontaminated",
    "Délai médian confirmation → décontamination": "Median delay confirmation → decontamination",
    "Enterrements sécurisés": "Safe burials",
    "Combien de lieux ont été identifiés, et combien de sites ont une évaluation PCI ?":
        "How many places were identified, and how many sites have an IPC assessment?",
    "{a} lieux d'exposition ; {b} sites PCI documentés.": "{a} exposure places; {b} documented IPC sites.",
    "Combien de décontaminations ont été réalisées ?": "How many decontaminations were carried out?",
    "{a} sites décontaminés ; {b} partiels ; {c} non faits.": "{a} sites decontaminated; {b} partial; {c} not done.",
    "Quel est le taux de réalisation des décontaminations ?": "What is the decontamination completion rate?",
    "Combien de lieux ont un statut PCI inconnu ?": "How many places have an unknown IPC status?",
    "{n} site(s).": "{n} site(s).",
    "Quel est le délai médian entre la confirmation et l'intervention PCI ?":
        "What is the median delay between confirmation and IPC intervention?",
    "{med} ({n} décontaminations datées) ; dans les 24 h : {p}.": "{med} ({n} dated decontaminations); within 24 h: {p}.",
    "Combien d'interventions disposent d'une date, d'une équipe et d'un produit documentés ?":
        "How many interventions have a documented date, team and product?",
    "Quels sites présentent encore un risque non maîtrisé ?": "Which sites still present an uncontrolled risk?",
    "Aucun site en attente.": "No site pending.",
    "Les enterrements des cas décédés ont-ils été dignes et sécurisés ?": "Were the burials of deceased cases safe and dignified?",
    "{p} parmi les décès avec une étape « Enterrement ».": "{p} among deaths with a \"Burial\" step.",
    "État des sites PCI": "Status of IPC sites", "Sites": "Sites", "sites": "sites",
    "Sites PCI par zone de santé et par état": "IPC sites by health zone and status",
    "{n} site(s) non décontaminé(s), partiel(s) ou inconnu(s) : à traiter en priorité.":
        "{n} site(s) not decontaminated, partial or unknown: to handle as a priority.",
    "Des enterrements n'ont pas été sécurisés : risque élevé de transmission aux funérailles.":
        "Some burials were not safe: high risk of transmission at funerals.",
    "Mesurer les délais diagnostiques, l'isolement et le parcours de soins avant la prise en charge.":
        "Measure diagnostic delays, isolation and the care pathway before case management.",
    "Cas prélevés": "Cases sampled", "Délai médian prélèvement → résultat": "Median delay sample → result",
    "Délai médian début → isolement": "Median delay onset → isolation", "Décès communautaires": "Community deaths",
    "Combien de cas ont été prélevés ?": "How many cases were sampled?",
    "Quel est le délai entre le prélèvement et le résultat ?": "What is the delay between sampling and result?",
    "Médiane {med} ; en {seuil} h ou moins : {p}.": "Median {med}; in {seuil} h or less: {p}.",
    "Quel est le délai entre le début des symptômes et l'isolement ?": "What is the delay between symptom onset and isolation?",
    "Médiane {med} ; isolés en 3 jours ou moins : {p}.": "Median {med}; isolated within 3 days or less: {p}.",
    "Combien de cas ont été isolés avant ou après la confirmation ?": "How many cases were isolated before or after confirmation?",
    "{a} avant, {b} après la confirmation.": "{a} before, {b} after confirmation.",
    "Quel est le nombre médian de consultations avant l'isolement ?": "What is the median number of consultations before isolation?",
    "{med} ; {n} cas ont consulté au moins deux fois avant d'être isolés.":
        "{med}; {n} case(s) consulted at least twice before being isolated.",
    "Combien de décès sont survenus dans la communauté, sans hospitalisation ?":
        "How many deaths occurred in the community, without hospitalisation?",
    "25 à 48 h": "25 to 48 h", "49 à 72 h": "49 to 72 h", "≤ 1 j": "≤ 1 d", "2 à 3 j": "2 to 3 d", "4 à 7 j": "4 to 7 d",
    "> 7 j": "> 7 d", "Délai prélèvement → résultat": "Delay sample → result",
    "Délai début des symptômes → isolement": "Delay symptom onset → isolation",
    "Délai médian de résultat de {med} : au-delà de {seuil} h.": "Median result delay of {med}: beyond {seuil} h.",
    "{n} décès communautaire(s) : cas détectés trop tard.": "{n} community death(s): cases detected too late.",
    "{n} cas ont consulté plusieurs structures avant l'isolement : exposition des soignants.":
        "{n} case(s) consulted several facilities before isolation: exposure of health workers.",
    "Suivre ce qui a été prescrit à partir des mappings : responsable, échéance, réalisation et retards, par pilier.":
        "Track what was prescribed from the mappings: responsible, due date, completion and delays, by pillar.",
    "Actions prescrites": "Prescribed actions", "Réalisées": "Done", "En retard": "Overdue", "Urgentes ouvertes": "Open urgent",
    "Combien d'actions ont été générées, et combien en moyenne par cas ?":
        "How many actions were generated, and how many on average per case?",
    "{n} actions ; {m} par cas.": "{n} actions; {m} per case.", "Aucun cas.": "No cases.",
    "Combien d'actions concernent chaque pilier ?": "How many actions concern each pillar?",
    "Combien d'actions ont un responsable identifié ?": "How many actions have an identified responsible person?",
    "Combien ont une échéance définie ?": "How many have a set due date?",
    "Combien sont en attente, en cours ou réalisées ?": "How many are pending, in progress or done?",
    "{a} à faire, {b} en cours, {c} faites.": "{a} to do, {b} in progress, {c} done.",
    "Combien sont en retard ?": "How many are overdue?",
    "{n} action(s) non faites dont l'échéance est dépassée.": "{n} action(s) not done and past their due date.",
    "Combien d'actions critiques (urgentes) sont ouvertes, et combien sans responsable ?":
        "How many critical (urgent) actions are open, and how many have no responsible person?",
    "{a} ouvertes, dont {b} sans responsable.": "{a} open, of which {b} without a responsible person.",
    "Combien de cas présentent au moins une action critique non résolue ?":
        "How many cases have at least one unresolved critical action?",
    "Combien d'actions réalisées ont été vérifiées par un superviseur ?": "How many completed actions were checked by a supervisor?",
    "Combien d'actions sont déclarées réalisées sans preuve ?": "How many actions are reported as done without proof?",
    "{a} sur {b} réalisées.": "{a} of {b} done.",
    "Quels obstacles bloquent ou retardent les actions (sécurité, communauté, intrants…) ?":
        "Which obstacles block or delay the actions (security, community, supplies…)?",
    "Aucun obstacle signalé.": "No obstacle reported.",
    "Actions par pilier et par statut": "Actions by pillar and status", "actions": "actions",
    "Actions en retard (les plus anciennes)": "Overdue actions (oldest first)", "Action": "Action",
    "Responsable": "Responsible", "Échéance": "Due date",
    "{n} action(s) en retard à relancer en réunion de coordination.": "{n} overdue action(s) to follow up at the coordination meeting.",
    "{n} action(s) urgente(s) sans responsable.": "{n} urgent action(s) without a responsible person.",
    "S'assurer que les mappings sont assez complets et cohérents pour orienter les opérations.":
        "Make sure the mappings are complete and consistent enough to guide operations.",
    "Complétude moyenne": "Average completeness", "Fiches complètes à 90 % ou plus": "Records 90% complete or more",
    "Fiches avec incohérence": "Records with an inconsistency", "Lieux géolocalisés": "Geolocated places",
    "Quel est le taux moyen de complétude des mappings ?": "What is the average completeness of the mappings?",
    "Combien de mappings ont une complétude supérieure ou égale à 90 % ?": "How many mappings are 90% complete or more?",
    "Quelles variables sont le plus souvent manquantes ?": "Which variables are most often missing?", "Aucune.": "None.",
    "Combien de fiches présentent des dates incohérentes ?": "How many records have inconsistent dates?",
    "{n} fiche(s) avec au moins une incohérence bloquante.": "{n} record(s) with at least one blocking inconsistency.",
    "Quelle proportion des lieux est géolocalisée ?": "What proportion of places is geolocated?",
    "Combien de cas disposent de plusieurs mappings potentiellement dupliqués ?":
        "How many cases have several possibly duplicated mappings?",
    "{n} paire(s) de doublons possibles.": "{n} possible duplicate pair(s).",
    "Combien de mappings sont restés en brouillon ?": "How many mappings remained in draft?",
    "Éléments le plus souvent manquants": "Most often missing items", "Fiches": "Records", "fiches": "records",
    "Complétude moyenne par zone de santé (%)": "Average completeness by health zone (%)", "Complétude": "Completeness",
    "Complétude moyenne sous 80 % : renforcer la supervision des fiches.":
        "Average completeness below 80%: strengthen supervision of the records.",
    "{n} fiche(s) avec des dates incohérentes à corriger.": "{n} record(s) with inconsistent dates to correct.",
    " en {province}": " in {province}",
    "{n} cas notifiés du {debut} au {fin}{lieu} ({total} cas au total dans le périmètre).":
        "{n} case(s) notified from {debut} to {fin}{lieu} ({total} cases in total in the scope).",
    # questions non couvertes (annexe)
    "A. Couverture": "A. Coverage", "C. Délais": "C. Delays", "D. Mobilité": "D. Mobility",
    "E et F. Contacts": "E and F. Contacts", "G. PCI": "G. IPC", "H. Investigation": "H. Investigation",
    "J. Communauté": "J. Community", "K. Vaccination": "K. Vaccination", "L. Coordination": "L. Coordination",
    "S. Impact": "S. Impact",
    "Combien de mappings ont été validés, rejetés ou soumis à investigation complémentaire ?":
        "How many mappings were validated, rejected or sent for further investigation?",
    "Circuit de validation par un superviseur": "Validation workflow by a supervisor",
    "Combien de cas confirmés de la liste linéaire n'ont pas de mapping ?": "How many confirmed cases in the line list have no mapping?",
    "Rapprochement avec la liste linéaire": "Matching with the line list",
    "Délais alerte → validation → investigation": "Delays alert → validation → investigation",
    "Dates d'alerte et de validation de l'alerte": "Alert and alert validation dates",
    "Corridors de mobilité entre zones et provinces": "Mobility corridors between zones and provinces",
    "Zone de santé de chaque lieu visité": "Health zone of each place visited",
    "Suivi quotidien sur 21 jours, contacts perdus de vue, J7 / J14 / J21":
        "Daily follow-up over 21 days, contacts lost to follow-up, D7 / D14 / D21",
    "Registre nominatif de suivi (Go.Data)": "Named follow-up register (Go.Data)",
    "Vérification des décontaminations par un superviseur, preuves, réévaluations":
        "Supervisor checks of decontaminations, proof, reassessments",
    "Validation et pièces justificatives": "Validation and supporting documents",
    "Investigations complémentaires recommandées, démarrées, achevées": "Further investigations recommended, started, completed",
    "Registre des investigations": "Investigation register",
    "Résistances communautaires, motifs, résolution": "Community resistance, reasons, resolution",
    "Registre des incidents communautaires": "Community incident register",
    "Éligibilité, refus, indisponibilité du vaccin": "Eligibility, refusal, vaccine unavailability",
    "Données nominatives de vaccination": "Named vaccination data",
    "Notifications interzones émises, reçues, traitées": "Inter-zone notifications sent, received, handled",
    "Registre des notifications interzones": "Inter-zone notification register",
    "Coût par investigation, par action PCI, par contact suivi": "Cost per investigation, per IPC action, per contact followed up",
    "Données de coût": "Cost data",
}

EN = {**_LISTES, **_TABLEAU_RIPOSTE, **_RAPPORTS}
