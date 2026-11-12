"""Indicateurs de la riposte, courbe épidémique, suivi des actions, paquet de fiches, liste et rapport."""
import io
import re
import zipfile
from datetime import date, datetime, timedelta

import pytest

from core import echanges as ECH
from core import pyramide
from core import riposte as R
from core.models import Action, Case, ContactGroup, Event
from core.storage import Store
from core.users import Users

REF = date(2026, 11, 12)


def _cas(code, zs="Bunia", j0=date(2026, 11, 1), **kw) -> Case:
    c = Case(code_cas=code, province="Ituri", zs=zs, aire_sante="Lembabo", debut_symptomes=j0,
             phase_dds="Phase sèche", date_notification=j0 + timedelta(days=2), **kw)
    return c


def jeu():
    a = _cas("RDC-ITU-BUN-26-001", contact_connu="Contact connu suivi", agent_sante="Oui",
             events=[Event(type="Hospitalisation", date_debut=date(2026, 11, 3))],
             contacts=[ContactGroup(categorie="Famille", nombre=10, suivis=9)],
             actions=[Action(texte="Boucler les contacts", priorite="Urgent", responsable="EPI ZS",
                             echeance=date(2026, 11, 8))])
    b = _cas("RDC-ITU-BUN-26-002", contact_connu="Non contact", issue="Décès", date_deces=date(2026, 11, 9),
             events=[Event(type="Enterrement", date_debut=date(2026, 11, 10), securise=False)],
             actions=[Action(texte="Décontaminer le ménage", statut="Fait")])
    c = _cas("RDC-ITU-FAT-26-001", zs="Fataki", j0=date(2026, 10, 1), contact_connu="Inconnu")
    return [a, b, c]


def test_indicateurs():
    ind = {i.nom: i for i in R.indicateurs(jeu())}
    i = ind["Nouveaux cas déjà connus comme contacts"]
    assert (i.num, i.den, i.inconnus) == (1, 2, 1) and i.texte() == "50 % (1/2)" and i.statut == "attention"
    assert ind["Cas sans lien épidémiologique connu"].cas == ["RDC-ITU-BUN-26-002"]
    assert ind["Délai médian début des symptômes → isolement"].valeur == 2
    assert ind["Décès survenus dans la communauté"].texte() == "100 % (1/1)"
    assert ind["Enterrements dignes et sécurisés"].statut == "alerte"
    assert ind["Contacts suivis parmi les contacts listés"].texte() == "90 % (9/10)"
    assert ind["Cas parmi les agents de santé (PPL)"].statut == "info"
    # rien d'inventé : sans données, pas de valeur
    vide = {i.nom: i for i in R.indicateurs([])}
    assert vide["Nouveaux cas déjà connus comme contacts"].texte() == "?"


def test_filtre_courbe_actions():
    cases = jeu()
    assert len(R.filtrer(cases, 21, REF)) == 2 and len(R.filtrer(cases, None, REF, "Ituri")) == 3
    cb = R.courbe(cases)
    assert sum(sum(v) for v in cb.series.values()) == 3 and sum(cb.deces) == 1
    assert cb.semaines[0].weekday() == 0
    svg = R.courbe_svg(cb)
    assert svg.startswith("<svg") and "Bunia" in svg
    acts = R.actions_ouvertes(cases, REF)
    assert len(acts) == 1 and acts[0].retard == 4
    assert len(R.actions_ouvertes(cases, REF, toutes=True)) == 2
    assert R.bilan_actions(acts)["retard"] == 1
    assert "Boucler les contacts" in R.html_actions(acts)
    assert "rip-k" in R.html_indicateurs(R.indicateurs(cases))


