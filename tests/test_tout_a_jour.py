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


def test_langue_bienvenue_theme(app):
    c = app.test_client()
    _login(c, "admin", "Secret123")
    page = c.get("/").get_data(as_text=True)
    assert "Bienvenue dans Mapping Épi" in page and "'light'" in page and '<html lang="fr">' in page
    c.get("/langue/en", headers={"Referer": "http://localhost/"})
    page = c.get("/").get_data(as_text=True)
    assert "Welcome to Mapping Épi" in page and "View cases" in page and '<html lang="en">' in page
    assert "Saved" in c.get("/cas").get_data(as_text=True)
    c2 = app.test_client()                    # langue gardée pour le compte, nouvelle session
    _login(c2, "admin", "Secret123")
    assert "Welcome to Mapping Épi" in c2.get("/").get_data(as_text=True)
    c2.get("/langue/fr")
    assert "Bienvenue" in c2.get("/").get_data(as_text=True)


def test_droits_super_admin_provincial_session_unique(app):
    """Riposte et rapports : super-admins ; admin provincial limité à sa province ; une session par compte."""
    from core.models import Action
    us = app.users
    us.create("chef.nat", "Secret123", role="admin")                                  # admin national, pas super
    us.create("chef.itu", "Secret123", role="admin", niveau="province", province="Ituri")
    c = app.test_client()
    tok = _login(c, "chef.nat", "Secret123")
    page = c.get("/").get_data(as_text=True)
    assert "Riposte ▾" not in page and "Données ▾" in page and "Analyses ▾" in page
    assert c.get("/riposte/indicateurs").status_code == 403 and c.get("/rapports").status_code == 403
    assert c.get("/donnees/rapport-situation.docx").status_code == 403
    assert c.get("/donnees/liste-cas.xlsx").status_code == 200
    # admin provincial : comptes de zone / aire de SA province seulement
    p = app.test_client()
    tp = _login(p, "chef.itu", "Secret123")
    r = p.post("/utilisateurs", data={"csrf": tp, "action": "create", "username": "zs.bunia", "nom": "ZS Bunia",
                                      "role": "agent", "niveau": "zone", "province": "Ituri", "zs": "Bunia",
                                      "password": "Secret123"})
    assert us.get("zs.bunia") and us.get("zs.bunia").zs == "Bunia"
    r = p.post("/utilisateurs", data={"csrf": tp, "action": "create", "username": "zs.beni", "nom": "ZS Beni",
                                      "role": "agent", "niveau": "zone", "province": "Nord-Kivu", "zs": "Beni",
                                      "password": "Secret123"})
    assert us.get("zs.beni") is None and "province Ituri" in r.get_data(as_text=True)
    r = p.post("/utilisateurs", data={"csrf": tp, "action": "create", "username": "adm.x", "nom": "X", "role": "admin",
                                      "niveau": "province", "province": "Ituri", "password": "Secret123"})
    assert us.get("adm.x") is None
    liste = p.get("/utilisateurs").get_data(as_text=True)
    assert "zs.bunia" in liste and "chef.nat" not in liste            # comptes de sa province seulement
    # vue d'un agent : mapping et réseau seulement, pas d'analyse ; saisie, import et téléchargement du mapping permis
    a = app.test_client()
    ta = _login(a, "zs.bunia", "Secret123")
    cid = a.post("/cas/nouveau", data={"csrf": ta}).headers["Location"].rsplit("/", 1)[1]
    assert a.get(f"/cas/{cid}/apercu/mapping").status_code == 200
    assert a.get(f"/cas/{cid}/apercu/network").status_code == 200
    assert a.get(f"/cas/{cid}/apercu/gantt").status_code == 403
    # téléchargement du mapping et du réseau permis à tout compte ; autres vues et données brutes : non
    assert a.get(f"/cas/{cid}/telecharger/svg?visuel=mapping").status_code == 200
    assert a.get(f"/cas/{cid}/telecharger/svg?visuel=network").status_code == 200
    assert a.get(f"/cas/{cid}/telecharger/png?visuel=gantt").status_code == 403
    assert a.get(f"/cas/{cid}/telecharger/xlsx").status_code == 403
    assert a.get(f"/cas/{cid}/telecharger/json").status_code == 403
    page = a.get(f"/cas/{cid}").get_data(as_text=True)
    assert 'data-v="network"' in page and 'data-v="gantt"' not in page and "Analyses ▾" not in page
    assert 'class="card etapes"' in page and 'id="progression"' in page            # fiche par étapes
    assert 'data-fmt="png"' in page and 'data-fmt="xlsx"' not in page
    assert "Importer une fiche" in a.get("/cas").get_data(as_text=True)
    # session unique : la 2e connexion déconnecte la 1re
    b = app.test_client()
    _login(b, "zs.bunia", "Secret123")
    r = a.get("/cas")
    assert r.status_code == 302 and "/connexion" in r.headers["Location"]
    assert "Un autre utilisateur vient de se connecter" in a.get("/connexion").get_data(as_text=True)
    assert b.get("/cas").status_code == 200
    assert Action(texte="Décontaminer le CS Vighole").pilier == ""


