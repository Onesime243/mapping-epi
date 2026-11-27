"""Mapping Épi 2.0, lots 2 à 5 : parcours clinique, besoins du cas, trajets, command center, centre des actions,
goulots, concordance DHIS2, vaccination, psychosocial, services essentiels, PoE / PoC, PCI enrichi.
(Les en-têtes des modèles Word / Excel restent en français : ils servent à la réimportation.)"""

EN = {
    # fiche : parcours de prise en charge, besoins, trajets, PCI, vaccination
    "Parcours de prise en charge": "Care pathway",
    "Rempli par la prise en charge. L'admission au CTE se saisit à l'étape 3 (dates clés). Deux PCR négatives ne changent pas l'état du cas : la sortie est validée par l'équipe.":
        "Filled in by case management. ETC admission is entered in step 3 (key dates). Two negative PCRs do not change the case status: discharge is validated by the team.",
    "Date de la 1re consultation": "Date of first consultation", "Date de la référence": "Referral date",
    "Date de la décision de transfert": "Date of transfer decision", "Début du traitement spécifique": "Start of specific treatment",
    "Date de sortie du CTE": "ETC discharge date", "Rendez-vous post-guérison": "Post-recovery appointment",
    "9. Besoins": "9. Needs", "statut": "status", "statuts": "statuses",
    "Statuts seulement : le détail reste chez chaque pilier. Laisser « Non renseigné » si on ne sait pas.":
        "Statuses only: details stay with each pillar. Leave “Not documented” if unknown.",
    "Services de santé essentiels": "Essential health services", "Psychosocial": "Psychosocial",
    "Statut seulement : jamais de notes d'entretien ni de détail personnel dans la fiche.":
        "Status only: never interview notes or personal details in the record.",
    "Vaccination des contacts": "Contact vaccination",
    "Contacts éligibles, vaccinés et motif de non-vaccination : colonnes de l'étape 5 Contacts. Début de l'anneau : étape 1 Identité.":
        "Eligible and vaccinated contacts and reason for non-vaccination: columns of step 5 Contacts. Ring start: step 1 Identity.",
    "Éligibles": "Eligible", "Vaccinés": "Vaccinated", "Motifs : ": "Reasons: ", "Début de l'anneau : ": "Ring start: ",
    "Suivi obstétrical": "Obstetric follow-up", "Suivi du nouveau-né": "Newborn follow-up", "Suivi post-partum": "Postpartum follow-up",
    "Soutien nutritionnel": "Nutritional support", "Continuité des soins après la sortie": "Continuity of care after discharge",
    "Besoin psychosocial du cas": "Psychosocial need of the case", "Soutien à la famille": "Family support",
    "Documenté": "Documented", "À vérifier": "To check", "À planifier": "To plan", "Sans objet": "Not applicable",
    "Non évalué": "Not assessed", "Évaluation en cours": "Assessment in progress", "Besoin identifié": "Need identified",
    "Soutien en cours": "Support in progress", "Satisfait": "Met", "Référé": "Referred",
    "Refus": "Refusal", "Non joignable": "Unreachable", "Grossesse": "Pregnancy", "Contre-indication": "Contraindication",
    "Rupture de vaccins": "Vaccine stock-out",
    "Trajets (fois)": "Trips (times)", "déplacement répété : nombre d'allers ; une seule flèche épaisse sur la carte":
        "repeated trip: number of journeys; a single thick arrow on the map",
    "PoE / PoC franchi": "PoE / PoC crossed", "point d'entrée ou de contrôle franchi ; vide = aucun ou inconnu":
        "point of entry or control crossed; empty = none or unknown",
    "Identifié le": "Identified on", "date où le site a été identifié comme à décontaminer": "date the site was identified for decontamination",
    "Décontaminé le": "Decontaminated on", "Vérifié le": "Checked on", "vérification après la décontamination": "check after decontamination",
    "Preuve": "Evidence", "photo, fiche, rapport": "photo, form, report",
    "Éligibles au vaccin": "Eligible for vaccine", "contacts éligibles à la vaccination ; ? = inconnu": "contacts eligible for vaccination; ? = unknown",
    "Motif de non-vaccination": "Reason for non-vaccination", " (×{n})": " (×{n})",
    # aperçu parcours clinique
    "Parcours clinique": "Clinical pathway", "PARCOURS CLINIQUE – {cas} {maladie} | ZS {zs}": "CLINICAL PATHWAY – {cas} {maladie} | HZ {zs}",
    "État du cas : {etat} · bleu = documenté, vert/bleu foncé = pris en charge, gris = non documenté (ND)":
        "Case status: {etat} · blue = documented, green/dark blue = under care, grey = not documented (ND)",
    "Du premier symptôme au suivi du survivant": "From first symptom to survivor follow-up",
    "1re consultation": "First consultation", "Décision de transfert": "Transfer decision", "Admission CTE": "ETC admission",
    "Traitement": "Treatment", "PCR négatives": "Negative PCRs", "Sortie": "Discharge", "Suivi du survivant": "Survivor follow-up",
    "ND = non documenté : à compléter à l'étape 2 Clinique (parcours de prise en charge) ou à l'étape 3 (dates clés).":
        "ND = not documented: complete in step 2 Clinical (care pathway) or step 3 (key dates).",
    "Délais cliniques": "Clinical delays", "Symptômes → 1re consultation": "Symptoms → first consultation",
    "Décision de transfert → admission CTE": "Transfer decision → ETC admission", "Admission → début du traitement": "Admission → start of treatment",
    "Durée de séjour au CTE": "Length of ETC stay", "Rouge = au-delà du seuil (consultation 2 j, autres 1 j).":
        "Red = beyond the threshold (consultation 2 d, others 1 d).",
    "Laboratoire successif": "Successive laboratory results", "Aucun prélèvement saisi.": "No sample entered.",
    "Deux PCR négatives ne changent pas l'état du cas : sortie validée par l'équipe.":
        "Two negative PCRs do not change the case status: discharge validated by the team.",
    "Besoins du cas": "Needs of the case", "Statuts seulement : le détail reste chez chaque pilier.": "Statuses only: details stay with each pillar.",
    # tableau de bord : command center, centre des actions
    "Command center : où sont les problèmes ?": "Command centre: where are the problems?",
    "Rouge < 60 % · ambre 60 à 84 % · vert ≥ 85 % · ND = non documenté": "Red < 60% · amber 60 to 84% · green ≥ 85% · ND = not documented",
    "Performance par zone de santé et par pilier": "Performance by health zone and pillar", "Cliquez sur une zone pour voir ses cas.": "Click a zone to see its cases.",
    "Cas (fiches)": "Cases (records)", "dans la période et le périmètre": "in the period and scope", "Complétude des fiches": "Record completeness",
    "cible ≥ 95 %": "target ≥ 95%", "suivis : {p}": "followed up: {p}", "Concordance DHIS2": "DHIS2 agreement", "écart : {n}": "gap: {n}",
    "nombre DHIS2 non saisi": "DHIS2 number not entered", "tous piliers": "all pillars", "Actions dans les délais": "Actions on time",
    "{n} en retard": "{n} overdue", "Fiches complètes": "Complete records", "PCI : sites décontaminés": "IPC: decontaminated sites",
    "Isolement ≤ 1 j après confirmation": "Isolation ≤ 1 d after confirmation", "Actions à jour": "Actions up to date",
    "Écarts de listing des contacts (fiche − DHIS2)": "Contact listing gaps (record − DHIS2)",
    "seulement les fiches où le nombre DHIS2 est saisi": "only records where the DHIS2 number is entered", "État des cas": "Case status",
    "Centre des actions": "Action centre", "Faite · à valider": "Done · to validate", "Validée": "Validated", "En retard": "Overdue",
    "Une action déclarée faite n'est close qu'après validation (champ « Vérifiée par » de la fiche).":
        "An action reported as done is closed only after validation (“Checked by” field of the record).",
    "Tous": "All", "éch.": "due", "Preuve :": "Evidence:", "non renseignée": "not documented", "validateur ?": "validator?",
    "… et {n} autre(s)": "… and {n} more",
    # pages communes
    "Rien à afficher.": "Nothing to display.",
    # goulots
    "Goulots de la surveillance": "Surveillance bottlenecks", "Goulots d'étranglement de la surveillance": "Surveillance bottlenecks",
    "Où la chaîne alerte → investigation → prélèvement → confirmation → isolement se casse":
        "Where the alert → investigation → sampling → confirmation → isolation chain breaks",
    "Calculé à partir des dates déjà saisies dans les fiches (étapes 1 à 3 et Laboratoire).":
        "Calculated from the dates already entered in the records (steps 1 to 3 and Laboratory).",
    "Chaque retard peut devenir une action dans la fiche (étape 8), suivie dans le tableau de bord, onglet À traiter.":
        "Each delay can become an action in the record (step 8), followed up in the dashboard, To-do tab.",
    "Fiches analysées": "Records analysed", "Investigations tardives": "Late investigations", "alerte → investigation > 1 j": "alert → investigation > 1 d",
    "Isolements tardifs": "Late isolations", "confirmation → isolement > 1 j": "confirmation → isolation > 1 d",
    "Résultats manquants": "Missing results", "prélèvement sans résultat daté": "sample without dated result",
    "Chaîne de surveillance": "Surveillance chain", "nombre de fiches où chaque étape est datée": "number of records where each step is dated",
    "Alerte datée": "Dated alert", "Investigation datée": "Dated investigation", "Prélèvement daté": "Dated sampling",
    "Résultat daté": "Dated result", "Confirmation datée": "Dated confirmation", "Isolement effectif daté": "Dated actual isolation",
    "Délais par étape": "Delays by step", "Étape": "Step", "Médiane": "Median", "Fiches": "Records", "Seuil": "Threshold",
    "Hors délai": "Late", "{s} j": "{s} d",
    "calculés depuis les dates saisies dans les fiches ; ND = aucune fiche avec les deux dates":
        "calculated from the dates entered in the records; ND = no record with both dates",
    "Symptômes → alerte": "Symptoms → alert", "Alerte → investigation": "Alert → investigation",
    "Investigation → prélèvement": "Investigation → sampling", "Prélèvement → résultat": "Sampling → result",
    "Symptômes → confirmation": "Symptoms → confirmation", "Confirmation → début de l'anneau": "Confirmation → ring start",
    "Causes de retard documentées (actions)": "Documented causes of delay (actions)", "Fiches hors délai": "Late records",
    "40 premières ; ouvrez la fiche pour documenter la cause ou créer une action": "first 40; open the record to document the cause or create an action",
    # concordance
    "Concordance Mapping Épi × DHIS2": "Mapping Épi × DHIS2 agreement",
    "Réconciliation des contacts par cas index (nombres seulement)": "Contact reconciliation by index case (numbers only)",
    "Le nombre DHIS2 est saisi à la main dans la fiche (étape 5 Contacts) en attendant la connexion automatique à DHIS2.":
        "The DHIS2 number is entered by hand in the record (step 5 Contacts) until the automatic DHIS2 connection.",
    "Même nombre ne veut pas dire mêmes personnes : un écart est un signal à investiguer, pas une preuve.":
        "The same number does not mean the same people: a gap is a signal to investigate, not proof.",
    "Fiches comparables": "Comparable records", "nombre DHIS2 saisi": "DHIS2 number entered", "Contacts dans les fiches": "Contacts in the records",
    "Contacts dans DHIS2": "Contacts in DHIS2", "Concordance": "Agreement", "Statut des fiches": "Record status",
    "Comparaison impossible": "Comparison not possible", "Concordance numérique": "Numerical agreement",
    "Sous-listing potentiel": "Potential under-listing", "Contacts supplémentaires dans DHIS2": "Additional contacts in DHIS2",
    "Complétude DHIS2 par zone de santé": "DHIS2 completeness by health zone", "contacts DHIS2 / contacts de la fiche": "DHIS2 contacts / record contacts",
    "Détail par cas index": "Detail by index case", "Fiche": "Record", "DHIS2 listés": "DHIS2 listed", "DHIS2 suivis": "DHIS2 followed up", "Écart": "Gap",
    # vaccination
    "Vaccination et protection des contacts": "Vaccination and protection of contacts",
    "Contacts éligibles autour des cas et vaccination en anneau": "Eligible contacts around cases and ring vaccination",
    "Saisie dans la fiche : étape 5 Contacts (éligibles, vaccinés, motif) et étape 1 Identité (début de l'anneau).":
        "Entered in the record: step 5 Contacts (eligible, vaccinated, reason) and step 1 Identity (ring start).",
    "Couverture = vaccinés / éligibles (ou / listés si les éligibles ne sont pas saisis).":
        "Coverage = vaccinated / eligible (or / listed if eligible contacts are not entered).",
    "Confirmation → anneau": "Confirmation → ring", "médiane": "median", "Anneaux ouverts (7 j)": "Rings opened (7 d)",
    "Cas sans début d'anneau": "Cases without ring start", "Cascade vaccinale": "Vaccination cascade",
    "Motifs de non-vaccination": "Reasons for non-vaccination", "{n} groupe(s)": "{n} group(s)", "Aucun motif saisi": "No reason entered",
    "Par zone de santé": "By health zone", "Cas": "Cases", "Couverture": "Coverage",
    "Cas sans début de vaccination de l'anneau": "Cases without start of ring vaccination",
    # psychosocial
    "Psychosocial (agrégats)": "Psychosocial (aggregates)", "Prise en charge psychosociale": "Psychosocial care",
    "Agrégats et statuts seulement · aucune liste nominative": "Aggregates and statuses only · no named list",
    "Les fiches ne contiennent que le statut du besoin (étape 9 Besoins) ; les notes d'entretien restent dans l'outil du pilier.":
        "Records contain only the status of the need (step 9 Needs); interview notes stay in the pillar's tool.",
    "Aucune liste de cas n'est affichée ici : seulement des nombres par statut et par zone.":
        "No case list is shown here: only numbers by status and zone.",
    "Cas évalués": "Cases assessed", "Soutien reçu": "Support received", "En attente": "Pending", "fiches sans statut": "records without status",
    "Aucun statut saisi": "No status entered", "Évalués": "Assessed",
    # services essentiels
    "Continuité des services de santé essentiels": "Continuity of essential health services",
    "Besoins des patients (statuts de l'étape 9 Besoins)": "Patient needs (statuses from step 9 Needs)",
    "Côté patient : statuts saisis dans la fiche (étape 9 Besoins).": "Patient side: statuses entered in the record (step 9 Needs).",
    "Côté structures (consultations, CPN, accouchements, vaccination de routine) : à brancher plus tard sur le SNIS (DHIS2) ; rien n'est saisi dans Mapping Épi.":
        "Facility side (consultations, ANC, deliveries, routine immunisation): to be connected later to the HMIS (DHIS2); nothing is entered in Mapping Épi.",
    "Cas avec un besoin en attente": "Cases with a pending need", "à vérifier ou à planifier": "to check or to plan",
    "Besoins documentés": "Documented needs", "Fiches sans aucun statut": "Records without any status", "Statuts par besoin": "Statuses by need",
    "Besoin": "Need", "Besoins à vérifier ou à planifier": "Needs to check or to plan",
    # PoE / PoC
    "PoE / PoC et mobilité": "PoE / PoC and mobility",
    "Couverture du screening aux points d'entrée et de contrôle · 7 derniers jours": "Screening coverage at points of entry and control · last 7 days",
    "Rapports journaliers saisis par point (formulaire ci-dessous) ; les passages des cas viennent de la chronologie des fiches (colonne « PoE / PoC franchi »).":
        "Daily reports entered by point (form below); case crossings come from the record timelines (“PoE / PoC crossed” column).",
    "Couverture = voyageurs screenés / voyageurs enregistrés ; objectif 95 %.": "Coverage = screened travellers / registered travellers; target 95%.",
    "Voyageurs enregistrés": "Registered travellers", "7 derniers jours": "last 7 days", "Screenés": "Screened", "objectif 95 %": "target 95%",
    "Alertes détectées": "Alerts detected", "{n} investiguées": "{n} investigated", "Passages de cas documentés": "Documented case crossings",
    "chronologie des fiches": "record timelines", "Couverture par point (7 jours)": "Coverage by point (7 days)",
    "Aucun rapport sur 7 jours": "No report in 7 days", "Passages des cas aux PoE / PoC": "Case crossings at PoE / PoC",
    "Trajet": "Trip", "PoE / PoC": "PoE / PoC", "Rapports journaliers": "Daily reports", "Point": "Point", "Voyageurs": "Travellers",
    "Alertes": "Alerts", "Investiguées": "Investigated", "Ajouter un rapport journalier": "Add a daily report",
    "Nombres seulement, jamais de nom de voyageur. Vide = inconnu (jamais 0).": "Numbers only, never a traveller's name. Empty = unknown (never 0).",
    "Point (PoE / PoC)": "Point (PoE / PoC)", "Supprimer un rapport saisi par erreur": "Delete a report entered by mistake",
    "Supprimer ce rapport ?": "Delete this report?", "Rapport journalier enregistré.": "Daily report saved.", "Rapport supprimé.": "Report deleted.",
    "Rapport non enregistré : {e}": "Report not saved: {e}", "point manquant": "missing point", "nombre négatif": "negative number",
    "plus de screenés que de voyageurs": "more screened than travellers", "plus d'alertes investiguées que d'alertes": "more investigated alerts than alerts",
    # PCI
    "sites PCI décontaminés": "IPC sites decontaminated", "vérifiés après décontamination": "checked after decontamination",
    "avec preuve (photo, fiche, rapport)": "with evidence (photo, form, report)", "délai médian identification → décontamination":
        "median delay identification → decontamination", "site(s)": "site(s)", "Identifié": "Identified", "Décontaminé": "Decontaminated",
    "Vérifié": "Checked",
}
