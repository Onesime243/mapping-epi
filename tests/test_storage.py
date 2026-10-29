from openpyxl import Workbook

from core import storage


def test_json_roundtrip(demo, tmp_path):
    p = tmp_path / "c.json"
    storage.save_json(demo, p)
    assert storage.load_json(p) == demo


def test_sqlite_versions(demo, tmp_path):
    st = storage.Store(tmp_path / "db.sqlite")
    st.save(demo, version=True, commentaire="v1")
    demo.age = 33
    st.save(demo, version=True, commentaire="v2")
    assert st.load(demo.id).age == 33
    vs = st.versions(demo.id)
    assert len(vs) == 2
    old = st.load_version(vs[-1][0])
    assert old.age == 41
    assert any("age" in d for d in storage.diff_cases(old, demo))
    st.close()


def test_excel_roundtrip(demo, tmp_path):
    p = tmp_path / "c.xlsx"
    storage.export_excel(demo, p)
    back = storage.import_excel(p)
    assert len(back.events) == len(demo.events)
    assert [g.nombre for g in back.contacts] == [g.nombre for g in demo.contacts]   # « ? » conservés
    assert back.debut_symptomes == demo.debut_symptomes
    assert back.labs[0].prelevement == demo.labs[0].prelevement
    assert back.events[5].heure_approx is True


def test_contact_list_import(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Nom", "Catégorie", "Lieu", "Dernier contact", "Suivi", "Risque"])
    ws.append(["A", "Famille & amis", "Monzombo", "29/07/2026", "oui", "Haut"])
    ws.append(["B", "Famille & amis", "Monzombo", "28/07/2026", "non", "Haut"])
    ws.append(["C", "Motard(s)", "Monzombo", "28/07/2026", "oui", "Très haut"])
    p = tmp_path / "liste.xlsx"
    wb.save(p)
    groups = {g.categorie: g for g in storage.import_contact_list(p)}
    assert groups["Famille & amis"].nombre == 2 and groups["Famille & amis"].suivis == 1
    assert groups["Motard(s)"].risque == "Très haut"
    assert str(groups["Famille & amis"].dernier_contact) == "2026-07-29"
