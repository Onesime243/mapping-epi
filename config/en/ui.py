"""Pages web, menus et messages (voir core/langue.py)."""

EN = {
    # barre du haut et menus
    "Cas": "Cases", "Analyses": "Analyses", "Riposte": "Response", "Données": "Data", "Utilisateurs": "Users",
    "Tutoriel": "Tutorial", "Mon compte": "My account", "Déconnexion": "Sign out", "Thème": "Theme", "Langue": "Language",
    "Menu": "Menu", "parcours thérapeutique": "care pathway",
    "Chaînes de transmission": "Transmission chains", "Catégories des ZS, délais et incubation":
        "Health zone categories, delays and incubation",
    "Lieux fréquentés par zone de santé": "Places visited by health zone",
    "Lieux fréquentés par aire de santé": "Places visited by health area",
    "Indicateurs clés et courbe épidémique": "Key indicators and epidemic curve", "Carte des cas": "Case map",
    "Suivi des actions": "Action tracking", "Mode réunion (diaporama)": "Meeting mode (slideshow)",
    "Liste des cas (Excel)": "Case list (Excel)", "Rapport de situation (Word)": "Situation report (Word)",
    "Échanger des fiches (paquet hors ligne)": "Exchange records (offline package)",
    "Doublons possibles": "Possible duplicates", "Mode clair / sombre": "Light / dark mode",
    "Changer de thème": "Change theme", "Logiciel libre sous licence GNU AGPL v3": "Free software under the GNU AGPL v3",
    "Pour tout contact :": "Contact:", "Équipe de développement : Onesime Mbulayi, John Kombe et al.":
        "Development team: Onesime Mbulayi, John Kombe et al.",
    "Système de gestion de l’incident, SGI-RDC, avec l’appui de UMIE-INRB":
        "Incident Management System, SGI-RDC, with support from UMIE-INRB",
    # niveaux et périmètres
    "National": "National", "Provincial": "Provincial", "Zone de santé": "Health zone", "Aire de santé": "Health area",
    "Toute la RDC": "All of DRC", "administrateur": "administrator", "admin": "admin",
    # connexion
    "Connexion": "Sign in", "Identifiant": "Username", "Mot de passe": "Password", "Se connecter": "Sign in",
    "Pas de compte ? Demandez-le à l'administrateur de l'outil.": "No account? Ask the tool administrator.",
    "Première fois ?": "First time?", "Suivre le tutoriel pas à pas": "Follow the step-by-step tutorial",
    # accueil
    "Accueil": "Home", "Bonjour": "Hello", "Bienvenue dans Mapping Épi.": "Welcome to Mapping Épi.",
    "Documentez ici le parcours thérapeutique de chaque cas confirmé. Renseignez l'ensemble des champs obligatoires, "
    "signalés par un astérisque (*), puis enregistrez la fiche : seules les fiches complètes et enregistrées sont "
    "prises en compte dans les analyses et partagées avec la coordination.":
        "Use this tool to document the care pathway of each confirmed case. Complete all mandatory fields, "
        "marked with an asterisk (*), then save the record: only complete, saved records are included in the analyses "
        "and shared with the coordination team.",
    "Bienvenue dans Mapping Épi": "Welcome to Mapping Épi",
    "Documentation du parcours thérapeutique des cas confirmés":
        "Documenting the care pathway of confirmed cases",
    "Pour chaque cas, renseignez l'ensemble des champs obligatoires, signalés par un astérisque (*), puis enregistrez "
    "la fiche.": "For each case, complete all mandatory fields, marked with an asterisk (*), then save the record.",
    "Seules les fiches complètes et enregistrées sont prises en compte dans les analyses et partagées avec la "
    "coordination.": "Only complete, saved records are included in the analyses and shared with the coordination team.",
    "Créer la fiche": "Create the record", "Compléter les champs *": "Complete the * fields", "Enregistrer": "Save",
    "Nouveau cas": "New case", "Voir mes cas": "View my cases", "Voir les cas": "View cases",
    "Exemple fictif": "Fictitious example", "pour s'entraîner": "for practice", "reprendre mon exemple": "resume my example",
    "enregistré": "saved", "enregistrés": "saved", "brouillon": "draft", "brouillons": "drafts",
    # liste des cas
    "Mes cas": "My cases", "Tous les cas": "All cases", "Cas de mon périmètre": "Cases in my area",
    "Enregistrés": "Saved", "Brouillons": "Drafts", "← Accueil": "← Home", "＋ Nouveau cas": "＋ New case",
    "Rechercher (ID, ZS, AS, maladie, agent…)": "Search (ID, HZ, HA, disease, user…)",
    "Rechercher (ID, ZS, AS, maladie…)": "Search (ID, HZ, HA, disease…)",
    "Tous les comptes": "All accounts", "Toutes les provinces": "All provinces", "Toutes les ZS": "All health zones",
    "Toutes les AS": "All health areas", "Filtrer": "Filter", "Effacer": "Clear", "Ouvrir": "Open",
    "Consulter": "View", "Mapping": "Mapping", "Voir le mapping": "View the mapping", "moi": "me",
    "ID / fiche": "ID / record", "Province": "Province", "ZS": "HZ", "AS": "HA", "J0": "D0",
    "Compte": "Account", "Créée le": "Created", "Modifiée le": "Modified", "Fiche": "Record",
    "Nouvelle fiche": "New record", "incomplet": "incomplete", "Aucun brouillon.": "No drafts.",
    "Fiches commencées mais pas encore enregistrées. Ouvrez-en une pour la terminer. Une fiche laissée vide est "
    "supprimée automatiquement après 24 heures.":
        "Records started but not saved yet. Open one to finish it. A record left empty is deleted automatically "
        "after 24 hours.",
    "Mode entraînement : cet exemple est visible par vous seul et n'est jamais compté avec les vrais cas (liste, "
    "analyses, carte, synchronisation).":
        "Practice mode: this example is visible to you only and is never counted with real cases (list, analyses, "
        "map, synchronisation).",
    "Cliquez sur un titre de colonne pour trier.": "Click a column title to sort.",
    "Importer une fiche": "Import a record", "Importer": "Import",
    "Réservé aux administrateurs": "Administrators only", "réservé aux administrateurs": "administrators only",
    "Exports réservés aux administrateurs": "Exports are for administrators only", "Rapports": "Reports",
    "Importer une fiche": "Import a record", "Importer une fiche (Word / Excel)": "Import a record (Word / Excel)",
    "⇪ Importer une fiche (Word / Excel)": "⇪ Import a record (Word / Excel)", "Word ou Excel déjà rempli": "Completed Word or Excel file",
    "Fichier de la fiche": "Record file", "Importer et ouvrir la fiche": "Import and open the record", "Annuler": "Cancel",
    "Modèle Excel": "Excel template", "Modèle Word": "Word template", "Modèle PowerPoint": "PowerPoint template",
    "Créez un cas à partir d'un fichier déjà rempli : les champs sont remplis automatiquement, puis la fiche s'ouvre pour vérification.":
        "Create a case from a completed file: fields are filled in automatically, then the record opens for checking.",
    "Formats acceptés : Excel (.xlsx), Word (.docx), PowerPoint (.pptx), ou ancien narratif Word / PowerPoint libre.":
        "Accepted formats: Excel (.xlsx), Word (.docx), PowerPoint (.pptx), or older free-text Word / PowerPoint narratives.",
    "Pas encore de fichier ? Téléchargez un modèle vierge :": "No file yet? Download a blank template:",
    "Si des champs obligatoires manquent, la fiche est gardée en brouillon jusqu'à ce qu'ils soient remplis.":
        "If required fields are missing, the record is kept as a draft until they are filled in.",
    "PCI": "IPC", "PCI : lieux fréquentés et adresses": "IPC: places visited and addresses",
    "Lieux fréquentés et adresses (Excel)": "Places visited and addresses (Excel)", "lieux fréquentés": "places visited",
    "avec adresse": "with address", "sans adresse (à compléter dans l'onglet PCI de la fiche)":
        "without address (to complete in the record's IPC tab)", "Lignes": "Rows", "à": "to", "sur": "of",
    "Le fichier Excel contient toutes les lignes et un résumé par cas.": "The Excel file contains every row and a summary per case.",
    "ID du cas": "Case ID", "Lieu fréquenté": "Place visited", "Origine": "Source", "Première date": "First date",
    "Adresse": "Address", "Statut PCI": "IPC status", "Parcours": "Pathway", "Lieu saisi": "Entered place",
    "Site PCI": "IPC site", "Pas de site PCI saisi": "No IPC site entered",
    "Aucun lieu saisi dans les fiches du périmètre.": "No place entered in the records of this scope.",
    "Tableau de bord": "Dashboard", "Précédent": "Previous", "Suivant": "Next", "Tableau de bord de la riposte": "Response dashboard",
    "Super-administrateur": "Super administrator", "Administrateur national": "National administrator",
    "Administrateur provincial": "Provincial administrator",
    "Sceau de la Présidence de la République démocratique du Congo":
        "Seal of the Presidency of the Democratic Republic of the Congo",
    "Task Force Présidentielle Ebola 17": "Presidential Ebola Task Force 17",
    "Système de Gestion de l’Incident MVE 17 : MAPPING EPI": "EVD 17 Incident Management System: MAPPING EPI",
    "Un autre utilisateur vient de se connecter avec votre compte sur un autre appareil. Vous avez été déconnecté. "
    "Si ce n'est pas vous, changez votre mot de passe.":
        "Another user has just signed in with your account on another device. You have been signed out. "
        "If this was not you, change your password.",
    "En tant qu'administrateur, vous voyez et corrigez les mappings de tous les comptes.":
        "As an administrator, you can view and edit the mappings of all accounts.",
    "Vous voyez et corrigez les cas de votre zone de santé, dont ceux de ses aires de santé.":
        "You can view and edit the cases of your health zone, including those of its health areas.",
    "Vous voyez les cas de toutes les provinces ; les fiches des autres comptes s'ouvrent en lecture seule.":
        "You can view cases from all provinces; records from other accounts open read-only.",
    "Vous voyez les cas de votre province ; les fiches des autres comptes s'ouvrent en lecture seule.":
        "You can view the cases of your province; records from other accounts open read-only.",
}

