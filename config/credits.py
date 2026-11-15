"""Mentions affichées dans l'outil (pied de page web, aide, modèle Excel, README)."""

INSTITUTION = "Système de gestion de l’incident, SGI-RDC, avec l’appui de UMIE-INRB"
EQUIPE = "Équipe de développement : Onesime Mbulayi et al."
CONTACTS = ["mbonesime@gmail.com", "dav.ebengo@umie-inrb.org"]
LICENCE = "Logiciel libre sous licence GNU AGPL v3"


def texte() -> str:
    return f"{INSTITUTION} · {EQUIPE} · Pour tout contact : {', '.join(CONTACTS)}"

# bandeau du site web (armoiries de la RDC : web/static/armoiries_rdc.svg, domaine public, Wikimedia Commons)
BANDEAU_SUR = "SGI-RDC · Riposte Ebola 2026"
BANDEAU_TITRE = "Mapping Épi"
BANDEAU_SOUS = "Documentation du parcours épidémiologique des cas confirmés · avec l’appui de l’UMIE-INRB"
