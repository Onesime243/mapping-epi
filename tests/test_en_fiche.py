"""Fiche (formulaire) en anglais : libellés traduits, choix enregistrés en français, français inchangé."""
import json
import re

import pytest

from core import langue, obligatoires as OBL, pyramide, rules
from core.models import Case, ContactGroup, Event
from core.storage import Store


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


def _admin_et_demo(app):
    c = app.test_client()
    tok = _csrf(c.get("/installation").get_data(as_text=True))
    c.post("/installation", data={"csrf": tok, "nom": "Admin", "username": "admin", "password": "Secret123",
                                  "password2": "Secret123"})
    tok = _login(c, "admin", "Secret123")
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    return c, tok, cid


def _i18n(html):
    m = re.search(r"window\.I18N = (\{.*?\});</script>", html, re.S)
    assert m, "window.I18N absent de la page"
    return json.loads(m.group(1))


def test_fiche_en_francais_inchangee(app):
    c, tok, cid = _admin_et_demo(app)
    html = c.get(f"/cas/{cid}").get_data(as_text=True)
    assert "1. Identité" in html and "3. Chronologie" in html and "Lecture seule" not in html
    assert "Identity" not in html and "Timeline of events" not in html
    assert _i18n(html) == {}
    s = c.get("/api/schema").get_json()
    assert s["tables"]["events"][7]["label"] == "Type d'étape"
    assert {"key": "zs", "label": "Zone de santé"} in s["obligatoires"]
    d = c.get(f"/api/cas/{cid}").get_json()
    assert d["controls"]["contacts"]["phrase"].startswith("Minimum documenté : 41")
    sugg = {x["texte"]: x["affiche"] for x in d["controls"]["suggestions"]}
    assert all(k == v for k, v in sugg.items())


def test_fiche_en_anglais(app):
    c, tok, cid = _admin_et_demo(app)
    c.get("/langue/en")
    page = c.get(f"/cas/{cid}").get_data(as_text=True)
    d = _i18n(page)
    html = re.sub(r"window\.I18N = \{.*?\};</script>", "", page, flags=re.S)     # page visible, sans le dictionnaire
    for txt in ("1. Identity", "2. Clinical", "3. Timeline of events", "4. Places", "6. IPC", "7. Laboratory",
                "Checks", "Save a version", "Suggested actions", "← Case list"):
        assert txt in html, txt
    assert "1. Identité" not in html and "Enregistrer une version" not in html and "—" not in html
    # dictionnaire du formulaire et des choix pour editor.js
    assert d["Contact connu"] == "Known contact" and d["Non vacciné"] == "Not vaccinated"
    assert d["Phase sèche"] == "Dry phase" and d["Très élevé"] == "Very high" and d["À investiguer"] == "To investigate"
    assert d["Enregistré"] == "Saved" and d["MVE"] == "EVD" and d["PCI"] == "IPC"
    assert d["Enterrement digne et sécurisé"] == "Safe and dignified burial"
    assert not any("—" in v for v in d.values() if isinstance(v, str))

    s = c.get("/api/schema").get_json()
    ev = {col["key"]: col for col in s["tables"]["events"]}
    assert ev["type"]["label"] == "Step type" and ev["personnes"]["label"] == "People present"
    assert "Début maladie" in ev["type"]["choices"]            # choix : valeurs françaises (affichées traduites)
    assert "Inconnu" in s["choices"]["risks"] and "Contact connu suivi" in s["choices"]["contact_status"]
    assert {"key": "zs", "label": "Health zone"} in s["obligatoires"]

    j = c.get(f"/api/cas/{cid}").get_json()
    ctl = j["controls"]
    assert ctl["contacts"]["phrase"].startswith("Documented minimum: 41 high-risk contacts")
    assert ctl["risk"] == "Très élevé"                         # valeur, traduite à l'affichage
    sugg = {x["texte"]: x for x in ctl["suggestions"]}
    if "Lister tous les contacts" in sugg:
        assert sugg["Lister tous les contacts"]["affiche"] == "List all contacts"
    assert all(re.search(r"[éèàù«»]", m) is None for m in ctl["missing"])
    msgs = [i["msg"] for i in ctl["issues"]]                   # titres saisis gardés tels quels, messages traduits
    assert any(m.endswith(": people present to complete.") for m in msgs)
    assert any(m.startswith("Uncovered period from ") for m in msgs)
    assert ctl["computed"]["events"][0]["lvl"] == "À investiguer"
    assert ctl["computed"]["events"][0]["why"] == "Source of exposure to be confirmed"


def test_enregistrement_en_anglais_garde_les_valeurs_francaises(app):
    c, tok, cid = _admin_et_demo(app)
    c.get("/langue/en")
    case = c.get(f"/api/cas/{cid}").get_json()["case"]
    case["aire_sante"] = "Dingila"
    case["contact_connu"] = "Contact connu suivi"
    case["id_cas_source"] = "RDC-TEST-001"
    case["phase_dds"] = "Phase sèche"
    case["issue"] = "Décès"
    case["events"][0]["type"] = "Enterrement"
    case["events"][0]["risque"] = "Très élevé"
    hdr = {"X-CSRF": tok, "Content-Type": "application/json"}
    r = c.put(f"/api/cas/{cid}?version=1", data=json.dumps(case), headers=hdr)
    assert r.status_code == 200 and r.get_json()["brouillon"] is False
    stored = app.store.load(cid)
    assert stored.contact_connu == "Contact connu suivi" and stored.phase_dds == "Phase sèche"
    assert stored.issue == "Décès" and stored.events[0].type == "Enterrement" and stored.events[0].risque == "Très élevé"
    # relue en français : identique
    c.get("/langue/fr")
    back = c.get(f"/api/cas/{cid}").get_json()["case"]
    assert back["contact_connu"] == "Contact connu suivi" and back["events"][0]["type"] == "Enterrement"


def test_regles_traduites_seulement_en_anglais():
    c = Case(maladie="MVE", contact_connu="Contact connu",
             events=[Event(type="Hospitalisation", titre="")], contacts=[ContactGroup(categorie="Voisins", nombre=None)])
    fr = [i.message for i in rules.check_consistency(c)]
    assert "Contact connu : l'ID du cas source est obligatoire (à compléter)." in fr
    assert any(m.startswith("« Hospitalisation » : date inconnue") for m in fr)
    with langue.utiliser("en"):
        en = [i.message for i in rules.check_consistency(c)]
        assert "Known contact: the source case ID is required (to complete)." in en
        assert any(m.startswith("\"Hospitalisation\": unknown date") for m in en)
        assert "Health area" in rules.completeness(c)[1]
        assert "Health zone" in OBL.manquants(c)
        assert OBL.message(["Sex"]).startswith("Cannot save: required field(s) missing: Sex")
        sug = rules.suggest_actions(c)
        assert all(s.texte != s.affiche for s in sug if s.texte == "Lister tous les contacts")
        assert any(s.texte == "Lister tous les contacts" and s.affiche == "List all contacts" for s in sug)
    assert "Zone de santé" in OBL.manquants(c)
    assert rules.contact_summary(c).phrase.startswith("Aucun contact à haut risque")