# --------------------------------------------------------------------------------------------------------------
# Pages web (gabarits web/templates/*.html hors fiche) et messages du serveur (web/server.py)
EN.update({
    # glossaire, libellés courts
    "Partenaire": "Partner", "partenaire": "partner", "agent": "agent", "Exemple": "Example", "bureau": "desktop",
    "Pages": "Pages", "Lieux communs": "Shared places", "Carte du parcours": "Pathway map",
    "Réseau": "Network", "Frise": "Timeline", "Afficher": "Show", "Du": "From", "Au": "To", "Période": "Period",
    "Niveau": "Level", "Nom": "Name", "Périmètre": "Scope", "Périmètre :": "Scope:", "province": "province",
    "cas": "case(s)", "Cas :": "Cases:", "Fiches": "Records", "Motif": "Reason", "Question": "Question",
    "Réponse": "Answer", "Seuil": "Threshold", "pilier": "pillar", "Piliers": "Pillars", "Contenu": "Contents",
    "par": "by", "Nouvelle": "New", "Lieux PCI": "IPC places", "Décontaminés": "Decontaminated",
    "Actions": "Actions", "Synthèse": "Summary", "Contacts, PCI et vaccination": "Contacts, IPC and vaccination",
    "Parcours et transmission": "Pathway and transmission", "Matrice des questions": "Question matrix",
    "7 derniers jours": "Last 7 days", "21 derniers jours": "Last 21 days", "42 derniers jours": "Last 42 days",
    "Mode réunion": "Meeting mode", "Installation": "Setup", "Classement": "Ranking",
    "Aires de santé": "Health areas", "Toutes les zones de santé": "All health zones",
    "Toutes les aires de santé": "All health areas", "Ouvrir la fiche": "Open the record",
    "Ouvrir en grand": "Open full size", "jamais": "never", "Lecture seule": "Read-only",
    # piliers des rapports (core/piliers.py)
    "Surveillance et investigation": "Surveillance and investigation", "Contacts et vaccination": "Contacts and vaccination",
    "Prévention et contrôle des infections (PCI)": "Infection prevention and control (IPC)",
    "Laboratoire et prise en charge": "Laboratory and case management", "Actions et coordination": "Actions and coordination",
    "Qualité des données": "Data quality",

    # messages du serveur
    "Session expirée : reconnectez-vous.": "Session expired: please sign in again.",
    "Jeton de sécurité invalide : rechargez la page.": "Invalid security token: reload the page.",
    "Aucun compte administrateur. Sur le serveur, lancez : sudo mapping-epi creer-admin":
        "No administrator account. On the server, run: sudo mapping-epi creer-admin",
    "Les deux mots de passe ne correspondent pas.": "The two passwords do not match.",
    "Compte administrateur créé. Connectez-vous.": "Administrator account created. Please sign in.",
    "Trop de tentatives. Réessayez dans quelques minutes.": "Too many attempts. Try again in a few minutes.",
    "Identifiant ou mot de passe incorrect.": "Incorrect username or password.",
    "Jeton invalide ou révoqué : créez-en un dans « Mon compte ».": "Invalid or revoked token: create one in “My account”.",
    "Jeton révoqué : l'ordinateur concerné ne peut plus se synchroniser.":
        "Token revoked: that computer can no longer synchronise.",
    "Mot de passe actuel incorrect.": "Current password is incorrect.",
    "Les deux nouveaux mots de passe ne correspondent pas.": "The two new passwords do not match.",
    "Mot de passe modifié.": "Password changed.",
    "Action réservée aux administrateurs.": "Action reserved for administrators.",
    "Compte « {u} » supprimé ({n} fiche(s) conservée(s)). La suppression est inscrite dans l'historique.":
        "Account “{u}” deleted ({n} record(s) kept). The deletion is recorded in the history.",
    "Niveau du compte « {u} » modifié.": "Level of account “{u}” changed.",
    "Vous ne pouvez pas désactiver votre propre compte.": "You cannot deactivate your own account.",
    "Un compte partenaire reste en consultation seule.": "A partner account stays view-only.",
    "AS {a} (ZS {z})": "HA {a} (HZ {z})", "ZS {z}": "HZ {z}",
    "LIEUX LES PLUS FRÉQUENTÉS | {place}": "MOST VISITED PLACES | {place}",
    "CAS RELIÉS PAR LES LIEUX FRÉQUENTÉS | {place}": "CASES LINKED BY VISITED PLACES | {place}",
    "Dates invalides : la période par défaut (4 dernières semaines) est affichée.":
        "Invalid dates: the default period (last 4 weeks) is shown.",
    "Cas pris en charge : ": "Case taken in charge: ", "Cas marqué résolu : ": "Case marked resolved: ",
    "Choisissez une date de début et une date de fin.": "Choose a start date and an end date.",
    "Cochez au moins un pilier.": "Tick at least one pillar.",
    "Choisissez un paquet de fiches (.zip).": "Choose a record package (.zip).",
    "Paquet importé : ": "Package imported: ",
    "Export impossible sur ce serveur : {msg}": "Export not possible on this server: {msg}",
    "Export impossible sur ce serveur : {msg}\n\nAstuce : utilisez « Imprimer → Enregistrer en PDF » depuis l'aperçu, "
    "ou les formats SVG / PowerPoint.":
        "Export not possible on this server: {msg}\n\nTip: use “Print → Save as PDF” from the preview, "
        "or the SVG / PowerPoint formats.",
    "Narratif importé : ": "Narrative imported: ", " À compléter : ": " To complete: ",
    " Vérifiez chaque onglet avant d'enregistrer le mapping.": " Check each tab before saving the mapping.",
    "Fichier illisible : {e}": "Unreadable file: {e}",
    "Fiche gardée en brouillon : complétez {champs} pour l'enregistrer.":
        "Record kept as a draft: complete {champs} to save it.",
    "application de bureau": "desktop application", "Brouillon supprimé.": "Draft deleted.",
    "Fiche supprimée (récupérable dans l'historique par un administrateur).":
        "Record deleted (an administrator can recover it from the history).",
    "Lecture seule : vous pouvez consulter cette fiche mais pas la modifier.":
        "Read-only: you can view this record but not edit it.",
    "Données invalides : {e}": "Invalid data: {e}",
    "Accès refusé : cette fiche n'est pas dans votre périmètre, ou vous pouvez seulement la consulter.":
        "Access denied: this record is not in your scope, or you can only view it.",
    "Page ou fiche introuvable.": "Page or record not found.",

    # erreur, installation, compte
    "Erreur": "Error", "Retour à mes cas": "Back to my cases", "Premier lancement": "First start",
    "Créez le compte": "Create the", ". Il pourra ensuite créer les comptes des agents de terrain.":
        " account. It can then create the accounts of field staff.",
    "Nom complet": "Full name", "ex. admin": "e.g. admin",
    "3 à 32 caractères : minuscules, chiffres, point, tiret.": "3 to 32 characters: lowercase letters, digits, dot, hyphen.",
    "8 caractères minimum, avec au moins une lettre et un chiffre.": "At least 8 characters, with at least one letter and one digit.",
    "Confirmer le mot de passe": "Confirm the password", "Créer le compte administrateur": "Create the administrator account",
    "identifiant": "username", "Mot de passe actuel": "Current password", "Nouveau mot de passe": "New password",
    "Confirmer": "Confirm", "Changer le mot de passe": "Change the password",
    "Synchroniser l'application de bureau": "Synchronise the desktop application",
    "L'application installée sur un ordinateur (Windows ou Mac) envoie ses fiches au serveur et reçoit celles de votre "
    "périmètre dès qu'elle a internet. Créez un jeton par ordinateur, puis dans l'application :":
        "The application installed on a computer (Windows or Mac) sends its records to the server and receives those "
        "of your scope as soon as it has internet. Create one token per computer, then in the application:",
    "Riposte ▾ → Synchronisation…": "Response ▾ → Synchronisation…", ", collez l'adresse": ", paste the address",
    "et le jeton.": "and the token.",
    "Jeton créé : copiez-le maintenant, il ne sera plus affiché.": "Token created: copy it now, it will not be shown again.",
    "Nom de l'ordinateur (ex. PC EPI Bunia)": "Computer name (e.g. PC EPI Bunia)", "Créer un jeton": "Create a token",
    "Ordinateur": "Computer", "Créé le": "Created", "Dernière synchronisation": "Last synchronisation",
    "Révoquer": "Revoke",

    # accueil, liste des cas
    "toutes les provinces": "all provinces",
    "Compte partenaire : consultation des fiches, des visuels (mapping, réseau de contacts, carte du parcours, multi-cas, "
    "chaînes de transmission) et téléchargement des images, PDF et PowerPoint.":
        "Partner account: viewing of records and visuals (mapping, contact network, pathway map, multi-case, "
        "transmission chains) and download of images, PDF and PowerPoint.",
    "Aucune fiche": "No record", "pour ces filtres": "for these filters",
    "Cliquez sur « Nouveau cas » pour commencer.": "Click “New case” to start.",
    "Excel rempli à partir du": "Excel completed from the", "modèle Excel vierge": "blank Excel template", ", du": ", the",
    "modèle Word": "Word template", "ou du": "or the", "modèle PowerPoint": "PowerPoint template",
    "(mêmes champs que l'Excel, lus tableau par tableau), ou ancien narratif Word / PowerPoint libre : les champs sont "
    "remplis automatiquement, à vérifier)":
        "(same fields as the Excel file, read table by table), or an older free-text Word / PowerPoint narrative: "
        "fields are filled in automatically, to be checked)",

    # suivi des actions
    "Suivi des actions de la riposte": "Response action tracking",
    "Actions inscrites dans les fiches de cas (onglet Actions) : qui fait quoi, pour quand. Les actions en retard "
    "apparaissent en premier. Pour modifier une action (responsable, échéance, statut), ouvrez la fiche du cas.":
        "Actions entered in the case records (Actions tab): who does what, by when. Overdue actions come first. "
        "To change an action (responsible person, due date, status), open the case record.",
    "afficher aussi les actions faites": "also show completed actions", "ouverte(s)": "open", "en retard": "overdue",
    "urgente(s)": "urgent", "sans responsable": "without a responsible person", "sans échéance": "without a due date",

    # carte des cas
    "notifiés dans les {n} derniers jours": "notified in the last {n} days",
    "Chaque cas est placé dans son aire de santé (contours réels": "Each case is placed in its health area (real boundaries",
    "ou au point GPS de la fiche. Fonctionne sans internet.": "or at the record's GPS point. Works without internet.",
    "Vue : autour des cas": "View: around the cases", "Vue : province entière": "View: whole province",
    "Recentrer": "Recentre", "cas sans position": "case(s) without a position",
    "Ni GPS dans la fiche, ni coordonnées connues pour leur aire ou leur zone de santé.":
        "No GPS in the record and no known coordinates for their health area or health zone.",
    "Contours des aires de santé": "Health area boundaries", "aires de santé avec contours": "health areas with boundaries",
    "Pour une autre province (Ituri, Haut-Uélé…), importez le fichier GeoPackage (.gpkg) des aires de santé GRID3 : "
    "colonnes Province, Zone, Aire. Il est simplifié et gardé sur le serveur.":
        "For another province (Ituri, Haut-Uélé…), import the GRID3 health area GeoPackage file (.gpkg): "
        "columns Province, Zone, Aire. It is simplified and kept on the server.",
    "Importer les contours (.gpkg)": "Import boundaries (.gpkg)",
    "Coordonnées des aires de santé (sans contours)": "Health area coordinates (without boundaries)",
    "aire(s) de santé avec coordonnées. Fichier CSV avec les colonnes": "health area(s) with coordinates. CSV file with the columns",
    "(par exemple les centres des aires de santé GRID3 / OCHA).": "(for example the GRID3 / OCHA health area centres).",
    "Les lignes hors de la RDC ou sans nombre valide sont ignorées.": "Rows outside the DRC or without a valid number are ignored.",
    "Importer les coordonnées": "Import coordinates",
    "Import réservé aux administrateurs et au niveau national.": "Import reserved for administrators and the national level.",

    # chaînes de transmission
    "Cas source → cas secondaires, à partir du champ « ID du cas source » de chaque fiche (comparé à l'ID des autres "
    "fiches).": "Source case → secondary cases, from the “Source case ID” field of each record (compared with the ID "
                "of the other records).",
    "Limité aux cas de votre périmètre ({p}).": "Limited to the cases in your scope ({p}).",
    "À droite : les « pistes », un cas contagieux et un cas exposé passés au même lieu sans lien saisi.":
        "On the right: the “leads”, an infectious case and an exposed case who were at the same place with no link entered.",

    # données
    "Données : listes, rapports et échange de fiches": "Data: lists, reports and record exchange",
    "{n} cas visibles.": "{n} visible case(s).",
    "Tous les fichiers ne contiennent que les fiches de votre périmètre.": "All files contain only the records in your scope.",
    "Liste des cas et rapport de situation": "Case list and situation report",
    "Indicateurs : 7 derniers jours": "Indicators: last 7 days", "Indicateurs : 21 derniers jours": "Indicators: last 21 days",
    "Indicateurs : 42 derniers jours": "Indicators: last 42 days", "Indicateurs : depuis le début": "Indicators: since the start",
    "Liste des cas : une ligne par cas (N° EPID, lieux, dates clés, état, isolement, contacts, complétude), sans nom de "
    "patient.": "Case list: one row per case (EPID no., places, key dates, condition, isolation, contacts, completeness), "
                "without patient names.",
    "Rapport : situation générale, courbe épidémique, catégories des ZS, indicateurs clés, alertes, actions et points "
    "d'attention. À relire avant diffusion.":
        "Report: general situation, epidemic curve, health zone categories, key indicators, alerts, actions and points "
        "of attention. To be proofread before circulation.",
    "Échanger des fiches entre ordinateurs (sans connexion)": "Exchange records between computers (offline)",
    "Pour rassembler les fiches saisies sur les ordinateurs où l'application est installée : exportez un paquet, "
    "transmettez-le (clé USB, e-mail, WhatsApp), puis importez-le ici ou dans l'application de bureau (menu Riposte ▾).":
        "To gather the records entered on computers where the application is installed: export a package, "
        "send it (USB key, e-mail, WhatsApp), then import it here or in the desktop application (Response ▾ menu).",
    "Seules les fiches de cas voyagent, jamais les comptes ni les mots de passe.":
        "Only case records travel, never accounts or passwords.",
    "Exporter un paquet de fiches (.zip)": "Export a record package (.zip)", "Importer un paquet": "Import a package",
    "À l'import : les nouvelles fiches sont ajoutées ; une fiche déjà présente n'est remplacée que par une version plus "
    "récente (l'ancienne reste dans l'historique) ; un N° EPID déjà utilisé par une autre fiche est signalé et rien "
    "n'est écrasé ; les fiches que votre compte n'a pas le droit de modifier sont ignorées.":
        "On import: new records are added; an existing record is only replaced by a more recent version (the old one "
        "stays in the history); an EPID no. already used by another record is reported and nothing is overwritten; "
        "records your account is not allowed to edit are ignored.",
    "Bilan :": "Summary:", "Ajoutées :": "Added:", "Mises à jour :": "Updated:", "Illisibles :": "Unreadable:",

    # doublons
    "Même N° EPID (certitude forte), ou même zone de santé, sexe, âge (± 1 an) et début des symptômes (± 2 jours) : "
    "à vérifier. Rien n'est supprimé ni fusionné automatiquement : ouvrez les deux fiches, gardez la plus complète et "
    "supprimez l'autre (elle reste récupérable dans l'historique).":
        "Same EPID no. (high certainty), or same health zone, sex, age (± 1 year) and symptom onset (± 2 days): "
        "to be checked. Nothing is deleted or merged automatically: open both records, keep the more complete one and "
        "delete the other (it can still be recovered from the history).",
    "Certitude": "Certainty", "Fiche 1": "Record 1", "Fiche 2": "Record 2", "Raison": "Reason",
    "forte": "high", "à vérifier": "to check",
    "Aucun doublon possible dans votre périmètre.": "No possible duplicate in your scope.",

    # lieux fréquentés
    "Lieux les plus fréquentés par aire de santé": "Most visited places by health area",
    "Lieux les plus fréquentés par zone de santé": "Most visited places by health zone",
    "Pour tous les cas d'une même aire de santé, quel que soit le compte qui les a saisis : les lieux d'exposition "
    "fréquentés par plusieurs cas (chronologie et lieux des fiches).":
        "For all cases in the same health area, whatever account entered them: the exposure places visited by several "
        "cases (timeline and places of the records).",
    "Pour tous les cas d'une même zone de santé, quel que soit le compte qui les a saisis : les lieux d'exposition "
    "fréquentés par plusieurs cas (chronologie et lieux des fiches).":
        "For all cases in the same health zone, whatever account entered them: the exposure places visited by several "
        "cases (timeline and places of the records).",
    "Les écritures d'un même lieu sont regroupées (majuscules, accents, précisions entre parenthèses).":
        "Different spellings of the same place are grouped (capitals, accents, details in brackets).",
    "Choisir la province…": "Choose the province…", "Choisir la zone de santé…": "Choose the health zone…",
    "Choisir l'aire de santé…": "Choose the health area…", "Nombre minimal de cas par lieu": "Minimum number of cases per place",
    "lieux fréquentés par ≥ {m} cas": "places visited by ≥ {m} case(s)",
    "Choisissez la zone de santé puis l'aire de santé pour afficher les lieux.":
        "Choose the health zone then the health area to show the places.",
    "Choisissez une zone de santé pour afficher les lieux.": "Choose a health zone to show the places.",
    "{n} cas, {l} lieu(x) fréquenté(s) par ≥ {m} cas": "{n} case(s), {l} place(s) visited by ≥ {m} case(s)",
    "Ouvrir le classement": "Open the ranking", "Classement (SVG)": "Ranking (SVG)", "Réseau des cas": "Case network",
    "Réseau (SVG)": "Network (SVG)", "Date de passage de chaque cas, contagieux ou exposé":
        "Date each case was there, infectious or exposed",
    "Lieux communs (dates)": "Shared places (dates)", "Lieux communs (SVG)": "Shared places (SVG)",
    "Cas concernés (ouvrir le mapping)": "Cases concerned (open the mapping)", "Risque max": "Max risk",
    "passage(s)": "visit(s)",
    "Aucun lieu fréquenté par au moins {m} cas dans cette sélection.": "No place visited by at least {m} case(s) in this selection.",
    "Lieux communs : qui y est passé, quand, et dans quelle période": "Shared places: who was there, when, and in which period",
    "Rouge : cas contagieux lors du passage. Bleu : cas dans sa fenêtre d'exposition. « Transmission possible » : un cas "
    "contagieux puis un cas exposé au même lieu.":
        "Red: case infectious during the visit. Blue: case in its exposure window. “Possible transmission”: an infectious "
        "case then an exposed case at the same place.",
    "Classement visuel": "Visual ranking",

    # rapports
    "Rapports par pilier": "Reports by pillar",
    "Analyse des fiches de cas enregistrées, pilier par pilier, sur la période choisie : indicateurs, graphiques, "
    "réponses aux questions du cadre d'analyse des mappings MVE et points d'attention. Les questions qui demandent des "
    "données absentes de l'outil sont listées en annexe. Réservé aux super-administrateurs.":
        "Analysis of saved case records, pillar by pillar, over the chosen period: indicators, charts, answers to the "
        "questions of the EVD mapping analysis framework and points of attention. Questions that need data not held in "
        "the tool are listed in an appendix. Reserved for super administrators.",
    "Rapport détaillé (Word)": "Detailed report (Word)", "Présentation (PowerPoint)": "Presentation (PowerPoint)",
    "Word détaillé :": "Detailed Word:",
    "page de garde, résumé exécutif, méthode, un chapitre par pilier (indicateurs clés, graphiques, questions d'analyse "
    "et réponses, points d'attention), annexe des questions non couvertes.":
        "cover page, executive summary, method, one chapter per pillar (key indicators, charts, analysis questions and "
        "answers, points of attention), appendix of questions not covered.",
    "PowerPoint :": "PowerPoint:",
    "messages clés, puis une diapositive par pilier (chiffres clés, graphique modifiable, points d'attention), et une "
    "diapositive de prochaines étapes.":
        "key messages, then one slide per pillar (key figures, editable chart, points of attention), and a next steps slide.",
    "Période : cas dont la date de notification (à défaut de confirmation, puis de début des symptômes) tombe entre les "
    "deux dates. Une information non renseignée n'est jamais comptée comme zéro.":
        "Period: cases whose notification date (failing that, confirmation date, then symptom onset) falls between the "
        "two dates. Missing information is never counted as zero.",

    # mode réunion
    "Briefing riposte MVE : situation au {d}": "EVD response briefing: situation on {d}",
    "nouveau(x) cas depuis {n} jour(s)": "new case(s) in the last {n} day(s)", "cas au total": "cases in total",
    "décès": "deaths", "alerte(s) nouveau foyer (21 j)": "new outbreak alert(s) (21 d)",
    "action(s) en retard": "overdue action(s)",
    "Zones de santé actives et indicateurs en alerte": "Active health zones and indicators on alert",
    "Zones de santé en catégorie 1 ou 2": "Health zones in category 1 or 2",
    "Aucune ZS en transmission récente.": "No health zone with recent transmission.",
    "Indicateurs en alerte (21 derniers jours)": "Indicators on alert (last 21 days)",
    "Aucun indicateur en alerte.": "No indicator on alert.", "Alertes et actions en retard": "Alerts and overdue actions",
    "Nouveau foyer possible (21 derniers jours)": "Possible new outbreak (last 21 days)", "Aucune alerte.": "No alerts.",
    "Actions en retard": "Overdue actions",
    "… et {n} autre(s) : menu Riposte → Suivi des actions.": "… and {n} more: Response menu → Action tracking.",
    "Aucune action en retard.": "No overdue actions.",
    "Flèches ← → ou espace · F : plein écran": "Arrows ← → or space · F: full screen",
    "Actualiser": "Refresh", "Quitter": "Exit",

    # indicateurs de la riposte
    "Indicateurs de la riposte": "Response indicators",
    "Indicateurs clés de la riposte et courbe épidémique": "Key response indicators and epidemic curve",
    "{n} cas au total,": "{n} case(s) in total,", "sur toute la période": "over the whole period",
    "Calculés à partir des fiches, sans rien modifier. Les cibles sont indicatives, à valider par la coordination.":
        "Calculated from the records, without changing anything. Targets are indicative, to be validated by the coordination team.",
    "Indicateurs :": "Indicators:", "Date de référence": "Reference date",
    "Nombre de reproduction observé": "Observed reproduction number",
    "cas secondaires reliés par cas": "secondary cases linked per case",
    "Au-dessus de 1, l'épidémie progresse ; en dessous, elle recule. Estimation simple à partir des liens « ID du cas "
    "source » saisis dans l'outil, à interpréter avec l'équipe épidémiologique.":
        "Above 1, the epidemic is growing; below 1, it is declining. Simple estimate from the “Source case ID” links "
        "entered in the tool, to be interpreted with the epidemiology team.",
    "Courbe épidémique : cas par semaine de début de la maladie": "Epidemic curve: cases by week of illness onset",
    "Semaine du J0 retenu (date rapportée corrigée selon la phase des premiers signes), par zone de santé, depuis le début.":
        "Week of the D0 used (reported date corrected for the phase of the first signs), by health zone, since the start.",
    "{n} cas sans date de début placé(s) à la date de notification.": "{n} case(s) without an onset date placed at the notification date.",
    "{n} cas sans aucune date non représenté(s).": "{n} case(s) without any date not shown.",
    "Pour un document à diffuser : menu": "For a document to circulate: menu",
    "Données ▾ → Rapport de situation (Word)": "Data ▾ → Situation report (Word)",

    # tableau de bord
    "Fiches enregistrées · cas notifiés du {d} au {f}": "Saved records · cases notified from {d} to {f}",
    "cas sur la période": "case(s) in the period", "{n} cas au total dans le périmètre": "{n} case(s) in total in the scope",
    "Pilier (actions)": "Pillar (actions)", "Tous les piliers": "All pillars", "Appliquer": "Apply",
    "Réinitialiser": "Reset", "Rapport Word": "Word report", "cas en alerte": "case(s) on alert",
    "avec alerte critique": "with a critical alert", "à surveiller": "to monitor",
    "Les cas avec une alerte critique passent en premier.": "Cases with a critical alert come first.",
    "À traiter": "To handle", "Prises en charge": "Taken in charge", "Réapparues": "Reappeared",
    "Résolues cette semaine": "Resolved this week", "notifié le": "notified on", "critiques": "critical",
    "Prise en charge · {p}": "Taken in charge · {p}", "Réapparue · résolue le": "Reappeared · resolved on",
    "Je m’en occupe": "I'll handle it", "Marquer résolue": "Mark resolved", "Note (facultatif)": "Note (optional)",
    "Note :": "Note:", "La fiche montre toujours le problème : mettre la fiche à jour.":
        "The record still shows the problem: update the record.",
    "Aucun cas dans cette catégorie.": "No case in this category.",
    "Aucune alerte résolue ces 7 derniers jours.": "No alert resolved in the last 7 days.",
    "Toutes fiches": "All records", "Voir les actions": "View the actions", "Aucune alerte": "No alerts",
    "sur la période et le périmètre choisis.": "for the chosen period and scope.", "Voir le détail": "View details",
    "pointillé : seuil {n} j": "dotted line: threshold {n} d", "courbe : 8 dernières semaines": "curve: last 8 weeks",
    "Cas notifiés par semaine et délai de confirmation": "Cases notified per week and confirmation delay",
    "Barres : cas notifiés · ligne : délai médian entre début des symptômes et confirmation · pointillés : seuil":
        "Bars: cases notified · line: median delay between symptom onset and confirmation · dotted: threshold",
    "Cas notifiés": "Cases notified", "Délai médian (j)": "Median delay (d)",
    "Exécution des actions par pilier": "Action completion by pillar", "action(s)": "action(s)",
    "Aucune action prescrite sur la période.": "No action prescribed in the period.",
    "Cas du périmètre": "Cases in the scope",
    "Cliquez sur un cas pour ouvrir son mapping · cliquez sur un titre de colonne pour trier":
        "Click a case to open its mapping · click a column title to sort",
    "ID cas": "Case ID", "ZS (province)": "HZ (province)", "Délai sympt. → conf.": "Delay onset → conf.",
    "Contacts listés / suivis": "Contacts listed / followed up", "Lieux PCI (décontaminés)": "IPC places (decontaminated)",
    "Actions faites": "Actions done",
    "Aucun cas notifié sur la période dans ce périmètre.": "No case notified in the period in this scope.",
    "Les exemples fictifs ne sont jamais comptés. Seuls les identifiants des cas sont affichés.":
        "Fictitious examples are never counted. Only case IDs are shown.",
    "Obstacles signalés": "Reported obstacles",
    "Causes de blocage ou de retard des actions non réalisées (champ « Blocage » des actions)":
        "Causes of blockage or delay of actions not done (“Blocker” field of the actions)",
    "Aucun obstacle signalé.": "No obstacle reported.", "À retenir": "Key points",
    "action(s) déclarée(s) réalisée(s) sans preuve : demander le justificatif.":
        "action(s) reported done without evidence: ask for the supporting document.",
    "action(s) avec preuve en attente de vérification par un superviseur.":
        "action(s) with evidence awaiting verification by a supervisor.",
    "action(s) en retard sans obstacle signalé : relancer le responsable.":
        "overdue action(s) with no obstacle reported: follow up with the responsible person.",
    "action(s) non vérifiée(s) sans responsable.": "unverified action(s) without a responsible person.",
    "Preuve, blocage et vérificateur se renseignent dans la partie « Actions » de chaque fiche.":
        "Evidence, blocker and verifier are entered in the “Actions” part of each record.",
    "Registre des actions": "Action register", "Les plus urgentes en premier": "Most urgent first",
    "Toutes les catégories": "All categories", "Cas (ZS)": "Case (HZ)", "à désigner": "to be assigned",
    "{n} j de retard": "{n} d overdue", "Aucune action.": "No actions.", "Par zone de santé": "By health zone",
    "« ? » : non renseigné dans les fiches (jamais compté comme 0)": "“?”: not entered in the records (never counted as 0)",
    "dont haut risque": "of which high risk", "% suivis": "% followed up",
    "Aucun cas sur la période.": "No case in the period.", "Lien avec un cas connu": "Link with a known case",
    "Les cas « non contact » ou de lien inconnu signalent une transmission non maîtrisée.":
        "“Not a contact” cases or cases with an unknown link point to uncontrolled transmission.",
    "Aucun cas.": "No cases.", "cas sur {n} reliés à un cas source identifié (ID).":
        "case(s) out of {n} linked to an identified source case (ID).",
    "décès communautaire(s) (sans hospitalisation avant le décès).": "community death(s) (no hospitalisation before death).",
    "agent(s) de santé parmi les cas.": "health worker(s) among the cases.",
    "Expositions à risque et mobilité": "Risk exposures and mobility",
    "Étapes de la chronologie des cas, toutes fiches confondues": "Steps of the case timelines, all records combined",
    "Aucune exposition à risque renseignée.": "No risk exposure entered.",
    "Complétude moyenne par zone de santé": "Average completeness by health zone", "Seuil de vigilance :": "Alert threshold:",
    "Éléments le plus souvent manquants": "Most often missing items", "Nombre de fiches concernées": "Number of records concerned",
    "Rien ne manque.": "Nothing is missing.", "fiche(s) avec des dates incohérentes.": "record(s) with inconsistent dates.",
    "brouillon(s) non enregistré(s) dans le périmètre.": "unsaved draft(s) in the scope.",
    "Questions du cadre d'analyse des mappings MVE": "Questions of the EVD mapping analysis framework",
    "Réponses calculées sur la période et le périmètre choisis. Les mêmes réponses figurent dans le rapport Word.":
        "Answers calculated for the chosen period and scope. The same answers appear in the Word report.",
    "Non couvert": "Not covered", "non collecté": "not collected", "manque :": "missing:",

    # utilisateurs
    "Province…": "Province…", "Zone de santé…": "Health zone…", "choisir ou saisir…": "choose or type…",
    "Compte « {u} »": "Account “{u}”", "mot de passe": "password",
    "Notez-le et transmettez-le à la personne : il ne sera plus affiché.":
        "Write it down and give it to the person: it will not be shown again.",
    "Nouveau compte": "New account",
    "Administrateur provincial : vous créez des comptes de zone de santé ou d'aire de santé de la province {p}.":
        "Provincial administrator: you create health zone or health area accounts for the province {p}.",
    "Un administrateur provincial se crée avec le niveau « Provincial » et le rôle Administrateur (réservé à "
    "l'administration nationale).":
        "A provincial administrator is created with the “Provincial” level and the Administrator role (reserved for "
        "the national administration).",
    "ex. agent.ganga": "e.g. agent.ganga", "Rôle": "Role", "Utilisateur": "User",
    "Administrateur (gère les comptes)": "Administrator (manages accounts)",
    "Partenaire (consultation seule, tous les cas)": "Partner (view only, all cases)", "Créer le compte": "Create the account",
    "Voit": "Sees", "Corrige": "Edits", "ses propres cas": "own cases",
    "tous les cas de sa ZS (dont ceux de ses aires de santé)": "all cases of their HZ (including those of its health areas)",
    "ses cas et ceux des comptes AS / ZS de sa zone": "own cases and those of the HA / HZ accounts of their zone",
    "tous les cas de sa province (toutes ZS et AS)": "all cases of their province (all HZ and HA)",
    "tous les cas de toutes les provinces": "all cases of all provinces", "tous les cas de sa province": "all cases of their province",
    "les cas de sa province, et les comptes de ses zones de santé": "the cases of their province, and the accounts of its health zones",
    "tout": "everything", "tout, plus la gestion de tous les comptes": "everything, plus management of all accounts",
    "Niveau national : vous pouvez consulter et supprimer des comptes. Chaque suppression est inscrite dans l'historique.":
        "National level: you can view and delete accounts. Each deletion is recorded in the history.",
    "Dernière connexion": "Last sign-in", "actif": "active", "désactivé": "deactivated", "Désactiver": "Deactivate",
    "Activer": "Activate", "Rendre agent": "Make agent", "Rendre admin": "Make admin",
    "Supprimer le compte « {u} » ? Ses fiches sont conservées. Motif (facultatif) :":
        "Delete the account “{u}”? Its records are kept. Reason (optional):",
    "Seul {u} peut modifier ce compte": "Only {u} can change this account", "compte principal": "main account",
    "Changer le niveau / le périmètre": "Change the level / scope",
    "Historique des suppressions de comptes": "Account deletion history", "Supprimé par": "Deleted by",
    "Fiches conservées": "Records kept", "Aucune suppression.": "No deletions.",

    # catégories des zones de santé
    "Catégories des ZS": "HZ categories",
    "Catégories des zones de santé, délais et incubation": "Health zone categories, delays and incubation",
    "Date de notification de chaque cas (à défaut : confirmation, puis début des symptômes). Seuils dans":
        "Notification date of each case (failing that: confirmation, then symptom onset). Thresholds in",
    "sans nouveau cas": "without a new case", "7 derniers j": "Last 7 d", "21 derniers j": "Last 21 d",
    "AS touchées": "HAs affected", "Dernier cas notifié": "Last case notified", "Jours sans nouveau cas": "Days without a new case",
    "sans date": "without a date", "Aucun cas dans ce périmètre.": "No case in this scope.",
    "Alertes : nouveau foyer possible (60 derniers jours)": "Alerts: possible new outbreak (last 60 days)",
    "Premier cas notifié dans une ZS ou une AS, ou reprise après plus de {n} jours sans cas : à investiguer en priorité.":
        "First case notified in an HZ or HA, or resurgence after more than {n} days without a case: to investigate first.",
    "Délais et incubation observés": "Observed delays and incubation", "Cas utilisés": "Cases used",
    "L'incubation observée n'utilise que les contacts connus dont la date du dernier contact avec le cas source est "
    "renseignée.": "Observed incubation only uses known contacts whose date of last contact with the source case is entered.",
})
