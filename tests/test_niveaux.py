"""Niveaux des comptes (national / province / zone / aire), chaînes de transmission, lieux communs."""
import re
from datetime import date, timedelta

import pytest

from core import links, pyramide
from core.access import Access
from core.models import Case, Event
from core.storage import Store
from core.users import Users
from render import chains, common_places

PWD = "Secret2026"


def _case(code, prov, zs, aire, j0=None, events=(), source="", contact="Inconnu"):
    # champs obligatoires remplis (sinon la fiche modifiée resterait en brouillon)
    return Case(code_cas=code, province=prov, zs=zs, aire_sante=aire, debut_symptomes=j0, events=list(events),
                id_cas_source=source, contact_connu=contact, sexe="M", age=30, issue="En traitement",
                date_confirmation=(j0 + timedelta(days=3)) if j0 else date(2026, 11, 1))


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "donnees"))
    pyramide._SINGLETON = None
    store = Store(tmp_path / "donnees" / "mapping_epi.sqlite")
    us = Users(store)
    us.create("admin", PWD, "Admin", "admin")
    us.create("nat", PWD, "National", niveau="national")
    us.create("prov.bu", PWD, "DPS Bas-Uele", niveau="province", province="Bas-Uele")
    us.create("prov.it", PWD, "DPS Ituri", niveau="province", province="ituri")         # orthographe corrigée
    us.create("zs.ganga", PWD, "BCZ Ganga", niveau="zone", province="Bas-Uele", zs="Ganga")
    us.create("as.dingila", PWD, "AS Dingila", niveau="aire", province="Bas-Uele", zs="Ganga", aire="Dingila")
    us.create("as.bondo", PWD, "AS Bondo", niveau="aire", province="Bas-Uele", zs="Bondo", aire="Bondo")
    a = _case("BU-GAN-001", "Bas-Uele", "Ganga", "Dingila", date(2026, 8, 18),
              [Event(date_debut=date(2026, 8, 20), lieu="HGR Ganga", type="Hospitalisation")])
    b = _case("BU-GAN-002", "Bas-Uele", "Ganga", "Mabodho", date(2026, 9, 1),
              [Event(date_debut=date(2026, 8, 21), lieu="hgr  ganga (pavillon)", type="Soins / consultation")],
              source="bu-gan-001", contact="Contact connu suivi")
    c = _case("BU-BON-001", "Bas-Uele", "Bondo", "Bondo", date(2026, 9, 10), source="BU-GAN-002",
              contact="Contact connu")
    d = _case("IT-MAN-001", "Ituri", "Mandima", "Babombi", date(2026, 10, 28), source="NK-BEN-099")
    store.save(a, owner="as.dingila")
    store.save(b, owner="zs.ganga")
    store.save(c, owner="as.bondo")
    store.save(d, owner="")                     # fiche saisie sur le poste de bureau
    return store, us, {"a": a, "b": b, "c": c, "d": d}


def _acc(us, name):
    return Access(us.get(name), {u.username: u for u in us.list()})


def _visible(store, us, name):
    acc = _acc(us, name)
    return {c.id for _cid, _u, owner, c in store.rows_full() if acc.can_view(c, owner or "")}


def test_scope_validation(world):
    _store, us, _ = world
    assert us.get("prov.it").province == "Ituri"
    with pytest.raises(ValueError):
        us.create("zs.sans", PWD, niveau="zone", province="Bas-Uele")       # ZS obligatoire
    with pytest.raises(ValueError):
        us.create("prov.sans", PWD, niveau="province")                       # province obligatoire
    assert us.create("vieux", PWD, zs="Ganga").niveau == "aire"              # comptes d'avant : leurs cas seulement


def test_visibility_by_level(world):
    store, us, k = world
    ids = {n: v.id for n, v in k.items()}
    assert _visible(store, us, "as.dingila") == {ids["a"]}
    assert _visible(store, us, "zs.ganga") == {ids["a"], ids["b"]}
    assert _visible(store, us, "prov.bu") == {ids["a"], ids["b"], ids["c"]}
    assert _visible(store, us, "prov.it") == {ids["d"]}
    assert _visible(store, us, "nat") == set(ids.values())
    assert _visible(store, us, "admin") == set(ids.values())


def test_edit_rights(world):
    _store, us, k = world
    zs, prov, nat, adm = (_acc(us, n) for n in ("zs.ganga", "prov.bu", "nat", "admin"))
    assert zs.can_edit(k["a"], "as.dingila")            # la ZS corrige les fiches de ses AS
    assert not zs.can_edit(k["c"], "as.bondo")          # pas celles d'une autre ZS
    assert not prov.can_edit(k["a"], "as.dingila")      # la province consulte seulement
    assert not nat.can_edit(k["d"], "")
    assert adm.can_edit(k["d"], "")
    assert not zs.can_delete(k["a"], "as.dingila") and _acc(us, "as.dingila").can_delete(k["a"], "as.dingila")


