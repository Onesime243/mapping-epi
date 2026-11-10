"""Modèles Word / PowerPoint du narratif : tous les champs de l'Excel, lus exactement à l'import."""
import pytest

from core import modele_narratif as M, narratif


@pytest.mark.parametrize("ext", [".docx", ".pptx"])
def test_aller_retour(tmp_path, demo, ext):
    demo.code_cas, demo.province, demo.contact_connu, demo.id_cas_source = "KC-TUM-26-003", "Kongo-Central", "Contact connu", "KC-TUM-26-001"
    f = tmp_path / f"narratif{ext}"
    (M.generer_docx if ext == ".docx" else M.generer_pptx)(f, demo)
    res = narratif.importer(f)
    c = res.case
    assert res.trouves[0].startswith("modèle Mapping Épi reconnu") and not res.manquants
    for k in ("code_cas", "rang", "maladie", "sexe", "age", "province", "zs", "aire_sante", "debut_symptomes",
              "date_confirmation", "issue", "date_deces", "contact_connu", "id_cas_source", "symptomes", "investigateur"):
        assert getattr(c, k) == getattr(demo, k), k
    for attr in ("events", "places", "contacts", "ipc", "labs", "actions"):
        a, b = getattr(demo, attr), getattr(c, attr)
        assert len(a) == len(b), attr
        for x, y in zip(a, b):
            dx, dy = x.model_dump(exclude={"id", "auto"}), y.model_dump(exclude={"id", "auto"})
            assert {k: str(v).replace("’", "'") for k, v in dx.items()} == {k: str(v) for k, v in dy.items()}, attr


@pytest.mark.parametrize("ext", [".docx", ".pptx"])
def test_modele_vierge_et_saisie_manuelle(tmp_path, ext):
    f = tmp_path / f"vierge{ext}"
    (M.generer_docx if ext == ".docx" else M.generer_pptx)(f)
    res = narratif.importer(f)
    assert res.trouves[0].startswith("modèle Mapping Épi reconnu") and not res.case.events
    # saisie à la main dans le modèle : casse / accents différents des listes, oui / ?, N° reliant les deux tableaux
    if ext == ".docx":
        import docx
        d = docx.Document(str(f))
        tabs = d.tables
    else:
        from pptx import Presentation
        d = Presentation(str(f))
        tabs = [s.table for sl in d.slides for s in sl.shapes if getattr(s, "has_table", False) and s.has_table]
    champs = [t for t in tabs if t.rows[0].cells[0].text.strip() == "Champ"]
    for t in champs:
        for r in t.rows:
            lab = r.cells[0].text.strip()
            val = {"ID du cas": "IT-FAT-26-002", "Sexe": "f", "Âge": "29", "Début symptômes": "03/11/2026",
                   "Issue": "deces", "Maladie": "mve"}.get(lab)
            if val:
                r.cells[1].text = val
    t1 = next(t for t in tabs if t.rows[0].cells[0].text.strip() == "N°" and "Date début" in t.rows[0].cells[1].text)
    t2 = next(t for t in tabs if t.rows[0].cells[0].text.strip() == "N°" and "Description" in t.rows[0].cells[1].text)
    h1 = [c.text.strip() for c in t1.rows[0].cells]
    h2 = [c.text.strip() for c in t2.rows[0].cells]
    t1.rows[1].cells[h1.index("Date début")].text = "05/11/2026"
    t1.rows[1].cells[h1.index("Lieu")].text = "HGR Fataki"
    t1.rows[1].cells[h1.index("Type")].text = "hospitalisation"
    t2.rows[1].cells[h2.index("Personnes présentes")].text = "Soignants"
    t2.rows[1].cells[h2.index("Sans PCI")].text = "oui"
    ct = next(t for t in tabs if t.rows[0].cells[0].text.strip() == "Catégorie")
    ct.rows[1].cells[0].text, ct.rows[1].cells[2].text = "Famille", "?"
    d.save(str(f))
    c = narratif.importer(f).case
    assert (c.code_cas, c.sexe, c.age, c.issue, c.maladie) == ("IT-FAT-26-002", "F", 29, "Décès", "MVE")
    assert len(c.events) == 1 and c.events[0].type == "Hospitalisation" and c.events[0].sans_pci
    assert c.events[0].personnes == "Soignants" and c.events[0].lieu == "HGR Fataki"
    assert len(c.contacts) == 1 and c.contacts[0].nombre is None


def test_ancien_narratif_libre_inchange(tmp_path):
    import docx
    d = docx.Document()
    d.add_paragraph("Le 12/08/2026 consultation au CS Bolebole pour fièvre.")
    f = tmp_path / "libre.docx"
    d.save(str(f))
    res = narratif.importer(f)
    assert not res.trouves[0].startswith("modèle Mapping Épi")
