"""Nombres impossibles (téléphone tapé dans « Nombre ») : ni affichés, ni additionnés, ni conservés ; signalés."""
import json
import re

import pytest

from core import coordination as CO
from core import langue, rules, surveillance as SUR
from core.models import Case, ContactGroup, Place
from tests.test_web import _csrf, _login, app  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def _fr():
    langue.definir("fr")
    yield
    langue.definir("fr")


def _cas():
    return Case(code_cas="RDC-ITU-BUN-26-1", zs="Bunia", contacts=[
        ContactGroup(categorie="Famille", nombre=4948027843, suivis=3, vaccines=2),
        ContactGroup(categorie="Voisins", nombre=12, suivis=10, vaccines=-5)],
        places=[Place(nom="Marché", nombre=243810000000)])


def test_valeur_impossible_supprimee_et_signalee():
    c = _cas()
    g = c.contacts[0]
    assert g.nombre is None and g.aberrants == ["nombre"] and g.suivis == 3
    assert c.contacts[1].vaccines is None and c.places[0].nombre is None
    assert "4948027843" not in c.model_dump_json()                  # un téléphone ne reste pas dans l'outil
    msgs = [i.message for i in rules.check_consistency(c) if i.niveau == "erreur"]
    assert any("Famille" in m and "nombre impossible dans Listés" in m for m in msgs)
    assert any("Marché" in m for m in msgs)
    v = CO.vaccination([c])
    assert v["kpis"][0]["v"] == "12"                                 # seule la valeur plausible est comptée
    ressaisi = Case.model_validate({**c.model_dump(mode="json"), "contacts": [{**c.contacts[0].model_dump(mode="json"), "nombre": 40}]})
    assert ressaisi.contacts[0].nombre == 40 and ressaisi.contacts[0].aberrants == []


def test_milliers():
    assert CO.milliers("12450") == "12 450" and CO.milliers("3 / 9") == "3 / 9" and CO.milliers("84,5 %") == "84,5 %"
    assert SUR.texte(1200) == "1 200"
    with langue.utiliser("en"):
        assert CO.milliers("12450") == "12,450"


def test_onglets_chronologie_et_clinique_avant_plein_ecran(app):  # noqa: F811
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123", "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    page = c.get(f"/cas/{cid}").get_data(as_text=True)
    ordre = re.findall(r'data-v="(\w+)"', page.split('id="vtabs"')[1].split("</div>")[0])
    assert ordre[-2:] == ["chrono", "clin"] and ordre[0] == "mapping"
    bloc = page.split('id="vtabs"')[1]
    assert bloc.index('data-v="clin"') < bloc.index('id="pleinEcran"')
    case = c.get(f"/api/cas/{cid}").get_json()["case"]
    case["contacts"][0]["nombre"] = 4948027843
    assert c.put(f"/api/cas/{cid}", data=json.dumps(case), headers={"X-CSRF": tok, "Content-Type": "application/json"}).status_code == 200
    d = c.get(f"/api/cas/{cid}").get_json()
    assert d["case"]["contacts"][0]["nombre"] is None and "4948027843" not in json.dumps(d)
    assert "4948027843" not in c.get("/surveillance").get_data(as_text=True)
