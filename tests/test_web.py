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


def test_admin_voit_tout_et_lieux_frequentes(app):
    from core.models import Case, Event
    st = app.store
    us = Users(st)
    us.create("chef", "Secret123", role="admin")
    us.create("agent.a", "Secret123")
    us.create("agent.b", "Secret123")
    for i, (owner, as_) in enumerate([("agent.a", "Bolebole"), ("agent.b", "Bolebole"), ("agent.b", "Abanagomu")]):
        c = Case(code_cas=f"HUE-WAM-{i + 1:03d}", province="Haut-Uele", zs="Wamba", aire_sante=as_,
                 events=[Event(lieu="Carrière minière Makasi (AS Bolebole)", type="Exposition"),
                         Event(lieu="Clinique Wamba" if i else "clinique wamba", type="Soins / consultation")])
        st.save(c, owner=owner)
    c = app.test_client()
    _login(c, "agent.a", "Secret123")
    html = c.get("/cas").get_data(as_text=True)
    assert "HUE-WAM-001" in html and "HUE-WAM-002" not in html          # un agent ne voit que ses fiches
    # un compte non administrateur n'a pas accès aux analyses (vue limitée au mapping et au réseau)
    assert c.get("/analyse/lieux/zs?province=Haut-Uele&zs=Wamba").status_code == 403
    c.get("/deconnexion")
    _login(c, "chef", "Secret123")
    html = c.get("/cas?agent=agent.b").get_data(as_text=True)
    assert "HUE-WAM-002" in html and "HUE-WAM-003" in html and "HUE-WAM-001" not in html
    html = c.get("/analyse/lieux/zs?province=Haut-Uele&zs=Wamba").get_data(as_text=True)
    assert "Carrière minière Makasi" in html and "3 cas" in html and "Clinique Wamba" in html
    html = c.get("/analyse/lieux/as?province=Haut-Uele&zs=Wamba&as=Bolebole").get_data(as_text=True)
    assert "2 cas" in html
    assert c.get("/analyse/lieux/zs/classement?province=Haut-Uele&zs=Wamba").status_code == 200
    r = c.get("/analyse/lieux/as/reseau.svg?province=Haut-Uele&zs=Wamba&as=Bolebole")
    assert r.status_code == 200 and b"<svg" in r.data


def test_import_ignore_lignes_residuelles(tmp_path):
    from openpyxl import load_workbook

    from core import storage
    from core.models import Case, Event
    p = tmp_path / "c.xlsx"
    storage.export_excel(Case(events=[Event(lieu="A", titre="Étape A")]), p)
    wb = load_workbook(p)
    ws = wb["Chronologie"]
    hdr = [x.value for x in ws[3]]
    for r in range(6, 12):                       # restes : seulement un risque, un type ou « oui »
        ws.cell(row=r, column=hdr.index("Risque (vide = auto)") + 1, value="Élevé")
        ws.cell(row=r, column=hdr.index("Type") + 1, value="Autre")
        ws.cell(row=r, column=hdr.index("Sans PCI") + 1, value="oui")
    wb.save(p)
    assert len(storage.import_excel(p).events) == 1


def test_tutoriel_public(app):
    c = app.test_client()
    assert c.get("/tutoriel").status_code in (301, 302, 308)
    r = c.get("/tutoriel/")
    assert r.status_code == 200 and "Parcours guidé Mapping Épi".encode() in r.data
    assert c.get("/tutoriel/frames/w01.jpg").status_code == 200
    assert c.get("/tutoriel/Exemple_Mapping_rempli_FICTIF.xlsx").status_code == 200
    assert c.get("/tutoriel/../server.py").status_code == 404


def test_import_narratif_web(app, tmp_path):
    import io

    from tests.test_narratif import _docx_fictif
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123",
                                  "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    p = tmp_path / "n.docx"
    _docx_fictif(p)
    r = c.post("/cas/importer", data={"csrf": tok, "fichier": (io.BytesIO(p.read_bytes()), "narratif.docx")},
               content_type="multipart/form-data")
    cid = r.headers["Location"].rsplit("/", 1)[1]
    d = c.get(f"/api/cas/{cid}").get_json()
    assert d["case"]["zs"] == "Tumba" and len(d["case"]["events"]) >= 3


def test_liste_cas_par_pages_de_20(app):
    from core.models import Case
    st = app.store
    Users(st).create("chef", "Secret123", role="admin")
    for i in range(45):
        st.save(Case(code_cas=f"PAG-{i + 1:03d}", province="Equateur", zs="Tumba"), owner="chef")
    c = app.test_client()
    _login(c, "chef", "Secret123")
    p1 = c.get("/cas?tri=code&ordre=asc").get_data(as_text=True)
    assert "PAG-001" in p1 and "PAG-020" in p1 and "PAG-021" not in p1
    assert "Fiches 1 à 20 sur 45" in p1 and "page=2" in p1 and "Suivant" in p1
    p3 = c.get("/cas?tri=code&ordre=asc&page=3").get_data(as_text=True)
    assert "PAG-041" in p3 and "PAG-045" in p3 and "PAG-040" not in p3 and "Précédent" in p3
    assert "PAG-041" in c.get("/cas?tri=code&ordre=asc&page=99").get_data(as_text=True)   # page trop grande : la dernière


