"""Mapping Épi 2.0, lots 2 à 5 : parcours clinique, besoins, trajets, command center, centre des actions,
goulots, concordance DHIS2, vaccination, psychosocial, services essentiels, PoE / PoC, PCI enrichi."""
import json
from datetime import date, datetime, timedelta

import pytest

from core import coordination as CO
from core import langue, storage
from core.models import Action, Case, ContactGroup, Event, IPCSite, LabSample
from render import clinique, map_view
from tests.test_web import _csrf, _login, app  # noqa: F401  (fixture)

REF = date(2026, 11, 27)


@pytest.fixture(autouse=True)
def _francais():
    langue.definir("fr")
    yield
    langue.definir("fr")


def _cas(code="FICTIF-L2-001", zs="Watsa", **kw):
    base = dict(code_cas=code, zs=zs, province="Ituri", debut_symptomes=date(2026, 11, 11), date_alerte=date(2026, 11, 11),
                date_investigation=date(2026, 11, 13), date_confirmation=date(2026, 11, 12), date_isolement=date(2026, 11, 15),
                date_premiere_consultation=date(2026, 11, 12), date_admission_cte=date(2026, 11, 25),
                date_debut_traitement=date(2026, 11, 25), issue="En traitement", date_debut_anneau=date(2026, 11, 13),
                suivi_obstetrical="Documenté", suivi_nouveau_ne="À vérifier", besoin_psychosocial="Besoin identifié",
                contacts_dhis2_listes=14, contacts_dhis2_suivis=11,
                contacts=[ContactGroup(categorie="Co-patients", nombre=63, suivis=40, eligibles=50, vaccines=30, motif_non_vaccination="Refus"),
                          ContactGroup(categorie="Famille", nombre=4, suivis=4, vaccines=4)],
                events=[Event(date_debut=date(2026, 11, 7), lieu="Domicile", lieu_arrivee="Clinique Doko", transport="Moto",
                              nb_trajets=5, poe_poc="PoC Bunia-Komanda", type="Déplacement")],
                ipc=[IPCSite(site="Domicile", statut="Décontaminé", identifie_le=date(2026, 11, 12), date=date(2026, 11, 14),
                             verifie_le=date(2026, 11, 15), preuve="photo"),
                     IPCSite(site="Clinique Doko", statut="Non")],
                labs=[LabSample(prelevement=datetime(2026, 11, 12, 9), resultat_le=datetime(2026, 11, 12, 18), resultat="Positif"),
                      LabSample(resultat_le=datetime(2026, 11, 24, 9), resultat="Négatif"),
                      LabSample(resultat_le=datetime(2026, 11, 26, 9), resultat="Négatif")],
                actions=[Action(texte="Lister les contacts", statut="À faire", echeance=date(2026, 11, 20), pilier="Suivi des contacts"),
                         Action(texte="Décontaminer le domicile", statut="Fait", pilier="PCI", preuve="photo"),
                         Action(texte="Vérifier l'éligibilité vaccinale", statut="Fait", pilier="Vaccination", valide_par="Superviseur ZS"),
                         Action(texte="Évaluer les passages aux PoC", statut="En cours", echeance=date(2026, 12, 5))])
    base.update(kw)
    return Case(**base)


def test_excel_aller_retour_lots2_5(tmp_path):
    p = tmp_path / "f.xlsx"
    storage.export_excel(_cas(), p)
    b = storage.import_excel(p)
    assert (b.date_premiere_consultation, b.date_debut_traitement) == (date(2026, 11, 12), date(2026, 11, 25))
    assert (b.suivi_obstetrical, b.suivi_nouveau_ne, b.besoin_psychosocial, b.soutien_famille) == ("Documenté", "À vérifier", "Besoin identifié", "")
    assert (b.events[0].nb_trajets, b.events[0].poe_poc) == (5, "PoC Bunia-Komanda")
    assert (b.ipc[0].identifie_le, b.ipc[0].verifie_le, b.ipc[0].preuve) == (date(2026, 11, 12), date(2026, 11, 15), "photo")
    assert (b.contacts[0].eligibles, b.contacts[0].motif_non_vaccination) == (50, "Refus")
    assert b.contacts[1].eligibles is None