def test_paquet_synchronisation(tmp_path):
    src = Store(tmp_path / "a.sqlite", mirror_json=False)
    dst = Store(tmp_path / "b.sqlite", mirror_json=False)
    cases = jeu()
    for c in cases:
        src.save(c, version=True)
    data = ECH.paquet_bytes(src.all_cases(), "agent")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert "manifeste.json" in z.namelist() and not any("user" in n for n in z.namelist())
    b = ECH.importer_paquet(dst, data, "national")
    assert len(b.ajoutees) == 3 and len(dst.all_cases()) == 3
    b = ECH.importer_paquet(dst, data, "national")         # deuxième import : rien ne change
    assert b.identiques == 3 and not b.ajoutees and len(dst.all_cases()) == 3

    # modification plus récente sur l'ordinateur A : mise à jour, l'ancienne reste dans l'historique
    c0 = src.load(cases[0].id)
    c0.aire_sante = "Nyakasanza"
    src.save(c0, version=True)
    plus_tard = src.load(c0.id)
    plus_tard.modifie_le += timedelta(minutes=5)       # modifiée après l'export (horodatage à la seconde)
    b = ECH.importer_paquet(dst, ECH.paquet_bytes([plus_tard]), "national")
    assert b.mises_a_jour == ["RDC-ITU-BUN-26-001"] and dst.load(c0.id).aire_sante == "Nyakasanza"
    assert dst.load(c0.id).modifie_le == plus_tard.modifie_le          # date d'origine conservée
    assert any("Avant import" in (v[3] or "") for v in dst.versions(c0.id))

    # version plus ancienne : ignorée
    vieux = cases[1].model_copy(update={"aire_sante": "Autre", "modifie_le": datetime(2020, 1, 1)})
    b = ECH.importer_paquet(dst, ECH.paquet_bytes([vieux]), "national")
    assert b.plus_anciennes and dst.load(vieux.id).aire_sante == "Lembabo"

    # même N° EPID sous une autre fiche : conflit, rien n'est écrasé
    double = _cas("RDC ITU BUN 26 002")
    b = ECH.importer_paquet(dst, ECH.paquet_bytes([double]), "national")
    assert b.conflits and len(dst.all_cases()) == 3

    # droits : fiche hors périmètre ignorée
    c1 = src.load(cases[2].id)
    c1.village = "Nouveau"
    c1.modifie_le = datetime.now() + timedelta(minutes=5)
    b = ECH.importer_paquet(dst, ECH.paquet_bytes([c1]), "zone", peut_modifier=lambda c, o: False)
    assert b.refusees and dst.load(c1.id).village == ""

    with pytest.raises(ValueError):
        ECH.importer_paquet(dst, b"pas un zip", "x")


def test_liste_et_rapport(tmp_path):
    from docx import Document
    from openpyxl import load_workbook
    cases = jeu()
    ECH.liste_cas_xlsx(cases, tmp_path / "l.xlsx", "Ituri")
    ws = load_workbook(tmp_path / "l.xlsx").active
    assert ws.cell(2, 1).value == "N° EPID" and ws.max_row == 5
    ECH.rapport_docx(cases, tmp_path / "r.docx", "Ituri", 21, REF)
    txt = "\n".join(p.text for p in Document(tmp_path / "r.docx").paragraphs)
    assert "RAPPORT DE SITUATION" in txt and "Points d'attention" in txt


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MAPPING_EPI_DONNEES", str(tmp_path / "donnees"))
    pyramide._SINGLETON = None
    from web.server import create_app
    store = Store(tmp_path / "donnees" / "mapping_epi.sqlite")
    Users(store).create("admin", "Secret123", role="admin")
    for c in jeu():
        store.save(c, owner="admin")
    a = create_app(store)
    a.testing = True
    return a


def _csrf(html):
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_pages_web(app):
    c = app.test_client()
    tok = _csrf(c.get("/connexion").get_data(as_text=True))
    c.post("/connexion", data={"csrf": tok, "username": "admin", "password": "Secret123"})
    page = c.get("/cas").get_data(as_text=True)
    assert "Riposte ▾" in page and "Données ▾" in page
    r = c.get("/riposte/indicateurs?periode=0")
    assert r.status_code == 200 and "Nouveaux cas déjà connus comme contacts" in r.get_data(as_text=True)
    assert "Boucler les contacts" in c.get("/riposte/actions").get_data(as_text=True)
    assert c.get("/donnees").status_code == 200
    for quoi in ("liste-cas.xlsx", "rapport-situation.docx", "paquet.zip"):
        assert c.get(f"/donnees/{quoi}?province=Ituri").status_code == 200
    data = c.get("/donnees/paquet.zip").data
    tok = _csrf(c.get("/donnees").get_data(as_text=True))
    r = c.post("/donnees", data={"csrf": tok, "paquet": (io.BytesIO(data), "p.zip")},
               content_type="multipart/form-data")
    assert "3 déjà à jour" in r.get_data(as_text=True)
