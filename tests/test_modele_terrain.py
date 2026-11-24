"""Modèle Word des investigateurs de terrain (« Rapport d'investigation MVE ») : copie entièrement FICTIVE."""
import io
import re
from datetime import date

import pytest

from core import modele_terrain as MT
from core.storage import Store
from core.users import Users

IDENT = [("CODE VHF", "RDC-ITU-XXX-26-0000001-MVE"), ("NOM", "FICTIFNOM"), ("POST NOM", "FICTIFPOST"), ("PRÉNOM", ""),
         ("AGE", "40 ans"), ("SEXE", "F"), ("PROFESSION", "Commerçante"), ("Village", "VILLAGEA"),
         ("AIRE DE SANTE", "LEMBABO"), ("COMMUNE/TERRITOIRE", "IRUMU"), ("ZONE DE SANTE", "BUNIA"),
         ("DATE DE NOTIFICATION", "Le 15/11/2026"), ("DATE DE CONFIRMATION", "Le 20/11/2026"),
         ("DATE DE DÉBUT DES SYMPTOMES", "08/11/2026"),
         ("NATURE DU CAS", "☒Décès communautaire ☒ Swab réalisé ☒ Confirmé décédé ☐ Probable ☐Vivant confirmé"),
         ("DATE DE DÉCÈS", "18/11/2026"),
         ("ENTERREMENT DIGNE ET SECURISÉ FAIT", "☐ Oui ☒ Non Si non : date et lieu enterrement non sécurisé 20/11/2026, Village VILLAGEB"),
         ("CAS CONTACT CONNU", "☒ Oui ☐ Non Si oui : CODE CONTACT NOM DU CONTACT RDC-ITU-XXX-26-0000002-MVE SOURCENOM FICTIF"),
         ("CAS VACCINÉ", "☐Oui ☒Non"), ("PÉRIODE INVESTIGATION", "DU 20 au 21/11/2026")]
SUITE = [
    "II-MÉTHODE D’INVESTIGATION", "☒ Entretien avec les membres de la famille",
    "III-RÉSULTATS DE L’INVESTIGATION", "A-FACTEURS D’EXPOSITION AVANT MALADIE",
    "CONTACT AVEC UN MALADE (CAS CONTAMINANT SUSPECT / CONFIRMÉ / PROBABLE)", "☒ OUI",
    "LIEN(S) ÉPIDÉMIOLOGIQUE(S) LE(S) PLUS PLAUSIBLE(S)",
    "Le cas a soigné SOURCENOM FICTIF dans sa pharmacie entre le 29/10 et le 31/10/2026.",
    "Avec la date de début des symptômes : 17/10/2026 au 30/10/2026",
    "B-HISTOIRE DE LA MALADIE et PARCOURS DU MALADE",
    "- En date du 29 au 31/10/2026, le cas avait soigné monsieur SOURCENOM FICTIF RDC-ITU-XXX-26-0000002-MVE ;",
    "- Le 8/11/2026, le contact était devenu suspect avec comme signes fièvre et céphalée ;",
    "- Du 10 au 13/11/2026, il a consulté deux tradipraticiens, le 14/11/2026, il a refusé le référencement au CTE BUNIA ;",
    "- En date du 15/11/2026, il s’était déplacé du village VILLAGEA vers le village VILLAGEB ;",
    "- Du 15 au 17/11/2026, il a été traité à domicile par un infirmier suite au vomissement et à la diarrhée ;",
    "- Le 18/11/2026 l’alerte décès communautaire a été remontée ;",
    "- Le 19/11/2026 : réalisation du SWAB ;",
    "- Le 20/11/2026 : acheminement de l'échantillon au Labo et résultat. Cette même date l’enterrement non sécurisé a été réalisé au village VILLAGEB",
    "LISTAGE CONTACTS", "NOMBRE DE CONTACTS LISTÉS PAR LIEU DE CONTACT :",
    "LIEU DE CONTACT", "NOMBRE LISTÉS", "Famille (ménages, voisins et amis)", "3", "Tradipraticiens", "En cours", "Total", "3",
    "IV-ACTIONS DE SANTÉ PUBLIQUE MENÉES", "Swab réalisé", "Listage de contacts",
    "V-DÉFIS ET DIFFICULTÉS RENCONTRÉS", "- Refus de la décontamination par la famille",
    "VII.EQUIPE D’INVESTIGATEUR", "1. Dr ENQUETEUR FICTIF, MCZ : +243810000000, enqueteur@exemple.org",
]


