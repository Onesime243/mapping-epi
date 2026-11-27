"""Aperçu de chaque fichier avant téléchargement (Excel, Word, PowerPoint)."""
import pytest

from core import langue
from tests.test_web import _csrf, _login, app  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def _fr():
    langue.definir("fr")
    yield
    langue.definir("fr")


def test_apercus(app):  # noqa: F811
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123", "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    urls = ["/donnees/liste-cas.xlsx", "/donnees/rapport-situation.docx", "/pci/lieux-adresses.xlsx",
            "/surveillance/contacts.xlsx", "/analyse/concordance.xlsx", f"/cas/{cid}/fiche.docx", f"/cas/{cid}/fiche.xlsx",
            "/rapports/generer?debut=2026-01-01&fin=2026-12-31&pilier=surveillance&pilier=contacts&format=pptx",
            "/rapports/generer?debut=2026-01-01&fin=2026-12-31&pilier=surveillance&format=docx"]
    for u in urls:
        r = c.get(u + ("&" if "?" in u else "?") + "apercu=1")
        assert r.status_code == 200, u
        h = r.get_data(as_text=True)
        assert "Aperçu avant téléchargement" in h and "Télécharger le fichier" in h, u
        assert "apercu=1" not in h.split("Télécharger le fichier")[0].rsplit("href=", 1)[1], u     # le bouton télécharge
        d = c.get(u)
        assert d.status_code == 200 and "attachment" in d.headers.get("Content-Disposition", ""), u
    h = c.get("/donnees/liste-cas.xlsx?apercu=1").get_data(as_text=True)
    assert 'class="ap-onglets"' in h and "Modélisation" in h
    assert "ap-diapo" in c.get(urls[7] + "&apercu=1").get_data(as_text=True)
    menu = c.get("/").get_data(as_text=True)
    assert "liste-cas.xlsx?apercu=1" in menu and "rapport-situation.docx?apercu=1" in menu