def test_visuel_parcours_clinique_et_trajets():
    svg = clinique.render_svg(_cas())
    for t in ("PARCOURS CLINIQUE", "1re consultation", "Admission CTE", "PCR négatives", "Délais cliniques",
              "Laboratoire successif", "Suivi du nouveau-né", "À vérifier", "Non renseigné"):
        assert t in svg
    assert "ND" in clinique.render_svg(Case())                      # rien d'inventé
    carte = map_view.render_svg(_cas())
    assert "×5" in carte and "PoC Bunia-Komanda" in carte and 'stroke-width="9.4"' in carte


def test_command_center_et_centre_actions():
    cases = [_cas(), _cas("FICTIF-L2-002", zs="Bunia", contacts=[], ipc=[], actions=[], contacts_dhis2_listes=None)]
    cc = CO.command_center(cases, REF)
    assert [k["t"] for k in cc["kpis"]][:2] == ["Cas (fiches)", "Complétude des fiches"]
    zones = {z["zs"]: z for z in cc["zones"]}
    assert zones["Bunia"]["cells"][1]["txt"] == "ND"               # aucun contact : jamais 0 %
    assert zones["Watsa"]["cells"][2]["txt"] == "50 %"             # 1 site décontaminé sur 2
    assert zones["Watsa"]["cells"][4]["ton"] == "re"               # isolement 3 j après confirmation
    ca = {k: items for k, _l, items in CO.centre_actions(cases, REF)["colonnes"]}
    assert [a["texte"] for a in ca["retard"]] == ["Lister les contacts"]
    assert [a["texte"] for a in ca["avalider"]] == ["Décontaminer le domicile"]
    assert [a["texte"] for a in ca["validee"]] == ["Vérifier l'éligibilité vaccinale"]
    assert [a["texte"] for a in ca["encours"]] == ["Évaluer les passages aux PoC"]
    only = CO.centre_actions(cases, REF, pilier="PCI")["colonnes"]
    assert sum(len(i) for _k, _l, i in only) == 1


def test_pages_piliers():
    cases = [_cas(), _cas("FICTIF-L2-002", zs="Bunia", contacts_dhis2_listes=67)]
    g = CO.goulots(cases)
    assert any(s["titre"] == "Fiches hors délai" and s["lignes"] for s in g["sections"])
    conc = CO.concordance(cases)
    det = [s for s in conc["sections"] if s["titre"] == "Détail par cas index"][0]
    statuts = [r["cells"][-1][0] for r in det["lignes"]]
    assert "Sous-listing potentiel" in statuts and "Concordance numérique" in statuts
    v = CO.vaccination(cases, REF)
    assert v["kpis"][2]["v"] == "68" and "Refus" in json.dumps(v, ensure_ascii=False, default=str)
    psy = json.dumps(CO.psychosocial(cases), ensure_ascii=False)
    assert "FICTIF-L2" not in psy and "Besoin identifié" in psy     # agrégats seulement
    s = CO.services(cases)
    assert s["kpis"][0]["v"] == "2"
    assert CO.pci_delais(cases)["delai_median"] == 2


def test_poe_saisie(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path))
    from core import poe
    r = poe.ajouter({"date": REF.isoformat(), "point": "PoC A", "voyageurs": "100", "screenes": "90", "alertes": "", "investiguees": ""}, "x")
    assert r["alertes"] is None                                  # vide = inconnu, jamais 0
    with pytest.raises(ValueError):
        poe.ajouter({"date": REF.isoformat(), "point": "PoC A", "voyageurs": "10", "screenes": "20"}, "x")
    p = CO.poe_poc(poe.charger(), [_cas()], REF)
    assert p["kpis"][2]["v"] == "90 %" and p["kpis"][4]["v"] == "1"
    assert poe.supprimer(r["id"]) and poe.charger() == []


