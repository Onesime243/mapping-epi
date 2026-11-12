"""Anneau, reproduction, doublons, carte, synchronisation, sécurité du bureau, réunion."""
import io
import json
import re
from datetime import date, timedelta

import pytest

from core import carte as CARTE
from core import doublons as DB
from core import echanges as ECH
from core import pyramide
from core import riposte as R
from core import securite as SEC
from core import sync as SYNC
from core.models import Case, ContactGroup
from core.storage import Store
from core.users import Users
from tests.test_riposte import _cas, jeu

REF = date(2026, 11, 12)


def test_anneau_reproduction_sequencage():
    a = _cas("RDC-ITU-BUN-26-010", j0=date(2026, 9, 1), date_confirmation=date(2026, 9, 5),
             date_debut_anneau=date(2026, 9, 7), sequencage="lignée A",
             contacts=[ContactGroup(nombre=20, suivis=18, vaccines=15)])
    b = _cas("RDC-ITU-BUN-26-011", j0=date(2026, 9, 12), id_cas_source="RDC ITU BUN 26 010",
             contact_connu="Contact connu")
    c = _cas("RDC-ITU-BUN-26-012", j0=date(2026, 9, 14), id_cas_source="RDC-ITU-BUN-26-010",
             contact_connu="Contact connu", date_confirmation=date(2026, 9, 16))
    ind = {i.nom: i for i in R.indicateurs([a, b, c])}
    assert ind["Contacts vaccinés parmi les contacts listés"].texte() == "75 % (15/20)"
    assert ind["Délai médian confirmation → début de l'anneau"].valeur == 2
    assert ind["Cas confirmés avec un résultat de séquençage"].texte() == "50 % (1/2)"
    rp = R.reproduction([a, b, c], REF)
    assert rp.cas_utilises == 3 and rp.secondaires == 2 and abs(rp.r - 2 / 3) < 1e-9
    assert R.reproduction([], REF).r is None
    # ancien format de fiche (sans les nouveaux champs) : toujours lisible
    old = json.loads(a.model_dump_json())
    for k in ("date_debut_anneau", "sequencage"):
        old.pop(k)
    old["contacts"][0].pop("vaccines")
    assert Case.model_validate(old).contacts[0].vaccines is None


def test_doublons():
    x = _cas("RDC-ITU-BUN-26-001", sexe="M", age=30)
    y = _cas("rdc itu bun 26 001", sexe="M", age=30)
    z = _cas("RDC-ITU-BUN-26-099", sexe="M", age=31, j0=date(2026, 11, 2))
    w = _cas("RDC-ITU-BUN-26-100", sexe="F", age=31, j0=date(2026, 11, 2))
    ds = DB.doublons([x, y, z, w])
    assert ds[0].certitude == "forte" and {ds[0].a.id, ds[0].b.id} == {x.id, y.id}
    assert any(d.certitude == "à vérifier" and z.id in (d.a.id, d.b.id) for d in ds)
    assert not any(w.id in (d.a.id, d.b.id) for d in ds)


def test_carte():
    co = CARTE.lire_coordonnees("province;zone_sante;aire_sante;latitude;longitude\n"
                                "Ituri;Bunia;Lembabo;1,56;30,25\nIturi;Bunia;Nyakasanza;1,58;30,23\n"
                                "Ituri;Bunia;Erreur;48,8;2,3\n")
    assert len(co) == 2
    cases = jeu()
    cases[2].lat, cases[2].lon = 1.97, 30.10
    autre = _cas("RDC-ITU-BUN-26-050")
    autre.aire_sante = "Inconnue"
    perdu = _cas("RDC-NOR-XXX-26-001", zs="Zone sans coordonnées")
    ct = CARTE.construire(cases + [autre, perdu], co)
    sources = sorted(p.source for p in ct.points)
    assert sources == ["GPS", "aire de santé", "centre de la ZS"] and ct.sans_position == [perdu]
    assert CARTE.svg(ct, REF).startswith("<svg")