def test_rapports_piliers(app, tmp_path):
    from datetime import date
    from docx import Document
    from pptx import Presentation
    from core import piliers as P
    from core import rapport_rendu as RR
    from core.models import Action
    assert P.pilier_action(Action(texte="Décontaminer le CS")) == "PCI"
    assert P.pilier_action(Action(texte="Lister les contacts")) == "Suivi des contacts"
    assert P.pilier_action(Action(texte="Réunion", pilier="Laboratoire")) == "Laboratoire"
    r = P.construire(jeu(), date(2026, 9, 1), date(2026, 11, 12), perimetre="Toute la RDC")
    assert [s.cle for s in r.sections] == ["surveillance", "contacts", "pci", "labo", "actions", "qualite"]
    assert all(s.questions and s.kpis for s in r.sections) and r.non_couverts
    RR.rapport_docx(r, tmp_path / "r.docx")
    RR.rapport_pptx(r, tmp_path / "r.pptx")
    txt = "\n".join(p.text for p in Document(tmp_path / "r.docx").paragraphs)
    assert "RAPPORT D'ANALYSE PAR PILIER" in txt and "Questions d'analyse" in txt and "Annexe" in txt
    assert len(Presentation(tmp_path / "r.pptx").slides) == 2 + 6 + 1
    c = app.test_client()
    _login(c, "admin", "Secret123")
    assert c.get("/rapports").status_code == 200
    for fmt in ("docx", "pptx"):
        res = c.get(f"/rapports/generer?debut=2026-09-01&fin=2026-11-12&pilier=pci&pilier=actions&format={fmt}")
        assert res.status_code == 200 and len(res.data) > 5000


