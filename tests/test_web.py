import json
import re

import pytest

from core import pyramide
from core.storage import Store
from core.users import Users, check_password, hash_password


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "donnees"))
    pyramide._SINGLETON = None
    from web.server import create_app
    a = create_app(Store(tmp_path / "donnees" / "mapping_epi.sqlite"))
    a.testing = True
    return a


def _csrf(html):
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def _login(c, u, p):
    tok = _csrf(c.get("/connexion").get_data(as_text=True))
    c.post("/connexion", data={"csrf": tok, "username": u, "password": p})
    return _csrf(c.get("/cas").get_data(as_text=True))


def test_password_hashing():
    h = hash_password("Secret123")
    assert "Secret123" not in h and check_password("Secret123", h) and not check_password("x", h)


def test_user_rules(tmp_path):
    us = Users(Store(tmp_path / "db.sqlite"))
    with pytest.raises(ValueError):
        us.create("ab", "Secret123")
    with pytest.raises(ValueError):
        us.create("agent", "court")
    us.create("chef", "Secret123", role="admin")
    with pytest.raises(ValueError):
        us.update("chef", actif=False)          # dernier administrateur
    assert us.authenticate("chef", "Secret123") and not us.authenticate("chef", "mauvais1")


def test_pyramide(tmp_path):
    p = pyramide.Pyramide(perso=tmp_path / "perso.csv")
    assert len(p.provinces()) == 26
    assert "Ganga" in p.zones("Bas-Uele")
    assert "Dingila" in p.aires("Bas-Uele", "Ganga")
    assert p.province_of("Ganga") == "Bas-Uele"
    assert len(p.zones()) > 500 and len(p.aires()) > 5000
    assert p.remember("Bas-Uele", "Ganga", "Aire test")
    assert "Aire test" in pyramide.Pyramide(perso=tmp_path / "perso.csv").aires("Bas-Uele", "Ganga")


def test_web_flow(app):
    c = app.test_client()
    assert c.get("/").headers["Location"].endswith("/installation")
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123",
                                  "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    c.post("/utilisateurs", data={"csrf": tok, "action": "create", "username": "agent.a", "nom": "A",
                                  "role": "agent", "password": "Agent2026x"})
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    d = c.get(f"/api/cas/{cid}").get_json()
    assert d["controls"]["contacts"]["phrase"].startswith("Minimum documenté : 41")
    case = d["case"]
    case["aire_sante"] = "Dingila"
    hdr = {"X-CSRF": tok, "Content-Type": "application/json"}
    assert c.put(f"/api/cas/{cid}?version=1", data=json.dumps(case), headers=hdr).status_code == 200
    assert c.put(f"/api/cas/{cid}", data=json.dumps(case),
                 headers={"Content-Type": "application/json"}).status_code == 400   # sans jeton CSRF
    for k in ("mapping", "network", "route", "gantt", "dashboard"):
        assert c.get(f"/cas/{cid}/apercu/{k}").status_code == 200
    assert c.get("/modele-excel").status_code == 200
    for fmt in ("svg", "pptx", "json", "xlsx"):
        r = c.get(f"/cas/{cid}/telecharger/{fmt}")
        assert r.status_code == 200 and len(r.data) > 1000
    # un agent ne voit pas les fiches des autres et n'administre pas les comptes
    c2 = app.test_client()
    _login(c2, "agent.a", "Agent2026x")
    assert c2.get(f"/cas/{cid}").status_code == 403
    assert c2.get("/utilisateurs").status_code == 403


def test_public_mode_blocks_web_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "d"))
    monkeypatch.setenv("MAPPING_EPI_PUBLIC", "1")
    from web.server import create_app
    a = create_app(Store(tmp_path / "d" / "db.sqlite"))
    assert a.config["SESSION_COOKIE_SECURE"] is True
    c = a.test_client()
    r = c.get("/installation")
    assert r.status_code == 503 and "creer-admin" in r.get_data(as_text=True)
    assert c.get("/sante").get_json()["ok"] is True