def test_compte_partenaire_consultation_seule(app):
    from core.models import Case
    st = app.store
    us = Users(st)
    us.create("chef", "Secret123", role="admin")
    us.create("agent.kv", "Secret123", niveau="zone", province="Nord-Kivu", zs="Butembo")
    p = us.create("partenaire.oms", "Secret123", role="partenaire", niveau="aire", province="Equateur")
    p = us.get("partenaire.oms")
    assert p.is_partenaire and p.niveau == "national" and not p.is_admin
    a = Case(code_cas="NK-BUT-001", province="Nord-Kivu", zs="Butembo")
    b = Case(code_cas="EQ-TUM-001", province="Equateur", zs="Tumba")
    st.save(a, owner="agent.kv")
    st.save(b, owner="chef")
    c = app.test_client()
    t0 = _csrf(c.get("/connexion").get_data(as_text=True))
    c.post("/connexion", data={"csrf": t0, "username": "partenaire.oms", "password": "Secret123"})
    tok = _csrf(c.get("/mon-compte").get_data(as_text=True))
    liste = c.get("/cas").get_data(as_text=True)
    assert "NK-BUT-001" in liste and "EQ-TUM-001" in liste          # toutes les provinces
    assert "Nouveau cas" not in liste and "Importer une fiche" not in liste
    accueil = c.get("/").get_data(as_text=True)
    assert "Tableau de bord" not in accueil and "Utilisateurs" not in accueil and "Analyses" not in accueil
    # pages réservées : refusées même en tapant l'adresse
    for url in ("/tableau-de-bord", "/analyse/chaines", "/donnees", "/utilisateurs", "/rapports", "/riposte/indicateurs",
                "/analyse/zones", "/modele-excel"):
        assert c.get(url).status_code == 403, url
    fiche = c.get(f"/cas/{a.id}").get_data(as_text=True)
    assert "Lecture seule" in fiche and "Carte du parcours" in fiche and "Chaînes de transmission" in fiche
    assert "Frise temporelle" not in fiche and "Lieux communs" not in fiche
    assert 'data-fmt="svg"' not in fiche and 'data-fmt="rapport-pptx"' not in fiche and 'data-fmt="xlsx"' not in fiche
    for v in ("mapping", "network", "route", "dashboard", "chains"):
        assert c.get(f"/cas/{a.id}/apercu/{v}").status_code == 200, v
    for v in ("gantt", "common"):
        assert c.get(f"/cas/{a.id}/apercu/{v}").status_code == 403, v
    for fmt, vis in (("svg", "mapping"), ("pdfa4", "mapping"), ("xlsx", "mapping"), ("json", "mapping"),
                     ("rapport-pptx", "mapping"), ("png", "gantt"), ("pptx", "network")):
        assert c.get(f"/cas/{a.id}/telecharger/{fmt}?visuel={vis}").status_code == 403, (fmt, vis)
    assert c.get(f"/api/cas/{a.id}").status_code == 200
    r = c.put(f"/api/cas/{a.id}", json={}, headers={"X-CSRF": tok})
    assert r.status_code == 403
    assert c.post("/cas/nouveau", data={"csrf": tok}).status_code == 403
    assert c.post(f"/cas/{a.id}/supprimer", data={"csrf": tok}).status_code == 403
    # un administrateur provincial ne crée pas de partenaire
    from core.users import User
    prov = User("adm.p", "", "admin", True, "", "", "", niveau="province", province="Equateur")
    assert Users.peut_gerer(prov, "partenaire", "national", "") is not None


def test_page_importer_une_fiche(app):
    Users(app.store).create("agent.x", "Secret123")
    c = app.test_client()
    _login(c, "agent.x", "Secret123")
    assert "/cas/importer" in c.get("/").get_data(as_text=True)
    page = c.get("/cas/importer").get_data(as_text=True)
    assert 'name="fichier"' in page and "Modèle Word" in page


def test_menu_pci_lieux_et_adresses(app, tmp_path):
    import io
    from datetime import date
    from openpyxl import load_workbook
    from core.models import Case, Event, IPCSite
    from core import pci_lieux as PCI
    us = Users(app.store)
    us.create("agent.p", "Secret123")
    c0 = Case(code_cas="EQ-TUM-009", province="Equateur", zs="Tumba",
              events=[Event(lieu="CS Nzala", date_debut=date(2026, 7, 19), titre="Début maladie"),
                      Event(lieu="CS Nzala", lieu_arrivee="HGR Tumba", date_debut=date(2026, 7, 27), titre="Référence")],
              ipc=[IPCSite(site="CS Nzala", statut="Oui", adresse="Av. du Marché 12, Q. Nzala")])
    app.store.save(c0, owner="agent.p")
    rows = PCI.lignes([c0])
    assert [r["lieu"] for r in rows] == ["CS Nzala", "HGR Tumba"]          # un lieu cité deux fois : une ligne
    assert rows[0]["adresse"] == "Av. du Marché 12, Q. Nzala" and rows[1]["adresse"] == "?"
    c = app.test_client()
    _login(c, "agent.p", "Secret123")
    assert "/pci" in c.get("/").get_data(as_text=True)
    page = c.get("/pci").get_data(as_text=True)
    assert "HGR Tumba" in page and "Av. du Marché 12" in page
    r = c.get("/pci/lieux-adresses.xlsx")
    assert r.status_code == 200
    ws = load_workbook(io.BytesIO(r.data))["Lieux et adresses"]
    assert ws["A3"].value == "EQ-TUM-009" and ws["I3"].value == "Av. du Marché 12, Q. Nzala" and ws["I4"].value == "?"