def test_tableau_de_bord(app):
    from datetime import date
    from core import tableau_bord as TB
    from core.models import Action, ContactGroup
    # catégories d'actions : vérifiée, sans preuve, à vérifier, bloquée, en retard
    ref = date(2026, 11, 15)
    assert TB.categorie_action(Action(texte="x", statut="Fait", valide_par="Sup"), ref)[0] == "verifiee"
    assert TB.categorie_action(Action(texte="x", statut="Fait"), ref)[0] == "sans_preuve"
    assert TB.categorie_action(Action(texte="x", statut="Fait", preuve="photo"), ref)[0] == "a_verifier"
    assert TB.categorie_action(Action(texte="x", obstacle="Sécurité ou accès", echeance=date(2026, 11, 1)), ref)[0] == "bloquee"
    assert TB.categorie_action(Action(texte="x", echeance=date(2026, 11, 1)), ref) == ("retard", 14)
    # contacts à haut risque sans suivi : alerte critique ; suivi absent : jamais compté comme 0
    c = jeu()[0]
    c.contacts = [ContactGroup(categorie="Famille", nombre=12, suivis=0, risque="Haut")]
    lc = TB.ligne_cas(c, ref)
    assert lc.statut == "Critique" and any("aucun en suivi" in a.texte for a in lc.alertes)
    c.contacts = [ContactGroup(categorie="Famille", nombre=12, risque="Haut")]
    lc = TB.ligne_cas(c, ref)
    assert lc.suivis is None and any("non renseigné" in a.texte for a in lc.alertes)
    tb = TB.construire(jeu(), date(2026, 9, 1), date(2026, 11, 12))
    assert tb.n and len(tb.tuiles) == 4 and tb.semaines
    assert "<svg" in TB.svg_semaines(tb.semaines)
    # accès : super-administrateur seulement
    c = app.test_client()
    _login(c, "admin", "Secret123")
    for o in ("", "?debut=2026-09-01&fin=2026-11-12&onglet=actions", "?province=Ituri&pilier=PCI", "?debut=abc"):
        r = c.get("/tableau-de-bord" + o)
        assert r.status_code == 200, o
    page = c.get("/tableau-de-bord?debut=2026-09-01&fin=2026-11-12").get_data(as_text=True)
    assert "Tableau de bord de la riposte" in page and "sceau_presidence.png" in page and "Task Force Présidentielle Ebola 17" in page and "Matrice des questions" in page
    us = app.users
    us.create("chef.nat2", "Secret123", role="admin")                                   # national (niveau par défaut)
    us.create("chef.prov2", "Secret123", niveau="province", province="Ituri")           # provincial
    for u in ("chef.nat2", "chef.prov2"):                     # comptes nationaux et provinciaux : accès au tableau de bord
        c2 = app.test_client()
        _login(c2, u, "Secret123")
        page2 = c2.get("/tableau-de-bord")
        assert page2.status_code == 200 and "Rapport Word" not in page2.get_data(as_text=True)
        assert "tableau-de-bord" in c2.get("/").get_data(as_text=True)
    c3 = app.test_client()                                     # agent de zone : pas d'accès
    _login(c3, "agent.bunia", "Agent2026x")
    assert c3.get("/tableau-de-bord").status_code == 403
    assert "tableau-de-bord" not in c3.get("/").get_data(as_text=True)


def test_noms_de_personnes_signales():
    from core import rules
    from core.models import Case, ContactGroup, Event
    c = Case(zs="Beni", province="Nord-Kivu", aire_sante="Ngongolio", events=[
        Event(lieu="CM TAMENDE", titre="Accouchement et contact avecMUSUBAO MURATUSI Benedicte"),
        Event(lieu="HGR Beni", titre="Prélèvement PCR", description="Équipe MSF ALIMA, transfert au CTE de Beni"),
        Event(titre="Visite", personnes="Maman Kahindo et ses enfants")],
        contacts=[ContactGroup(categorie="Famille", lien="frère KAMBALE"), ContactGroup(categorie="Co-patients HGR")])
    trouves = [e for _o, e in rules.noms_personnes(c)]
    assert "MUSUBAO MURATUSI" in trouves and "Maman Kahindo" in trouves and "frère KAMBALE" in trouves
    assert not any("HGR" in e or "PCR" in e or "MSF" in e or "Beni" in e for e in trouves)
    msgs = [i.message for i in rules.check_consistency(c)]
    assert sum(1 for m in msgs if m.startswith("Nom de personne ?")) == 3
    import json
    from pathlib import Path
    ex = Case.model_validate(json.loads(Path("sample_data/cas_exemple_fictif.json").read_text(encoding="utf-8")))
    assert rules.noms_personnes(ex) == []


