"""Rapprochement Mapping Épi × DHIS2 : ID du mapping retrouvé dans la liste linéaire, contacts comptés, écart.
Aucun appel réseau : les réponses de l'API sont simulées."""
import io
import json

import pytest
from openpyxl import load_workbook

from core import dhis2, langue
from core.models import Case, ContactGroup
from tests.test_web import _csrf, _login, app  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "donnees"))
    monkeypatch.delenv("DHIS2_TOKEN", raising=False)
    dhis2._CACHE.clear()
    langue.definir("fr")
    yield
    dhis2._CACHE.clear()


def _cas(code, *nombres):
    return Case(code_cas=code, zs="Bunia", province="Ituri", contacts=[ContactGroup(categorie=f"G{i}", nombre=n) for i, n in enumerate(nombres)])


def test_cle_epid():
    assert dhis2.cle_epid("RDC-ITU-RWA-26-001058-MVE") == dhis2.cle_epid(" rdc-itu-rwa-26-1058 ") == "RDC-ITU-RWA-26-1058"
    assert dhis2.cle_epid("") == "" and dhis2.cle_epid(None) == ""


def _faux_api(monkeypatch):
    ll = [["RDC-ITU-BUN-26-000101-MVE", "CC"], ["RDC-ITU-BUN-26-000101-MVE", "NC"], ["RDC-ITU-BUN-26-000202-MVE", "CC"],
          ["RDC-ITU-MAM-26-000303-MVE", ""]]
    ct = [["t1", "RDC-ITU-BUN-26-000101-MVE"], ["t2", "RDC-ITU-BUN-26-000101-MVE"], ["t2", "RDC-ITU-BUN-26-000101-MVE"],
          ["t3", "RDC-ITU-BUN-26-000202-MVE"]] + [[f"x{i}", "RDC-ITU-BUN-26-000202-MVE"] for i in range(11)]
    appels = []

    def get(path, params, tok):
        appels.append((path, dict(params)))
        assert tok == "jeton-test"
        h = dict(params)["headers"]
        assert "GK0zoBqrpAx" not in h and "luaR4AtJPBC" not in h          # jamais les noms
        return {"rows": ll if dhis2.PROG_LL in path else ct}
    monkeypatch.setattr(dhis2, "_get", get)
    return appels


def test_synchronisation_et_rapprochement(monkeypatch):
    _faux_api(monkeypatch)
    d = dhis2.synchroniser_api("jeton-test")
    assert d["ll"]["RDC-ITU-BUN-26-101"] == "CC"                     # classification la plus forte gardée
    assert d["contacts"] == {"RDC-ITU-BUN-26-101": 2, "RDC-ITU-BUN-26-202": 12} and d["n_contacts"] == 14
    assert "jeton-test" not in dhis2._fichier().read_text()            # le jeton n'est jamais enregistré
    r = dhis2.rapprochement(_cas("RDC-ITU-BUN-26-101", 5, 3))
    assert (r["trouve"], r["classif"], r["mapping"], r["dhis2"], r["difference"]) == (True, "Confirmé", 8, 2, 6)
    r = dhis2.rapprochement(_cas("RDC-ITU-MAM-26-303", 4))
    assert (r["trouve"], r["dhis2"], r["difference"]) == (True, 0, 4)    # retrouvé, aucun contact enregistré : vrai 0
    r = dhis2.rapprochement(_cas("RDC-ITU-XXX-26-999", 4))
    assert (r["trouve"], r["dhis2"], r["difference"]) == (False, None, None)
    r = dhis2.rapprochement(Case(code_cas="RDC-ITU-BUN-26-202"))
    assert (r["mapping"], r["dhis2"], r["difference"]) == (None, 12, None)   # contacts du mapping inconnus : pas d'écart


def test_sans_synchronisation_nombre_saisi():
    c = _cas("RDC-ITU-BUN-26-101", 10)
    c.contacts_dhis2_listes = 7
    r = dhis2.rapprochement(c)
    assert (r["trouve"], r["dhis2"], r["difference"], r["source"]) == (None, 7, 3, "saisi")


def test_import_fichiers(tmp_path):
    ll = tmp_path / "LINELIST.csv"
    ll.write_text("Organisation unit name hierarchy,MVE-N-Numéro d’identification de l’alerte,MVE - Nom, post nom et prénom du cas ,"
                  "MVE - Classification finale du cas \nRDC,RDC-ITU-BUN-26-000101-MVE,NOM CACHE,CC\n".replace(
                      "MVE - Nom, post nom", '"MVE - Nom, post nom').replace("cas ,", 'cas ",', 1), encoding="utf-8")
    ct = tmp_path / "SUIVI.csv"
    ct.write_text("UID visite,UID contact,MVE - Numéro Epid - Alerte MVE,002 MVE-FS-Nom et prénom du contact\n"
                  "v1,c1,RDC-ITU-BUN-26-000101-MVE,X\nv2,c1,RDC-ITU-BUN-26-000101-MVE,X\nv3,c2,RDC-ITU-BUN-26-000101-MVE,Y\n", encoding="utf-8")
    assert dhis2.type_fichier(ll) == "linelist" and dhis2.type_fichier(ct) == "contacts"
    d = dhis2.importer_fichiers([ll, ct])
    assert d["ll"] == {"RDC-ITU-BUN-26-101": "CC"} and d["contacts"] == {"RDC-ITU-BUN-26-101": 2}
    assert "NOM CACHE" not in dhis2._fichier().read_text()


def test_web_concordance_dhis2(app, monkeypatch):  # noqa: F811
    _faux_api(monkeypatch)
    dhis2.synchroniser_api("jeton-test")
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123", "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    for code, n in (("RDC-ITU-BUN-26-0101", 8), ("RDC-ITU-ZZZ-26-0999", 3)):
        cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
        case = c.get(f"/api/cas/{cid}").get_json()["case"]
        case.update(entrainement=False, code_cas=code, contacts=[ContactGroup(categorie="Famille", nombre=n).model_dump(mode="json")])
        assert c.put(f"/api/cas/{cid}", data=json.dumps(case), headers={"X-CSRF": tok, "Content-Type": "application/json"}).status_code == 200
    page = c.get("/analyse/concordance").get_data(as_text=True)
    for t in ("Contacts déclarés dans le mapping", "Contacts retrouvés dans DHIS2", "Différence (mapping − DHIS2)",
              "Introuvable dans la linelist DHIS2", "+6", "Téléverser LINELIST"):
        assert t in page, t
    assert "Synchroniser avec DHIS2 maintenant" not in page           # pas de jeton sur ce serveur de test
    x = c.get("/analyse/concordance.xlsx")
    ws = load_workbook(io.BytesIO(x.data)).worksheets[0]
    lignes = {r[0]: r for r in ws.iter_rows(min_row=3, values_only=True)}
    assert lignes["RDC-ITU-BUN-26-0101"][4:9] == ("Oui", "Confirmé", 8, 2, 6)
    assert lignes["RDC-ITU-ZZZ-26-0999"][4] == "Non" and lignes["RDC-ITU-ZZZ-26-0999"][7] is None
    lc = load_workbook(io.BytesIO(c.get("/donnees/liste-cas.xlsx").data)).worksheets[0]
    entetes = [h for h in next(lc.iter_rows(min_row=2, max_row=2, values_only=True))]
    assert "Contacts retrouvés dans DHIS2" in entetes and "Différence contacts (mapping − DHIS2)" in entetes
    assert c.post("/analyse/concordance/synchroniser", data={"csrf": tok}).status_code == 302
