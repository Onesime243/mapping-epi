"""Mentions affichées dans l'outil (pied de page web, aide, modèle Excel, README)."""

INSTITUTION = "Système de gestion de l’incident, SGI-RDC, avec l’appui de UMIE-INRB"
EQUIPE = "Équipe de développement : Onesime Mbulayi et al."
CONTACTS = ["mbonesime@gmail.com", "dav.ebengo@umie-inrb.org"]


def texte() -> str:
    return f"{INSTITUTION} · {EQUIPE} · Pour tout contact : {', '.join(CONTACTS)}"