def test_lieux_harmonises_et_lieux_de_zone():
    from core.lieux import harmoniser, lieux_de_zone
    from core.models import Case, Event, Place
    assert harmoniser("hgr beni") == "HGR Beni" and harmoniser("HGR BENI") == "HGR Beni"
    assert harmoniser("cs de la mission") == "CS de la Mission"
    assert harmoniser("Lieu de culte Monzombo") == "Lieu de culte Monzombo"      # écriture mixte respectée
    a = Case(zs="Beni", province="Nord-Kivu", events=[Event(lieu="hgr beni"), Event(lieu="Domicile")])
    b = Case(zs="Beni", province="Nord-Kivu", places=[Place(nom="HGR BENI")], events=[Event(lieu="CM My God")])
    c = Case(zs="Butembo", province="Nord-Kivu", events=[Event(lieu="HGR Butembo")])
    z = lieux_de_zone([a, b, c], "Beni", "Nord-Kivu")
    assert z[0] == {"nom": "HGR Beni", "n": 2} and {"nom": "CM My God", "n": 1} in z
    assert not any(l["nom"] in ("Domicile", "HGR Butembo") for l in z)          # lieu vague, autre zone


def test_alertes_regroupees_par_cas():
    from datetime import date
    from core import tableau_bord as TB
    from core.models import ContactGroup
    cases = jeu()
    cases[0].contacts = [ContactGroup(categorie="Famille", nombre=12, suivis=0, risque="Haut")]
    tb = TB.construire(cases, date(2026, 9, 1), date(2026, 11, 12))
    assert tb.groupes and tb.groupes[0]["crit"] >= 1
    assert all(tb.groupes[i]["crit"] >= tb.groupes[i + 1]["crit"] for i in range(len(tb.groupes) - 1))
    assert sum(len(g["liste"]) for g in tb.groupes) == sum(1 for a in tb.alertes if a.cid)


def test_suivi_des_alertes_et_courbes(app):
    from core import alertes_suivi as AS
    from core import tableau_bord as TB
    from core.models import ContactGroup
    assert AS.type_alerte("12 contacts à haut risque listés, aucun en suivi") == AS.type_alerte("3 contacts à haut risque listés, aucun en suivi")
    svg = TB.sparkline([None, 2, 3, None, 5, 4, 6, 7], seuil=5)
    assert svg.count("<polyline") == 2 and "sp-seuil" in svg and "sp-mal" in svg
    st = app.store
    c = jeu()[0]
    c.contacts = [ContactGroup(categorie="Famille", nombre=12, suivis=0, risque="Haut")]
    st.save(c, owner="admin")
    cl = app.test_client()
    tok = _login(cl, "admin", "Secret123")
    q = "debut=2026-09-01&fin=2026-11-12"
    page = cl.get("/tableau-de-bord?" + q).get_data(as_text=True)
    assert "Je m’en occupe" in page and "courbe : 8 dernières semaines" in page and "tb-spark-svg" in page
    r = cl.post("/tableau-de-bord/alerte", data={"csrf": tok, "cid": c.id, "action": "prendre", "note": "relance EPI", "retour": q})
    assert r.status_code == 302 and q in r.headers["Location"]
    page = cl.get("/tableau-de-bord?" + q).get_data(as_text=True)
    assert "Prise en charge · admin" in page and "relance EPI" in page
    cl.post("/tableau-de-bord/alerte", data={"csrf": tok, "cid": c.id, "action": "resoudre", "retour": q})
    page = cl.get("/tableau-de-bord?" + q).get_data(as_text=True)
    assert "Réapparue" in page                                 # la fiche montre toujours le problème
    assert AS.resolues_depuis(st, 7)[0]["par"] == "admin"
    agent = app.test_client()
    ta = _login(agent, "agent.bunia", "Agent2026x")
    assert agent.post("/tableau-de-bord/alerte", data={"csrf": ta, "cid": c.id, "action": "prendre"}).status_code == 403