def test_securite_sauvegarde(tmp_path):
    st = Store(tmp_path / "db.sqlite", mirror_json=False)
    for c in jeu():
        st.save(c)
    assert not SEC.a_mot_de_passe(st) and SEC.verifier_mot_de_passe(st, "")
    with pytest.raises(ValueError):
        SEC.definir_mot_de_passe(st, "court")
    SEC.definir_mot_de_passe(st, "Ebola2026x")
    assert SEC.verifier_mot_de_passe(st, "Ebola2026x") and not SEC.verifier_mot_de_passe(st, "faux12345")
    SEC.ecrire(st, "dossier_sauvegarde", str(tmp_path / "usb"))
    assert SEC.sauvegarde_due(st)
    f = SEC.sauvegarder(st, tmp_path / "usb")
    assert f.exists() and not SEC.sauvegarde_due(st)
    neuf = Store(tmp_path / "neuf.sqlite", mirror_json=False)
    b = SEC.restaurer(neuf, f)
    assert len(b.ajoutees) == 3 and len(neuf.all_cases()) == 3
    assert SEC._tuple("1.10.0") > SEC._tuple("1.9.3")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "donnees"))
    pyramide._SINGLETON = None
    from web.server import create_app
    store = Store(tmp_path / "donnees" / "mapping_epi.sqlite")
    us = Users(store)
    us.create("admin", "Secret123", role="admin")
    us.create("agent.bunia", "Agent2026x", niveau="zone", province="Ituri", zs="Bunia")
    for c in jeu():
        store.save(c, owner="admin")
    a = create_app(store)
    a.testing = True
    return a


def _login(c, u, p):
    tok = re.search(r'name="csrf" value="([^"]+)"', c.get("/connexion").get_data(as_text=True)).group(1)
    c.post("/connexion", data={"csrf": tok, "username": u, "password": p})
    return re.search(r'name="csrf" value="([^"]+)"', c.get("/mon-compte").get_data(as_text=True)).group(1)


def test_synchronisation_web(app):
    c = app.test_client()
    tok = _login(c, "agent.bunia", "Agent2026x")
    page = c.post("/mon-compte", data={"csrf": tok, "action": "jeton", "nom": "PC Bunia"}).get_data(as_text=True)
    jeton = re.search(r'value="(mepi_[^"]+)"', page).group(1)
    assert "PC Bunia" in c.get("/mon-compte").get_data(as_text=True)
    api = app.test_client()                            # sans session : seul le jeton compte
    assert api.get("/api/sync/recevoir").status_code == 401
    assert api.get("/api/sync/recevoir", headers={"Authorization": "Bearer mepi_faux"}).status_code == 401
    h = {"Authorization": f"Bearer {jeton}"}
    recu, _err = ECH.lire_paquet(api.get("/api/sync/recevoir", headers=h).data)
    assert {x.zs for x in recu} == {"Bunia"}          # périmètre de la zone seulement
    nouveau = _cas("RDC-ITU-BUN-26-077")
    r = api.post("/api/sync/envoyer", data=ECH.paquet_bytes([nouveau]), headers=h)
    assert r.status_code == 200 and "1 fiche(s) ajoutée(s)" in r.get_json()["bilan"]
    assert app.store.load(nouveau.id) and app.store.owner_of(nouveau.id) == "agent.bunia"
    # révocation
    jid = SYNC.jetons(app.store, "agent.bunia")[0]["id"]
    c.post("/mon-compte", data={"csrf": tok, "action": "revoquer", "id": jid})
    assert api.get("/api/sync/recevoir", headers=h).status_code == 401


def test_client_sync(app, tmp_path, monkeypatch):
    """Le client du bureau, branché sur le serveur de test."""
    jeton = SYNC.creer_jeton(app.store, "admin", "PC")
    api = app.test_client()

    def fake(url, jeton_, data=None, timeout=90):
        h = {"Authorization": f"Bearer {jeton_}"}
        path = url.split("://", 1)[1].split("/", 1)[1]
        r = api.post("/" + path, data=data, headers=h) if data is not None else api.get("/" + path, headers=h)
        assert r.status_code == 200, r.data
        return r.data
    monkeypatch.setattr(SYNC, "_requete", fake)
    local = Store(tmp_path / "bureau.sqlite", mirror_json=False)
    local.save(_cas("RDC-HAU-ISI-26-001", zs="Isiro"))
    envoi, recu = SYNC.synchroniser(local, "serveur.test", jeton)
    assert "1 fiche(s) ajoutée(s)" in envoi and "3 fiche(s) ajoutée(s)" in recu
    assert len(local.all_cases()) == 4 and len(app.store.all_cases()) == 4


def test_pages_nouvelles(app):
    c = app.test_client()
    tok = _login(c, "admin", "Secret123")
    for url in ("/riposte/carte?periode=0", "/riposte/reunion?depuis=30&ref=2026-11-12", "/donnees/doublons",
                "/riposte/indicateurs"):
        r = c.get(url)
        assert r.status_code == 200, url
    assert "Nouveau cas 1/" in c.get("/riposte/reunion?depuis=30&ref=2026-11-12").get_data(as_text=True)
    assert "Nombre de reproduction observé" in c.get("/riposte/indicateurs").get_data(as_text=True)
    csv = "province;zone_sante;aire_sante;latitude;longitude\nIturi;Bunia;Lembabo;1.56;30.25\n"
    c.post("/riposte/carte", data={"csrf": tok, "coordonnees": (io.BytesIO(csv.encode()), "c.csv")},
           content_type="multipart/form-data")
    assert "<circle" in c.get("/riposte/carte?periode=0").get_data(as_text=True)
    assert "☰ Menu" in c.get("/cas").get_data(as_text=True)