def rapport_fictif() -> bytes:
    from docx import Document
    d = Document()
    d.add_paragraph("Dans le cadre de la riposte, l'équipe devait entreprendre des actions de Santé Publique.")
    d.add_paragraph("I-IDENTIFICATION DU DECES")
    t = d.add_table(rows=len(IDENT), cols=2)          # identification en tableau, comme le modèle terrain
    for r, (k, v) in zip(t.rows, IDENT):
        r.cells[0].text, r.cells[1].text = k, v
    for l in SUITE:
        d.add_paragraph(l)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def test_lecture_du_modele_terrain(tmp_path):
    f = tmp_path / "rapport.docx"
    f.write_bytes(rapport_fictif())
    r = MT.lire(f)
    assert r is not None
    c = r.case
    assert (c.code_cas, c.age, c.sexe, c.profession) == ("RDC-ITU-XXX-26-0000001-MVE", 40, "F", "Commerçante")
    assert c.zs.lower() == "bunia" and c.province == "Ituri" and c.issue == "Décès" and c.vaccine == "Non"
    assert c.contact_connu == "Contact connu" and c.id_cas_source == "RDC-ITU-XXX-26-0000002-MVE"
    assert c.date_contact_source == date(2026, 10, 31) and c.debut_symptomes == date(2026, 11, 8)
    types = [e.type for e in c.events]
    assert types[0] == "Exposition" and "Déplacement" in types and "Enterrement" in types
    assert types.count("Déplacement") == 1                              # le référencement refusé n'est pas un déplacement
    dep = next(e for e in c.events if e.type == "Déplacement")
    assert dep.lieu == "Village VILLAGEA" and dep.lieu_arrivee == "Village VILLAGEB"
    ent = next(e for e in c.events if e.type == "Enterrement")
    assert ent.date_debut == date(2026, 11, 20) and not ent.securise and ent.lieu == "Village VILLAGEB"
    assert [g.nombre for g in c.contacts] == [3, None]
    assert [a.texte for a in c.actions] == ["Swab réalisé", "Listage de contacts"] and all(a.statut == "Fait" for a in c.actions)
    assert "Refus de la décontamination" in c.note_pied
    # aucun nom de personne, téléphone ni courriel repris
    texte = c.model_dump_json()
    for x in ("FICTIFNOM", "FICTIFPOST", "SOURCENOM", "ENQUETEUR", "810000000", "exemple.org"):
        assert x.lower() not in texte.lower(), x


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "donnees"))
    from core import pyramide
    pyramide._SINGLETON = None
    from web.server import create_app
    a = create_app(Store(tmp_path / "donnees" / "mapping_epi.sqlite"))
    a.testing = True
    return a


def _login(c, u, p):
    tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/connexion").get_data(as_text=True)).group(1)
    c.post("/connexion", data={"csrf": tok, "username": u, "password": p})
    return re.search(r'name="csrf" value="([^"]+)"', c.get("/cas").get_data(as_text=True)).group(1)


def test_import_et_reimport_du_modele_terrain(app):
    Users(app.store).create("zs.bunia", "Secret123", niveau="zone", province="Ituri", zs="Bunia")
    c = app.test_client()
    tok = _login(c, "zs.bunia", "Secret123")
    r = c.post("/cas/importer", data={"csrf": tok, "fichier": (io.BytesIO(rapport_fictif()), "Rapport_terrain.docx")},
               content_type="multipart/form-data")
    assert r.status_code == 302
    cid = r.headers["Location"].rstrip("/").split("/")[-1]
    cas = app.store.load(cid) or app.store.load_brouillon(cid)[0]
    assert cas.code_cas == "RDC-ITU-XXX-26-0000001-MVE" and len(cas.events) >= 8
    # téléchargement : toujours nos modèles (Word / Excel) ; réimport du modèle terrain dans la même fiche
    assert c.get(f"/cas/{cid}/fiche.docx").status_code == 200
    r = c.post(f"/cas/{cid}/reimporter", data={"csrf": tok, "fichier": (io.BytesIO(rapport_fictif()), "Rapport.docx")},
               content_type="multipart/form-data")
    assert r.status_code == 302 and len(app.store.list_full()) == 1