def test_chains_and_common_places(world):
    store, _us, k = world
    cases = store.all_cases()
    ch = links.build_chains(cases)
    roots = {r.key: r for r in ch.roots}
    assert k["a"].id in roots and "src:nkben099" in roots          # source hors périmètre (autre province)
    child = roots[k["a"].id].children[0]
    assert child.case.code_cas == "BU-GAN-002" and child.lien == "Contact connu suivi"
    assert child.children[0].gen == 2 and child.children[0].case.code_cas == "BU-BON-001"
    assert not ch.isolated
    assert links.serial_interval(k["a"], k["b"]) == 14
    shared = links.shared_places(cases)
    assert len(shared) == 1 and shared[0].name == "HGR Ganga" and len(shared[0].cases) == 2
    # a contagieux à l'HGR le 20/08, b dans sa fenêtre d'exposition le 21/08
    assert [(x.code_cas, y.code_cas) for x, y in shared[0].pistes] == [("BU-GAN-001", "BU-GAN-002")]
    for svg in (chains.render_svg(cases), chains.render_svg(cases, k["b"]), common_places.render_svg(cases),
                common_places.render_svg(cases, k["a"]), chains.render_svg([]), common_places.render_svg([])):
        assert svg.startswith("<svg") and svg.endswith("</svg>") and "—" not in svg


def test_chain_loop_and_duplicates():
    a, b = Case(code_cas="X-1", id_cas_source="X-2"), Case(code_cas="X-2", id_cas_source="X-1")
    ch = links.build_chains([a, b])
    assert ch.ignored and len(ch.roots) == 1
    c1, c2, d = Case(code_cas="Y-1"), Case(code_cas="Y-1"), Case(code_cas="Y-2", id_cas_source="Y-1")
    assert links.build_chains([c1, c2, d]).ignored                 # ID en double : lien non deviné


# ---------------------------------------------------------------------------- web
def _login(app, u):
    c = app.test_client()
    tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/connexion").get_data(as_text=True)).group(1)
    c.post("/connexion", data={"csrf": tok, "username": u, "password": PWD})
    tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/cas").get_data(as_text=True)).group(1)
    return c, tok


def test_web_levels(world):
    store, _us, k = world
    from web.server import create_app
    app = create_app(store)
    app.testing = True

    def put(cl, tok, case):
        return cl.put(f"/api/cas/{case.id}", data=case.model_dump_json(),
                      headers={"X-CSRF": tok, "Content-Type": "application/json"})

    zs, tz = _login(app, "zs.ganga")
    assert put(zs, tz, k["a"]).status_code == 200                      # correction d'une fiche AS
    assert zs.get(f"/cas/{k['c'].id}").status_code == 403              # autre ZS
    html = zs.get("/cas?tri=j0&ordre=asc").get_data(as_text=True)
    assert html.index("BU-GAN-001") < html.index("BU-GAN-002") and "BU-BON-001" not in html
    html = zs.get("/cas?tri=j0&ordre=desc").get_data(as_text=True)
    assert html.index("BU-GAN-002") < html.index("BU-GAN-001")

    prov, tp = _login(app, "prov.bu")
    r = prov.get(f"/cas/{k['a'].id}")
    assert r.status_code == 200 and "Lecture seule" in r.get_data(as_text=True)
    assert put(prov, tp, k["a"]).status_code == 403
    assert prov.get(f"/cas/{k['d'].id}").status_code == 403            # autre province
    assert "BU-BON-001" in prov.get("/cas?zs=Bondo").get_data(as_text=True)
    html = prov.get("/analyse/lieux/zs?province=Bas-Uele&zs=Ganga").get_data(as_text=True)
    assert "HGR Ganga" in html
    r = prov.get("/analyse/lieux/zs/communs?province=Bas-Uele&zs=Ganga")
    assert r.status_code == 200 and "Transmission possible" in r.get_data(as_text=True)

    asd, _ = _login(app, "as.dingila")
    assert asd.get(f"/cas/{k['b'].id}").status_code == 403

    nat, _ = _login(app, "nat")
    assert nat.get("/analyse/chaines").status_code == 200
    svg = nat.get("/analyse/chaines/apercu?province=Bas-Uele").get_data(as_text=True)
    assert "BU-GAN-002" in svg and "IT-MAN-001" not in svg
    assert nat.get("/analyse/chaines/chaines.svg").status_code == 200
    for key in ("chains", "common"):
        assert nat.get(f"/cas/{k['b'].id}/apercu/{key}").status_code == 200
        assert nat.get(f"/cas/{k['b'].id}/telecharger/svg?visuel={key}").status_code == 200

    adm, ta = _login(app, "admin")
    r = adm.post("/utilisateurs", data={"csrf": ta, "action": "scope", "username": "as.bondo", "niveau": "zone",
                                        "province": "Bas-Uele", "zs": "Bondo"})
    assert r.status_code == 200 and app.users.get("as.bondo").niveau == "zone"
    assert "Zone de santé" in adm.get("/utilisateurs").get_data(as_text=True)
