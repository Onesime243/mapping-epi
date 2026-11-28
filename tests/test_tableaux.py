"""Les 12 tableaux de bord (Tableau de bord ▾) : calcul en direct, aucun identifiant dans la page, droits d'accès."""
import json
import re
from datetime import date, timedelta

import pytest

from core import langue
from core import tableaux as TBX
from core.models import Case, ContactGroup, Event
from tests.test_lots2_5 import _cas
from tests.test_web import _csrf, _login, app  # noqa: F401  (fixture)

REF = date(2026, 11, 27)


@pytest.fixture(autouse=True)
def _fr():
    langue.definir("fr")
    yield
    langue.definir("fr")


def _jeu():
    cs = [_cas(code=f"RDC-ITU-BUN-26-{i}", zs=z, date_confirmation=REF - timedelta(days=d))
          for i, (z, d) in enumerate([("Bunia", 2), ("Beni", 5), ("Bunia", 10), ("Mambasa", 20), ("Beni", 1)])]
    cs[1].id_cas_source = "RDC-ITU-BUN-26-0"
    cs[2].id_cas_source = "rdc-itu-bun-26-000"                      # même EPID écrit autrement
    cs[3].issue, cs[3].date_deces = "Décès", REF - timedelta(days=3)
    cs[4].contacts = [ContactGroup(categorie="Famille", nombre=4948027843)]   # téléphone saisi : écarté
    return cs


def test_construire():
    D = TBX.construire(_jeu(), REF)
    assert D["n"] == 5 and D["kpi"]["deces"] == 1 and D["kpi"]["zs"] == 3
    assert D["kpi"]["cas7"] == 3 and len(D["cas_sem"]) == 13 and len(D["cas_j"]) == 28
    assert D["chaines"][0]["n"] == 3 and D["src_base"] == 2              # chaîne reconstituée malgré l'écriture
    assert D["ct"]["listes"] < 10000 and D["qualite"]["nombre_impossible"] == 1
    assert [z["zs"] for z in D["zs"]][:2] == ["Bunia", "Beni"]
    assert "RDC-ITU" not in json.dumps(D, default=str)                    # aucun identifiant de cas
    assert TBX.construire([], REF) == {"n": 0, "ref": REF.isoformat()}


def test_delais_aberrants_ecartes():
    c = Case(code_cas="X", debut_symptomes=date(2021, 1, 1), date_confirmation=REF)
    D = TBX.construire([c], REF)
    assert D["kpi"]["d_conf"] is None and D["qualite"]["date_aberrante"] == 1 and D["qualite"]["delai_aberrant"] == 1


def test_pages(app):  # noqa: F811
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123", "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    for x in _jeu():
        x.entrainement = False
        app.store.save(x, owner="admin")
    for k in TBX.CLES:
        r = c.get(f"/tableau-de-bord/{k}")
        assert r.status_code == 200, k
        h = r.get_data(as_text=True)
        assert "window.TDB =" in h and "tableaux.js" in h and 'class="it on"' in h
        donnees = h.split("window.TDB =")[1].split("</script>")[0]
        assert "RDC-ITU-BUN-26" not in donnees, k                         # jamais d'ID dans les données de la page
    assert c.get("/tableau-de-bord/inconnu").status_code == 404
    h = c.get("/tableau-de-bord/geo?province=Ituri&debut=2026-11-01&fin=2026-11-27").get_data(as_text=True)
    d = json.loads(re.search(r"window\.TDB = (\{.*?\}); window\.TDB_CARTES", h, re.S).group(1))
    assert d["n"] == 5 and d["prov"] == [["Ituri", 5]]
    menu = c.get("/").get_data(as_text=True)
    assert "/tableau-de-bord/strategique" in menu and "/tableau-de-bord/qualite" in menu and "Vue d&#39;ensemble et alertes" in menu
    assert c.get("/tableau-de-bord").status_code == 200                  # l'ancien tableau de bord reste disponible


def test_acces(app):  # noqa: F811
    from core.users import Users
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123", "password2": "Secret123"})
    us = Users(app.store)
    us.create("agent.t", "Secret123", role="agent")
    us.create("partenaire.t", "Secret123", role="partenaire")
    for u in ("agent.t", "partenaire.t"):
        c2 = app.test_client()
        t0 = _csrf(c2.get("/connexion").get_data(as_text=True))
        c2.post("/connexion", data={"csrf": t0, "username": u, "password": "Secret123"})
        assert c2.get("/tableau-de-bord/strategique").status_code == 403, u
