"""Import des anciens narratifs (Word / PowerPoint) : documents FICTIFS construits pour le test."""
from datetime import date

import docx
from pptx import Presentation
from pptx.util import Inches

from core import narratif


def _docx_fictif(path):
    d = docx.Document()
    d.add_paragraph("RAPPORT D'INVESTIGATION APPROFONDIE D'UN CAS CONFIRME DE LA MALADIE A VIRUS EBOLA DANS LA ZONE DE SANTE DE TUMBA")
    d.add_paragraph("VERSION EN DATE DU 06/11/2026")
    t = d.add_table(rows=0, cols=2)
    for k, v in [("CODE VHF", "DEMO 001"), ("AGE", "35 ans"), ("SEXE", "FEMININ"), ("PROFESSION", "MENAGERE"),
                 ("CELLULE et QUARTIER", "QUARTIER FICTIF"), ("AIRE DE SANTE", "NZALA"), ("ZONE DE SANTE", "TUMBA"),
                 ("DATE DE CONFIRMATION", "05/11/2026"), ("DATE DE DÉBUT DES SYMPTOMES de la MVE", "28/ 10 / 2026"),
                 ("NATURE DU CAS", "VIVANT"), ("CAS CONTACT CONNU", "OUI"), ("PÉRIODE INVESTIGATION", "Du 04 au 06/11/ 2026")]:
        r = t.add_row().cells
        r[0].text, r[1].text = k, v
    d.add_paragraph("Cas contaminant : PERSONNE FICTIVE")
    d.add_paragraph("Lieu de contact : Communauté : dans leur famille à Villefictive")
    d.add_paragraph("B-HISTOIRE DE LA MALADIE et PARCOURS DU MALADE")
    d.add_paragraph("11/10/2026 au 24/10/2026 : probable contact avec le cas contaminant.")
    d.add_paragraph("28/10/2026 : début des signes de la MVE par une fièvre, céphalées et myalgie, automédiquée sans succès,")
    d.add_paragraph("Du 03 au 04/11/2026 : s'ajoutent les vomissements et diarrhée, consultation au CH Fictif, "
                    "où l'alerte été lancée, validée et isolée à la même date.")
    d.add_paragraph("C- LISTAGE CONTACTS")
    d.add_paragraph("Investigation approfondie : OUI")
    d.add_paragraph("Décontamination de l'ESS Fictif et ménage du cas : en cours")
    t2 = d.add_table(rows=0, cols=2)
    for k, v in [("LIEN DE CONTACT", "NOMBRE LISTÉS"), ("FAMILLE", "11"), ("VOISINS", "En cours"),
                 ("PERSONNELS SOIGNANTS", "16"), ("TOTAL", "27")]:
        r = t2.add_row().cells
        r[0].text, r[1].text = k, v
    d.save(path)


def test_narratif_word(tmp_path):
    p = tmp_path / "narratif.docx"
    _docx_fictif(p)
    res = narratif.importer(p)
    c = res.case
    assert (c.code_cas, c.age, c.sexe, c.zs, c.aire_sante) == ("DEMO 001", 35, "F", "Tumba", "Nzala")
    assert c.debut_symptomes == date(2026, 10, 28) and c.date_confirmation == date(2026, 11, 5)
    assert c.issue == "Vivant" and c.contact_connu == "Contact connu" and c.id_cas_source == "PERSONNE FICTIVE"
    types = [e.type for e in c.events]
    assert types[:2] == ["Exposition", "Début maladie"] and "Hospitalisation" in types
    assert c.events[0].date_fin == date(2026, 10, 24) and c.events[0].lieu == "Villefictive"
    assert {"Fièvre", "Vomissements", "Diarrhée"} <= set(c.symptomes)
    assert [(g.categorie, g.nombre) for g in c.contacts] == [("Famille", 11), ("Voisins", None), ("Personnels soignants", 16)]
    assert any(x.site == "ESS Fictif" and x.statut == "Partiel" for x in c.ipc)
    assert any(a.texte == "Investigation approfondie" and a.statut == "Fait" for a in c.actions)
    assert any(pl.nom == "CH Fictif" and pl.type == "Hôpital" for pl in c.places)


def test_narratif_powerpoint(tmp_path):
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Descriptif cas confirmé FICTIF ZS TUMBA"
    rows = [("Age", "26 ans"), ("Sexe", "Masculin"), ("Statut", "Confirmé"), ("Date de début des symptômes", "26/10/2026"),
            ("Zone de santé", "TUMBA"), ("Aire de Santé", "NZALA"), ("Etat actuel", "VIVANT"),
            ("Contact connu?", "Oui"), ("Source (si disponible)", "RDC KCE TUM 0003"),
            ("Observations :", "Histoire de la maladie:\nExposition estimée du 08 Octobre au 21 Octobre 2026.\n"
                               "Le 26/10/2026, DDS à domicile par céphalées et fièvre ;\n"
                               "Le 30/10/2026 : ajout des vomissements, consultation à l'HGR Fictif, alerte, prélevée\n"
                               "Le 02/11/2026 : l'échantillon expédié au laboratoire provincial de Fictiville\n"
                               "04/11/2026 : Rendu du résultat positif MVE\n"
                               "Actions de SP: Listage des contacts, soutien psychologique")]
    tbl = s.shapes.add_table(len(rows), 2, Inches(.3), Inches(1.5), Inches(9), Inches(5)).table
    for i, (k, v) in enumerate(rows):
        tbl.cell(i, 0).text, tbl.cell(i, 1).text = k, v
    p = tmp_path / "narratif.pptx"
    prs.save(p)
    c = narratif.importer(p).case
    assert (c.age, c.sexe, c.zs, c.debut_symptomes) == (26, "M", "Tumba", date(2026, 10, 26))
    assert c.id_cas_source == "RDC-KCE-TUM-0003"
    assert c.events[0].type == "Exposition" and c.events[0].date_debut == date(2026, 10, 8)
    assert c.date_confirmation == date(2026, 11, 4)            # déduite du résultat positif
    assert c.labs and c.labs[0].resultat == "Positif" and "Fictiville" in c.labs[0].laboratoire
    assert any(a.texte == "Soutien psychologique" for a in c.actions)


def test_dates_du_recit():
    t = narratif.trouver_periode
    assert t("Du 03 au 04/11/2026 : vomissements")[:2] == (date(2026, 11, 3), date(2026, 11, 4))
    assert t("Le 31/10 -01/11/2026 : isolement")[:2] == (date(2026, 10, 31), date(2026, 11, 1))
    assert t("Du 16 au 25 octobre 2026: garde malade")[:2] == (date(2026, 10, 16), date(2026, 10, 25))
    assert t("30/ 10 / 2026")[:2] == (date(2026, 10, 30), None)