def test_web_lots2_5(app):  # noqa: F811
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123",
                                  "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    case = c.get(f"/api/cas/{cid}").get_json()["case"]
    case.update(entrainement=False, code_cas="RDC-L2-26-001", suivi_nouveau_ne="À vérifier", besoin_psychosocial="Soutien en cours")
    case["actions"].append(Action(texte="Décontaminer le véhicule", statut="Fait", pilier="PCI").model_dump(mode="json"))
    hdr = {"X-CSRF": tok, "Content-Type": "application/json"}
    assert c.put(f"/api/cas/{cid}", data=json.dumps(case), headers=hdr).status_code == 200
    page = c.get(f"/cas/{cid}").get_data(as_text=True)
    assert "9. Besoins" in page and 'id="p-besoins"' in page and "Parcours clinique" in page
    assert "PARCOURS CLINIQUE" in c.get(f"/cas/{cid}/apercu/clin").get_data(as_text=True)
    assert c.get(f"/cas/{cid}/telecharger/svg?visuel=clin").status_code == 200
    sch = c.get("/api/schema").get_json()
    assert "Documenté" in sch["choices"]["besoin"] and any(col["key"] == "nb_trajets" for col in sch["tables"]["events"])
    tb = c.get("/tableau-de-bord?debut=2026-01-01").get_data(as_text=True)
    assert "Command center" in tb and "Centre des actions" in tb and "Faite · à valider" in tb and "Décontaminer le véhicule" in tb
    for url in ("/analyse/goulots", "/analyse/concordance", "/riposte/vaccination", "/riposte/psychosocial",
                "/riposte/services-essentiels", "/riposte/poe-poc", "/pci"):
        r = c.get(url)
        assert r.status_code == 200, url
    assert "RDC-L2-26-001" not in c.get("/riposte/psychosocial").get_data(as_text=True)
    assert "RDC-L2-26-001" in c.get("/riposte/services-essentiels").get_data(as_text=True)
    assert "Identifié" in c.get("/pci").get_data(as_text=True)
    menu = c.get("/").get_data(as_text=True)
    for lien in ("/analyse/goulots", "/analyse/concordance", "/riposte/poe-poc", "/riposte/psychosocial"):
        assert lien in menu
    r = c.post("/riposte/poe-poc", data={"csrf": tok, "action": "ajouter", "date": date.today().isoformat(), "point": "PoC Test",
                                          "voyageurs": "200", "screenes": "150"})
    assert r.status_code == 302
    assert "PoC Test" in c.get("/riposte/poe-poc").get_data(as_text=True)
    assert c.post("/riposte/poe-poc", data={"action": "ajouter"}).status_code == 400        # sans jeton CSRF


def test_acces_pages_piliers(app):  # noqa: F811
    from core.storage import Store  # noqa: F401
    from core.users import Users
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123",
                                  "password2": "Secret123"})
    us = Users(app.store)
    us.create("agent.z", "Secret123", role="agent")
    us.create("partenaire.z", "Secret123", role="partenaire")
    for u in ("agent.z", "partenaire.z"):
        c2 = app.test_client()
        t0 = _csrf(c2.get("/connexion").get_data(as_text=True))
        c2.post("/connexion", data={"csrf": t0, "username": u, "password": "Secret123"})
        for url in ("/analyse/goulots", "/analyse/concordance", "/riposte/poe-poc", "/riposte/psychosocial"):
            assert c2.get(url).status_code == 403, (u, url)


def test_word_aller_retour_lots2_5(tmp_path):
    from core import modele_narratif as MN
    f = tmp_path / "fiche.docx"
    MN.generer_docx(f, _cas())
    b = MN.lire_modele(f).case
    assert (b.date_premiere_consultation, b.suivi_nouveau_ne, b.besoin_psychosocial) == (date(2026, 11, 12), "À vérifier", "Besoin identifié")
    assert [(e.nb_trajets, e.poe_poc) for e in b.events] == [(5, "PoC Bunia-Komanda")]
    assert (b.ipc[0].identifie_le, b.ipc[0].preuve) == (date(2026, 11, 12), "photo")
    assert (b.contacts[0].eligibles, b.contacts[0].motif_non_vaccination) == (50, "Refus")
