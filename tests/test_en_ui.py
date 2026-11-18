"""Pages web en anglais (GET /langue/en) et inchangées en français (GET /langue/fr)."""
import re

import pytest

from core import pyramide
from core.models import Case
from core.storage import Store

ROOT_SAMPLE = "sample_data/cas_exemple_fictif.json"


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


def _page(c, url):
    r = c.get(url)
    assert r.status_code == 200, url
    html = r.get_data(as_text=True)
    return re.sub(r'name="password" value="[^"]*"', "", html)       # mot de passe proposé : tiré au hasard


@pytest.fixture
def client(app):
    """Super-administrateur « adminone », un agent et une fiche enregistrée (pas un exemple fictif)."""
    from pathlib import Path
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin One", "username": "adminone", "password": "Secret123",
                                  "password2": "Secret123"})
    tok = _login(c, "adminone", "Secret123")
    c.post("/utilisateurs", data={"csrf": tok, "action": "create", "username": "agent.a", "nom": "Agent A",
                                  "role": "agent", "password": "Agent2026x"})
    case = Case.model_validate_json((Path(__file__).resolve().parent.parent / ROOT_SAMPLE).read_text("utf-8"))
    case.code_cas, case.entrainement = "TEST-EN-001", False
    app.store.save(case, version=True, auteur="adminone", commentaire="test", owner="adminone")
    return c


PAGES_FR = {
    "/utilisateurs": ["Nouveau compte", "Dernière connexion", "Historique des suppressions de comptes", "Créer le compte"],
    "/donnees": ["Données : listes, rapports et échange de fiches", "Importer un paquet", "Exporter un paquet de fiches (.zip)"],
    "/tableau-de-bord": ["Tableau de bord de la riposte", "Appliquer", "Réinitialiser", "Registre des actions"],
    "/rapports": ["Rapports par pilier", "Rapport détaillé (Word)", "Présentation (PowerPoint)"],
    "/analyse/zones": ["Catégories des zones de santé, délais et incubation", "Délais et incubation observés"],
    "/mon-compte": ["Mot de passe actuel", "Créer un jeton"],
    "/riposte/indicateurs": ["Nombre de reproduction observé", "Date de référence"],
    "/donnees/doublons": ["Aucun doublon possible dans votre périmètre."],
}
PAGES_EN = {
    "/utilisateurs": ["New account", "Last sign-in", "Account deletion history", "Create the account", "Full name"],
    "/donnees": ["Data: lists, reports and record exchange", "Import a package", "Export a record package (.zip)"],
    "/tableau-de-bord": ["Response dashboard", "Apply", "Reset", "Action register"],
    "/rapports": ["Reports by pillar", "Detailed report (Word)", "Presentation (PowerPoint)", "All provinces"],
    "/analyse/zones": ["Health zone categories, delays and incubation", "Observed delays and incubation"],
    "/mon-compte": ["Current password", "Create a token"],
    "/riposte/indicateurs": ["Observed reproduction number", "Reference date"],
    "/donnees/doublons": ["No possible duplicate in your scope."],
}


def test_pages_en_anglais_puis_inchangees_en_francais(client):
    c = client
    avant = {}
    for url, textes in PAGES_FR.items():
        avant[url] = _page(c, url)
        for s in textes:
            assert s in avant[url], (url, s)
    c.get("/langue/en")
    for url, textes in PAGES_EN.items():
        html = _page(c, url)
        assert '<html lang="en">' in html
        for s in textes:
            assert s in html, (url, s)
        for s in PAGES_FR[url]:                     # plus les libellés français
            assert s not in html, (url, s)
    # en anglais, aucun tiret long dans les libellés ajoutés
    assert "—" not in _page(c, "/utilisateurs")
    c.get("/langue/fr")
    for url in PAGES_FR:
        assert _page(c, url) == avant[url], url


def test_messages_flash_traduits(client):
    c = client
    c.get("/langue/en")
    tok = _csrf(_page(c, "/utilisateurs"))
    r = c.post("/utilisateurs", data={"csrf": tok, "action": "delete", "username": "agent.a", "motif": ""},
               follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "Account “agent.a” deleted (0 record(s) kept)" in html
    assert "supprimé" not in html
    assert "Page or record not found." in c.get("/page-inexistante").get_data(as_text=True)


def test_connexion_en_anglais(client):
    c = client
    c.get("/deconnexion")
    assert "Se connecter" in c.get("/connexion").get_data(as_text=True)
    c.get("/langue/en")
    html = c.get("/connexion").get_data(as_text=True)
    assert "Sign in" in html and "Username" in html and "Se connecter" not in html
    tok = _csrf(html)
    html = c.post("/connexion", data={"csrf": tok, "username": "adminone", "password": "faux-mot-1"}).get_data(as_text=True)
    assert "Incorrect username or password." in html
