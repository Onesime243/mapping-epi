"""Remarques de la présentation : comptes (adminone, suppressions), catégories des ZS, délais, pyramide, État."""
import re
from datetime import date

import pytest

from core import indicateurs as IND, pyramide
from core.models import Case
from core.storage import Store
from core.users import Users

PWD = "Secret2026"


def test_bunia_23_aires(tmp_path):
    p = pyramide.Pyramide(perso=tmp_path / "perso.csv")
    aires = p.aires("Ituri", "Bunia")
    assert len(aires) == 23 and {"Betokomba", "Kigonze", "Rwambuzi"} <= set(aires)


def test_categories_et_foyers(tmp_path, monkeypatch):
    ref = date(2026, 11, 11)
    cs = [Case(province="Ituri", zs="Bunia", aire_sante="Nzere", date_notification=date(2026, 11, 10)),
          Case(province="Ituri", zs="Bunia", aire_sante="Kigonze", date_notification=date(2026, 11, 11)),
          Case(province="Ituri", zs="Mambasa", aire_sante="Biakato", date_notification=date(2026, 10, 20)),
          Case(province="Ituri", zs="Mambasa", aire_sante="Biakato", date_notification=date(2026, 8, 1)),
          Case(province="Ituri", zs="Komanda", date_confirmation=date(2026, 9, 1))]
    z = {x.zs: x for x in IND.zones(cs, ref)}
    assert z["Bunia"].cat["num"] == 1 and z["Bunia"].n7 == 2
    assert z["Mambasa"].cat["num"] == 3 and z["Mambasa"].jours == 22
    assert z["Komanda"].cat["num"] == 4
    al = IND.alertes_foyers(cs)
    textes = [(a.lieu, a.texte) for a in al]
    assert any(l == "Mambasa" and "reprise après 80 jours" in t for l, t in textes)
    assert any(l == "Kigonze" for l, _t in textes)                         # nouvelle aire touchée


def test_delais_et_incubation():
    src = Case(code_cas="S-1", debut_symptomes=date(2026, 10, 1))
    a = Case(code_cas="A-1", debut_symptomes=date(2026, 10, 12), date_notification=date(2026, 10, 15),
             date_confirmation=date(2026, 10, 16), contact_connu="Contact connu", id_cas_source="s-1",
             date_contact_source=date(2026, 10, 3))
    st = {s.nom: s for s in IND.delais([src, a])}
    assert st["Incubation observée"].valeurs == [9]
    assert st["Intervalle sériel"].valeurs == [11]
    assert st["Début des symptômes → notification"].valeurs == [3]
    assert st["Début des symptômes → notification"].exclus == 1


def test_comptes_adminone_et_historique(tmp_path):
    us = Users(Store(tmp_path / "db.sqlite"))
    one = us.create("adminone", PWD, "Principal", "admin")
    adm2 = us.create("admin2", PWD, "Autre admin", "admin")
    nat = us.create("nat", PWD, "National", niveau="national")
    us.create("as.x", PWD, "Agent")
    with pytest.raises(ValueError, match="adminone"):
        us.delete(adm2, "adminone")                     # un autre administrateur ne peut pas supprimer adminone
    assert Users.protege(adm2, "adminone") and not Users.protege(one, "adminone")
    with pytest.raises(ValueError):
        us.delete(nat, "admin2")                        # le niveau national ne supprime pas un administrateur
    us.delete(nat, "as.x", "doublon", 3)                # le niveau national supprime un compte agent
    us.delete(one, "admin2", "départ")                  # adminone supprime n'importe quel compte
    assert us.get("as.x") is None and us.get("admin2") is None
    h = us.suppressions()
    assert [(x["username"], x["auteur"], x["fiches"], x["motif"]) for x in h] == [
        ("admin2", "adminone", 0, "départ"), ("as.x", "nat", 3, "doublon")]
    with pytest.raises(ValueError):
        us.delete(one, "adminone")                      # pas de suppression de son propre compte


def test_excel_ancien_libelle_issue(tmp_path, demo):
    from openpyxl import load_workbook
    from core import storage
    f = tmp_path / "c.xlsx"
    demo.issue = "Vivant"
    storage.export_excel(demo, f)
    wb = load_workbook(f)
    for row in wb["Cas"].iter_rows():
        if row[0].value == "État":
            row[0].value = "Issue"                      # fichier rempli avant le renommage
    wb.save(f)
    assert storage.import_excel(f).issue == "Vivant"


def _login(app, u):
    c = app.test_client()
    tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/connexion").get_data(as_text=True)).group(1)
    c.post("/connexion", data={"csrf": tok, "username": u, "password": PWD})
    tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/cas").get_data(as_text=True)).group(1)
    return c, tok


def test_web_suppression_et_zones(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "d"))
    pyramide._SINGLETON = None
    from web.server import create_app
    st = Store(tmp_path / "d" / "db.sqlite")
    us = Users(st)
    us.create("adminone", PWD, "Principal", "admin")
    us.create("admin2", PWD, "Autre", "admin")
    us.create("nat", PWD, "National", niveau="national")
    us.create("as.y", PWD, "Agent Y")
    st.save(Case(code_cas="X-1", province="Ituri", zs="Bunia", date_notification=date(2026, 11, 10),
                 debut_symptomes=date(2026, 11, 6)), owner="as.y")
    app = create_app(st)
    app.testing = True
    a2, t2 = _login(app, "admin2")
    html = a2.get("/utilisateurs").get_data(as_text=True)
    assert "compte principal" in html
    r = a2.post("/utilisateurs", data={"csrf": t2, "action": "reset", "username": "adminone"})
    assert "Seul le compte" in r.get_data(as_text=True)
    n, tn = _login(app, "nat")
    assert n.get("/utilisateurs").status_code == 200
    r = n.post("/utilisateurs", data={"csrf": tn, "action": "create", "username": "zz.zz", "nom": "Z"})
    assert "réservée aux administrateurs" in r.get_data(as_text=True) and app.users.get("zz.zz") is None
    n.post("/utilisateurs", data={"csrf": tn, "action": "delete", "username": "as.y", "motif": "test"})
    assert app.users.get("as.y") is None
    html = n.get("/utilisateurs").get_data(as_text=True)
    assert "Historique des suppressions" in html and "as.y" in html
    html = n.get("/analyse/zones?ref=2026-11-11").get_data(as_text=True)
    assert "Bunia" in html and "Cat. 1" in html and "premier cas notifié" in html
    a1, _ = _login(app, "adminone")
    assert a1.get("/utilisateurs").status_code == 200
