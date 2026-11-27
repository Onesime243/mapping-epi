"""Mapping Épi 2.0, lot 1 : dates clés, chronologie simplifiée, cascade des contacts, DHIS2, anomalies."""
import json
from datetime import date, datetime

import pytest

from core import langue, rules, storage
from core.models import Action, Case, ContactGroup, Event, LabSample, Place
from render import chrono
from tests.test_web import _csrf, _login, app  # noqa: F401  (fixture)



@pytest.fixture(autouse=True)
def _francais():
    langue.definir("fr")
    yield
    langue.definir("fr")


def _cas():
    return Case(code_cas="FICTIF-QC-001", zs="Watsa", debut_symptomes=date(2026, 11, 11), phase_dds="Phase sèche",
                date_alerte=date(2026, 11, 11), date_investigation=date(2026, 11, 12), date_notification=date(2026, 11, 12),
                date_confirmation=date(2026, 11, 12), date_isolement=date(2026, 11, 15), date_admission_cte=date(2026, 11, 25),
                issue="En traitement", contacts_dhis2_listes=14, contacts_dhis2_suivis=11,
                contacts=[ContactGroup(categorie="Co-patients", exposes=50, nombre=63, suivis=0, symptomatiques=1, confirmes=1),
                          ContactGroup(categorie="Famille", nombre=4, suivis=0, symptomatiques=5)],
                events=[Event(date_debut=date(2026, 11, 22), lieu="Clinique Doko", lieu_arrivee="CTE Watsa", type="Autre")],
                labs=[LabSample(resultat_le=datetime(2026, 11, 12, 14), resultat="Positif"),
                      LabSample(resultat_le=datetime(2026, 11, 24, 9), resultat="Négatif"),
                      LabSample(resultat_le=datetime(2026, 11, 26, 9), resultat="Négatif")],
                places=[Place(nom="Clinique Bavière"), Place(nom="CM La Bavière")],
                actions=[Action(texte="Suivi quotidien des contacts", statut="Fait")])


def test_controles_qualite():
    msgs = {i.message: i.niveau for i in rules.controles_qualite(_cas())}
    txt = " | ".join(msgs)
    assert "Isolement effectif 3 j après la confirmation" in txt
    assert "Contradiction : admission au CTE le 25/11, mais la chronologie place le CTE le 22/11" in txt
    assert "plus de listés que d'exposés estimés" in txt
    assert msgs["Contacts « Famille » : plus de contacts devenus symptomatiques que de listés."] == "erreur"
    assert "0 suivi saisi alors qu'une action de suivi est marquée « Fait »" in txt
    assert "67 listés dans la fiche, 14 dans DHIS2 (sous-listing potentiel, écart 53)" in txt
    assert "issue à valider" in txt
    assert "« Clinique Bavière » et « CM La Bavière »" in txt
    # contrôles repris dans les contrôles de la fiche
    assert any("Isolement effectif" in i.message for i in rules.check_consistency(_cas()))


def test_cas_sans_nouvelles_donnees_sans_anomalie():
    c = Case(debut_symptomes=date(2026, 11, 1), date_confirmation=date(2026, 11, 3))
    assert rules.controles_qualite(c) == []


def test_chronologie_simplifiee_svg():
    svg = chrono.render_svg(_cas())
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    for t in ("CHRONOLOGIE SIMPLIFIÉE", "J0 rapporté", "J0 retenu", "Isolement effectif", "Admission au CTE",
              "Cascade des contacts", "Listés dans DHIS2", "Points à vérifier"):
        assert t in svg
    vide = chrono.render_svg(Case())
    assert "Aucune date clé saisie" in vide and "Non renseigné" in vide     # rien d'inventé, jamais 0


def test_excel_aller_retour_nouveaux_champs(tmp_path):
    p = tmp_path / "f.xlsx"
    storage.export_excel(_cas(), p)
    b = storage.import_excel(p)
    assert (b.date_alerte, b.date_isolement, b.date_admission_cte) == (date(2026, 11, 11), date(2026, 11, 15), date(2026, 11, 25))
    assert (b.contacts_dhis2_listes, b.contacts_dhis2_suivis) == (14, 11)
    g = b.contacts[0]
    assert (g.exposes, g.nombre, g.symptomatiques, g.confirmes) == (50, 63, 1, 1)
    assert b.contacts[1].exposes is None                 # inconnu reste inconnu


def test_web_apercu_et_anomalies(app):  # noqa: F811
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123",
                                  "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    case = c.get(f"/api/cas/{cid}").get_json()["case"]
    case.update(entrainement=False, code_cas="RDC-QC-26-001", date_isolement="2026-08-05", contacts_dhis2_listes=3)
    hdr = {"X-CSRF": tok, "Content-Type": "application/json"}
    assert c.put(f"/api/cas/{cid}", data=json.dumps(case), headers=hdr).status_code == 200
    page = c.get(f"/cas/{cid}").get_data(as_text=True)
    assert "Chronologie simplifiée" in page and 'id="datesCles"' in page and 'id="contactsDhis2"' in page
    assert "CHRONOLOGIE SIMPLIFIÉE" in c.get(f"/cas/{cid}/apercu/chrono").get_data(as_text=True)
    r = c.get(f"/cas/{cid}/telecharger/svg?visuel=chrono")
    assert r.status_code == 200 and "Chronologie_" in r.headers["Content-Disposition"]
    tb = c.get("/tableau-de-bord?debut=2026-01-01&onglet=qualite").get_data(as_text=True)
    assert "Anomalies à vérifier" in tb and "RDC-QC-26-001" in tb and "sous-listing potentiel" in tb
    assert "onglet=qualite" in tb                        # lien du menu Données


def test_chronologie_en_anglais():
    with langue.utiliser("en"):
        svg = chrono.render_svg(_cas())
        msgs = " ".join(i.message for i in rules.controles_qualite(_cas()))
    assert "SIMPLIFIED TIMELINE" in svg and "Contact cascade" in svg and "Reported D0" in svg
    assert "Actual isolation 3 d after confirmation" in msgs and "Isolement" not in msgs