def test_champs_obligatoires(app):
    """Sans les champs obligatoires, la fiche reste en brouillon : ni liste des cas, ni analyses."""
    from core import obligatoires as OBL
    c = app.test_client()
    tok = _login(c, "admin", "Secret123")
    cid = c.post("/cas/nouveau", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    assert app.store.load(cid) is None and app.store.load_brouillon(cid)
    hdr = {"X-CSRF": tok, "Content-Type": "application/json"}
    d = c.get(f"/api/cas/{cid}").get_json()["case"]
    d.update(code_cas="RDC-NOK-KAT-26-900", province="Nord-Kivu", zs="Katwa")
    j = c.put(f"/api/cas/{cid}", data=json.dumps(d), headers=hdr).get_json()
    assert j["brouillon"] and "Aire de santé" in j["obligatoires"] and app.store.load(cid) is None
    liste = c.get("/cas").get_data(as_text=True)
    assert "Brouillons (1)" in liste and "Aire de santé" not in liste.split("onglets")[0]
    assert "incomplet" in c.get("/cas?onglet=brouillons").get_data(as_text=True)
    d.update(aire_sante="Vighole", sexe="F", age=24, debut_symptomes="2026-11-01", date_confirmation="2026-11-05",
             issue="En traitement")
    j = c.put(f"/api/cas/{cid}", data=json.dumps(d), headers=hdr).get_json()
    assert not j["brouillon"] and app.store.load(cid).aire_sante == "Vighole"
    assert app.store.load_brouillon(cid) is None and app.store.owner_of(cid) == "admin"
    # une fiche enregistrée qu'on vide d'un champ obligatoire garde sa version enregistrée
    d["zs"] = ""
    j = c.put(f"/api/cas/{cid}", data=json.dumps(d), headers=hdr).get_json()
    assert j["brouillon"] and app.store.load(cid).zs == "Katwa"
    assert OBL.manquants(Case()) and len(OBL.champs()) == 9


def test_carte_contours():
    from core import geo
    g = geo.charger()
    assert len(g["aires"]) == 661 and g["limites_zs"] and "Nord-Kivu" in g["provinces"]
    assert geo.trouver_aire("Nord-Kivu", "Katwa", "vighole")
    c = _cas("RDC-NOK-KAT-26-001", zs="Katwa")
    c.province, c.aire_sante = "Nord-Kivu", "Vighole"
    ct = CARTE.construire([c], {})
    assert ct.points[0].source == "aire de santé"
    s = CARTE.svg(ct, REF)
    assert "<path" in s and "KATWA" in s and "GRID3" in s



def test_accueil_exemple_brouillons_vides(app):
    from datetime import datetime, timedelta
    c = app.test_client()
    tok = _login(c, "admin", "Secret123")
    page = c.get("/").get_data(as_text=True)
    assert "Nouveau cas" in page and "Voir les cas" in page and "Chaînes de transmission" in page and "Exemple fictif" in page
    # exemple fictif : mode entraînement, jamais compté avec les vrais cas
    n = len(app.store.all_cases())
    cid = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    assert app.store.load(cid).entrainement and "mode entraînement" in c.get(f"/cas/{cid}").get_data(as_text=True)
    assert "FICTIF-TUM" not in c.get("/cas").get_data(as_text=True)
    assert "FICTIF-TUM" in c.get("/cas?onglet=exemples").get_data(as_text=True)
    cid2 = c.post("/cas/demo", data={"csrf": tok}).headers["Location"].rsplit("/", 1)[1]
    assert app.store.load(cid) is None and len(app.store.all_cases()) == n + 1      # un seul exemple par compte
    ancien = _cas("FICTIF-TUM-26-003")          # ancien exemple enregistré avant ce mode : exclu aussi
    app.store.save(ancien, owner="admin")
    assert ECH.lire_paquet(c.get("/donnees/paquet.zip").data)[0] and all(
        not x.exemple() for x in ECH.lire_paquet(c.get("/donnees/paquet.zip").data)[0])
    # brouillon vide de plus de 24 h : supprimé ; brouillon commencé : gardé
    vide, commence = Case(zs="Bunia", province="Ituri"), Case(code_cas="RDC-X-1")
    for b in (vide, commence):
        app.store.save_brouillon(b, "admin")
    old = (datetime.now() - timedelta(hours=30)).isoformat()
    app.store.db.execute("UPDATE brouillons SET updated=?", (old,))
    app.store.db.commit()
    c.get("/")
    assert app.store.load_brouillon(vide.id) is None and app.store.load_brouillon(commence.id)
    assert cid2
