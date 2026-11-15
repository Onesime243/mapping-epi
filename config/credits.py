"""Mentions affichées dans l'outil (pied de page web, aide, modèle Excel, README)."""

INSTITUTION = "Système de gestion de l’incident, SGI-RDC, avec l’appui de UMIE-INRB"
EQUIPE = "Équipe de développement : Onesime Mbulayi, John Kombe et al."
CONTACTS = ["mbonesime@gmail.com", "dav.ebengo@umie-inrb.org"]
LICENCE = "Logiciel libre sous licence GNU AGPL v3"


def texte() -> str:
    return f"{INSTITUTION} · {EQUIPE} · Pour tout contact : {', '.join(CONTACTS)}"

# bandeau du site web (sceau : web/static/sceau_presidence.png)
BANDEAU_SUR = "Task Force Présidentielle Ebola 17"
BANDEAU_TITRE = "Système de Gestion de l’Incident MVE 17"
BANDEAU_SOUS = "Documentation du parcours épidémiologique des cas confirmés"
