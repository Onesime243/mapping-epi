"""Description des colonnes des tableaux de saisie (partagée bureau / web)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from config import theme


@dataclass
class Col:
    key: str
    label: str
    kind: str = "text"          # text | combo | choice | date | datetime | int? | float? | bool | computed
    choices: Sequence[str] = ()
    width: int = 0
    tip: str = ""
    complete: bool = False      # autocomplétion des lieux


EVENT_COLS = [
    Col("date_debut", "Date début", "date", width=123, tip="JJ/MM/AAAA — vide si inconnue"),
    Col("date_fin", "Date fin", "date", width=123, tip="Pour une période (ex. 01–14/08)"),
    Col("heure", "Heure", width=91, tip="ex. 23h, 04h, 15–17h"),
    Col("heure_approx", "~", "bool", width=41, tip="Heure approximative (affiche ~23h)"),
    Col("date_incertaine", "Date ?", "bool", width=71, tip="Date incertaine (barre en pointillés)"),
    Col("lieu", "Lieu / départ", width=182, complete=True),
    Col("lieu_arrivee", "Arrivée", width=156, complete=True, tip="Pour un déplacement A → B"),
    Col("type", "Type d'étape", "choice", theme.EVENT_TYPE_CHOICES, width=208),
    Col("titre", "Titre affiché", width=195),
    Col("description", "Description", width=286, tip="Utiliser • pour séparer les éléments"),
    Col("transport", "Transport", "combo", theme.TRANSPORTS, width=123),
    Col("personnes", "Personnes présentes", width=195),
    Col("contact_corps", "Corps", "bool", width=65, tip="Contact avec le corps → risque très élevé"),
    Col("liquides", "Liquides", "bool", width=78, tip="Liquides biologiques → +1 niveau"),
    Col("sans_pci", "Sans PCI", "bool", width=84, tip="Soins / contacts sans PCI → +1 niveau"),
    Col("securise", "Sécurisé", "bool", width=84, tip="Enterrement digne et sécurisé / transport sécurisé"),
    Col("risque", "Risque (vide = auto)", "choice", [""] + theme.RISK_CHOICES, width=169),
    Col("_suggere", "Suggéré", "computed", width=195, tip="Risque suggéré par les règles (info-bulle : règle appliquée)"),
]

PLACE_COLS = [
        Col("nom", "Lieu", width=221, complete=True), Col("type", "Type", "combo", theme.PLACE_TYPES, width=208),
        Col("population", "Population exposée", width=260), Col("nombre", "Nombre estimé", "int?", width=130),
        Col("risque", "Risque (vide = auto)", "choice", [""] + theme.RISK_CHOICES, width=169),
        Col("lat", "Latitude", "float?", width=117), Col("lon", "Longitude", "float?", width=117),
        Col("_suggere", "Suggéré", "computed", width=143)]

CONTACT_COLS = [
        Col("categorie", "Catégorie", "combo", ["Famille & amis", "Prestataires de soins", "Co-patients", "PPL / garde-malades",
                                                  "Motard(s)", "Équipe pastorale", "Fidèles", "Participants funérailles",
                                                  "Voisins", "Collègues"], width=247),
        Col("lien", "Lien avec le cas", width=182), Col("nombre", "Nombre (? = inconnu)", "int?", width=169),
        Col("libelle_nombre", "Libellé", width=91, tip="ex. « listés »"), Col("suivis", "Suivis", "int?", width=91),
        Col("risque", "Risque", "choice", theme.CONTACT_RISK_CHOICES, width=123),
        Col("lieu", "Lieu de contact", width=195, complete=True), Col("dernier_contact", "Dernier contact", "date", width=143),
        Col("_fin", "Fin du suivi", "computed", width=130)]

IPC_COLS = [
        Col("site", "Site", width=260, complete=True), Col("statut", "Statut", "choice", theme.IPC_CHOICES, width=156),
        Col("date", "Date", "date", width=130), Col("equipe", "Équipe", width=208), Col("produit", "Produit", width=208)]

LAB_COLS = [
        Col("type", "Échantillon", "combo", ["Swab", "Sang total", "Plasma", "Urine", "Autre"], width=143),
        Col("laboratoire", "Laboratoire", width=182),
        Col("prelevement", "Prélèvement", "datetime", width=169, tip="JJ/MM/AAAA HH:MM"),
        Col("envoi", "Envoi", "datetime", width=169), Col("reception", "Réception", "datetime", width=169),
        Col("resultat_le", "Résultat le", "datetime", width=169),
        Col("resultat", "Résultat", "combo", ["Positif", "Négatif", "En attente", "Indéterminé"], width=143),
        Col("_delai", "Délai", "computed", width=104)]

ACTION_COLS = [
    Col("texte", "Action", width=416), Col("priorite", "Priorité", "choice", theme.ACTION_PRIORITY_CHOICES, width=130),
    Col("responsable", "Responsable", width=182), Col("echeance", "Échéance", "date", width=130),
    Col("statut", "Statut", "choice", theme.ACTION_STATUS_CHOICES, width=117),
    Col("auto", "Suggérée", "bool", width=91)]
