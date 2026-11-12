"""Langue de l'interface web (français par défaut, anglais).

Les textes sont écrits en français dans les gabarits et passés à t("…") : en anglais, la traduction ci-dessous est
utilisée ; un texte sans traduction reste en français (rien ne disparaît). La langue est gardée pour le compte
(table preferences) et dans la session.
Première étape : connexion, accueil, menus, liste des cas, messages principaux. Le formulaire de la fiche et les
visuels produits (mapping, rapports) restent en français.
"""
from __future__ import annotations

import re
from typing import Optional

LANGUES = {"fr": "Français", "en": "English"}

EN = {
    # barre du haut et menus
    "Cas": "Cases", "Analyses": "Analyses", "Riposte": "Response", "Données": "Data", "Utilisateurs": "Users",
    "Tutoriel": "Tutorial", "Mon compte": "My account", "Déconnexion": "Sign out", "Thème": "Theme", "Langue": "Language",
    "Menu": "Menu", "parcours épidémiologique": "epidemiological pathway",
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
    "Pour tout contact :": "Contact:", "Équipe de développement : Onesime Mbulayi et al.":
        "Development team: Onesime Mbulayi et al.",
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
    "Documentez ici le parcours épidémiologique de chaque cas confirmé. Renseignez l'ensemble des champs obligatoires, "
    "signalés par un astérisque (*), puis enregistrez la fiche : seules les fiches complètes et enregistrées sont "
    "prises en compte dans les analyses et partagées avec la coordination.":
        "Use this tool to document the epidemiological pathway of each confirmed case. Complete all mandatory fields, "
        "marked with an asterisk (*), then save the record: only complete, saved records are included in the analyses "
        "and shared with the coordination team.",
    "Créer la fiche": "Create the record", "Compléter les champs *": "Complete the * fields", "Enregistrer": "Save",
    "Nouveau cas": "New case", "Voir mes cas": "View my cases", "Voir les cas": "View cases",
    "Exemple fictif": "Practice example", "pour s'entraîner": "for practice", "reprendre mon exemple": "resume my example",
    "enregistré": "saved", "enregistrés": "saved", "brouillon": "draft", "brouillons": "drafts",
    # liste des cas
    "Mes cas": "My cases", "Tous les cas": "All cases", "Cas de mon périmètre": "Cases in my area",
    "Enregistrés": "Saved", "Brouillons": "Drafts", "← Accueil": "← Home", "＋ Nouveau cas": "＋ New case",
    "Rechercher (ID, ZS, AS, maladie, agent…)": "Search (ID, zone, area, disease, user…)",
    "Rechercher (ID, ZS, AS, maladie…)": "Search (ID, zone, area, disease…)",
    "Tous les comptes": "All accounts", "Toutes les provinces": "All provinces", "Toutes les ZS": "All health zones",
    "Toutes les AS": "All health areas", "Filtrer": "Filter", "Effacer": "Clear", "Ouvrir": "Open",
    "Consulter": "View", "Mapping": "Mapping", "Voir le mapping": "View the mapping", "moi": "me",
    "ID / fiche": "ID / record", "Province": "Province", "ZS": "Zone", "AS": "Area", "J0": "Onset",
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
    "En tant qu'administrateur, vous voyez et corrigez les mappings de tous les comptes.":
        "As an administrator, you can view and edit the mappings of all accounts.",
    "Vous voyez et corrigez les cas de votre zone de santé, dont ceux de ses aires de santé.":
        "You can view and edit the cases of your health zone, including those of its health areas.",
    "Vous voyez les cas de toutes les provinces ; les fiches des autres comptes s'ouvrent en lecture seule.":
        "You can view cases from all provinces; records from other accounts open read-only.",
    "Vous voyez les cas de votre province ; les fiches des autres comptes s'ouvrent en lecture seule.":
        "You can view the cases of your province; records from other accounts open read-only.",
}

_NB = re.compile(r"^(\d+) ")


def t(texte: str, lang: Optional[str]) -> str:
    """Traduction de `texte` (français) dans la langue `lang` ; à défaut, le texte français."""
    if lang != "en" or not texte:
        return texte
    return EN.get(texte, texte)


# -- préférence du compte ---------------------------------------------------------------------------
def _init(store) -> None:
    store.db.execute("CREATE TABLE IF NOT EXISTS preferences(username TEXT, cle TEXT, valeur TEXT, "
                     "PRIMARY KEY(username, cle))")


def langue_du_compte(store, username: str) -> Optional[str]:
    _init(store)
    r = store.db.execute("SELECT valeur FROM preferences WHERE username=? AND cle='langue'", (username,)).fetchone()
    return r[0] if r and r[0] in LANGUES else None


def enregistrer_langue(store, username: str, lang: str) -> None:
    if lang not in LANGUES:
        return
    _init(store)
    with store.lock:
        store.db.execute("INSERT INTO preferences(username, cle, valeur) VALUES(?, 'langue', ?) "
                         "ON CONFLICT(username, cle) DO UPDATE SET valeur=excluded.valeur", (username, lang))
        store.db.commit()
