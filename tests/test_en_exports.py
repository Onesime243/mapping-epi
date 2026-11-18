"""Exports et textes d'analyse en anglais (core/langue.py, config/en/exports.py) ; en français, rien ne change.

Liste des cas Excel, rapport de situation Word, PCI Excel, symptômes, doublons, chaînes ; tableau de bord, riposte,
indicateurs ; mapping PowerPoint, rapport PowerPoint, rapports par pilier Word / PowerPoint.
"""
from datetime import date, timedelta

from core import alertes_suivi as AS
from core import echanges as ECH
from core import indicateurs as IND
from core import pci_lieux as PCI
from core import riposte as R
from core import tableau_bord as TB
from core.langue import utiliser
from core.models import Action, Case, ContactGroup, Event, IPCSite

REF = date(2026, 11, 12)


def _cas(code, zs="Bunia", j0=date(2026, 11, 1), **kw) -> Case:
    return Case(code_cas=code, province="Ituri", zs=zs, aire_sante="Lembabo", debut_symptomes=j0,
                phase_dds="Phase sèche", date_notification=j0 + timedelta(days=2), **kw)


def jeu():
    a = _cas("RDC-ITU-BUN-26-001", contact_connu="Contact connu suivi", agent_sante="Oui", symptomes=["Fièvre", "Diarrhée"],
             events=[Event(type="Hospitalisation", date_debut=date(2026, 11, 3), titre="Hospitalisé, fièvre et vomissements")],
             contacts=[ContactGroup(categorie="Famille", nombre=10, suivis=9)],
             actions=[Action(texte="Lister les contacts", priorite="Urgent", responsable="EPI ZS",
                             echeance=date(2026, 11, 8))])
    b = _cas("RDC-ITU-BUN-26-002", contact_connu="Non contact", issue="Décès", date_deces=date(2026, 11, 9),
             id_cas_source="RDC-ITU-BUN-26-001",
             events=[Event(type="Enterrement", date_debut=date(2026, 11, 10), securise=False)],
             actions=[Action(texte="Décontaminer le ménage", statut="Fait")])
    c = _cas("RDC-ITU-FAT-26-001", zs="Fataki", j0=date(2026, 10, 1), contact_connu="Inconnu")
    return [a, b, c]


def _liste(tmp_path, lang):
    from openpyxl import load_workbook
    with utiliser(lang):
        ECH.liste_cas_xlsx(jeu(), tmp_path / f"l_{lang}.xlsx", "Ituri")
    return load_workbook(tmp_path / f"l_{lang}.xlsx")


def test_liste_cas_en_anglais(tmp_path):
    wb = _liste(tmp_path, "en")
    assert wb.sheetnames == ["Case list", "Modelling", "Variables", "Symptoms by phase", "Symptoms by date",
                             "Symptoms (detail)", "Frequency by phase"]
    ws = wb["Case list"]
    assert ws["A1"].value.startswith("Mapping Épi case list: Ituri · 3 case(s) · extracted on ")
    entetes = [c.value for c in ws[2]]
    assert entetes[:4] == ["EPID number", "Province", "Health zone", "Health area"]
    assert "Retained D0" in entetes and "Overall risk" in entetes and "Zone de santé" not in entetes
    valeurs = {c.value for row in ws.iter_rows(min_row=3) for c in row}
    assert {"Known contact under follow-up", "Not a contact", "Unknown", "Death", "Dry phase", "Yes"} <= valeurs
    assert "Bunia" in valeurs and "RDC-ITU-BUN-26-001" in valeurs           # valeurs saisies jamais traduites
    dico = {r[0].value: r[1].value for r in wb["Variables"].iter_rows(min_row=2) if r[0].value}
    assert dico["id_cas"] == "Case EPID number" and dico["enterrement_securise"] == "Safe and dignified burial"
    assert dico["Rule"].startswith("An empty cell = information not provided (never 0). Dates in dd/mm/yyyy")
    assert [c.value for c in wb["Modelling"][1]][:2] == ["id_cas", "province"]   # noms de variables : stables
    det = [[c.value for c in r] for r in wb["Symptoms (detail)"].iter_rows(min_row=2)]
    assert any(r[3] == "Fever" for r in det) and any(r[5] == "record checklist" for r in det)
    assert all(r[2] in ("Dry phase", "Wet phase", "Critical phase", "Before D0", "Symptomatic phase", "Undated")
               for r in det)
    freq = [c.value for c in wb["Frequency by phase"]["A"] if c.value]
    assert freq[0].startswith("Most frequent symptoms by phase") and any(" documented case(s)" in v for v in freq)
    jours = [c.value for c in wb["Symptoms by date"]["E"][1:] if c.value]
    assert jours and all(j.startswith("D") for j in jours)


def test_liste_cas_en_francais_inchangee(tmp_path):
    wb = _liste(tmp_path, "fr")
    assert wb.sheetnames[0] == "Liste des cas" and "Modélisation" in wb.sheetnames
    ws = wb["Liste des cas"]
    assert ws.cell(2, 1).value == "N° EPID" and ws.cell(2, 3).value == "Zone de santé"
    assert ws["A1"].value.startswith("Liste des cas Mapping Épi : Ituri · 3 cas · extraite le ")
    valeurs = {c.value for row in ws.iter_rows(min_row=3) for c in row}
    assert {"Contact connu suivi", "Non contact", "Décès", "Phase sèche", "Oui"} <= valeurs
    jours = [c.value for c in wb["Symptômes par date"]["E"][1:] if c.value]
    assert jours and all(j.startswith("J") for j in jours)


def test_rapport_situation_word(tmp_path):
    from docx import Document

    def texte(lang):
        with utiliser(lang):
            ECH.rapport_docx(jeu(), tmp_path / f"r_{lang}.docx", "Ituri", 21, REF)
        d = Document(tmp_path / f"r_{lang}.docx")
        return "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells])
    en, fr = texte("en"), texte("fr")
    assert "SITUATION REPORT: EBOLA VIRUS DISEASE" in en and "1. General situation" in en
    assert "Confirmed cases" in en and "Health zones affected" in en and "Since the start" in en
    assert "Scope: Ituri" in en and "situation as of 12/11/2026" in en and "Priority" in en and "\nHZ\n" in en
    assert "RAPPORT DE SITUATION" in fr and "Points d'attention" in fr and "Cas confirmés" in fr


def test_pci_excel(tmp_path):
    from openpyxl import load_workbook
    c0 = Case(code_cas="EQ-TUM-009", province="Equateur", zs="Tumba",
              events=[Event(lieu="CS Nzala", date_debut=date(2026, 7, 19), type="Début maladie"),
                      Event(lieu="Marché central", date_debut=date(2026, 7, 21), titre="Marché")],
              ipc=[IPCSite(site="CS Nzala", statut="Décontaminé", adresse="Av. du Marché 12")])
    with utiliser("en"):
        PCI.xlsx([c0], tmp_path / "p_en.xlsx", "Equateur")
        rows = PCI.lignes([c0])
    PCI.xlsx([c0], tmp_path / "p_fr.xlsx", "Equateur")
    wb = load_workbook(tmp_path / "p_en.xlsx")
    assert wb.sheetnames == ["Places and addresses", "Summary by case"]
    ws = wb["Places and addresses"]
    assert [c.value for c in ws[2]][:5] == ["Case ID", "Province", "Health zone", "Health area", "Place visited"]
    assert "Address" in [c.value for c in ws[2]] and ws["A1"].value.startswith("IPC: places visited and addresses")
    vals = [[c.value for c in r] for r in ws.iter_rows(min_row=3)]
    assert vals[0][5] == "Care pathway + IPC site" and vals[0][9] == "Decontaminated" and "Illness onset" in vals[0][7]
    assert vals[1][9] == "No IPC site entered" and vals[1][8] == "?"
    assert PCI.bilan(rows)["sans_site"] == 1                     # le bilan reste juste en anglais
    wf = load_workbook(tmp_path / "p_fr.xlsx")
    assert wf.sheetnames == ["Lieux et adresses", "Résumé par cas"]
    assert [c.value for c in wf["Lieux et adresses"][2]][0] == "ID du cas"
    assert [[c.value for c in r] for r in wf["Lieux et adresses"].iter_rows(min_row=3)][1][9] == "Pas de site PCI saisi"


def test_bilan_paquet_doublons_chaines():
    from core import doublons as DB
    from core.links import build_chains, case_long_label
    b = ECH.Bilan(ajoutees=["A"], identiques=2)
    with utiliser("en"):
        assert b.texte() == "1 record(s) added; 0 updated; 2 already up to date."
    assert b.texte() == "1 fiche(s) ajoutée(s) ; 0 mise(s) à jour ; 2 déjà à jour."
    x, y = _cas("X-1"), _cas("X-1")
    with utiliser("en"):
        d = DB.doublons([x, y])[0]
        assert d.raison == "same EPID number (X-1)" and d.certitude == "forte"
        assert case_long_label(x).endswith("· HZ Bunia")
        assert build_chains(jeu()).roots
    assert DB.doublons([x, y])[0].raison == "même N° EPID (X-1)" and case_long_label(x).endswith("· ZS Bunia")


# -- tableau de bord, riposte, indicateurs -------------------------------------------------------------------------------
REF_B = date(2026, 11, 15)


def _cas_b(code, zs="Bunia", j0=date(2026, 11, 1), **kw) -> Case:
    return Case(code_cas=code, province="Ituri", zs=zs, aire_sante="Lembabo", debut_symptomes=j0,
                phase_dds="Phase sèche", date_notification=j0 + timedelta(days=2), **kw)


def jeu_b():
    a = _cas_b("RDC-ITU-BUN-26-001", contact_connu="Contact connu suivi",
             date_confirmation=date(2026, 11, 12),
             events=[Event(type="Hospitalisation", date_debut=date(2026, 11, 3))],
             contacts=[ContactGroup(categorie="Famille", nombre=12, suivis=0, risque="Haut")],
             ipc=[IPCSite(site="Maison", statut="Non")],
             actions=[Action(texte="Lister les contacts", priorite="Urgent", echeance=date(2026, 11, 2)),
                      Action(texte="Décontaminer", statut="Fait")])
    b = _cas_b("RDC-ITU-MAN-26-002", zs="Mandima", j0=date(2026, 10, 20), contact_connu="Non contact", issue="Décès")
    return [a, b]


def test_tableau_de_bord_en():
    with utiliser("en"):
        tb = TB.construire(jeu_b(), date(2026, 9, 1), date(2026, 11, 12), ref=REF_B)
        titres = [t.titre for t in tb.tuiles]
        assert titres == ["Mapped cases", "Verified actions", "Delay symptoms → confirmation",
                          "Exposure places decontaminated"]
        assert "average completeness" in tb.tuiles[0].detail
        assert all(t.serie_txt and "semaine" not in t.serie_txt for t in tb.tuiles)
        textes = [a.texte for a in tb.alertes]
        assert any("high-risk contacts listed, none followed up" in t for t in textes)
        assert any("urgent action(s) overdue" in t for t in textes)
        assert any("reported as done without proof" in t for t in textes)
        g = tb.groupes[0]
        assert "texte_fr" in g["liste"][0] and "aucun en suivi" in g["liste"][0]["texte_fr"]
        assert [lib for _k, lib, _c in TB.CATEGORIES][0] == "Verified" and TB.LIB_CAT["retard"] == "Overdue"
        assert 'title="Overdue: 2"' in TB.barre_empilee({"retard": 2})
        svg = TB.svg_semaines(tb.semaines)
        assert "Week of" in svg and "Semaine" not in svg
        assert tb.cas[0].statut == "Critique"          # clé interne, comparée dans le gabarit : reste en français
    # français inchangé
    tb = TB.construire(jeu_b(), date(2026, 9, 1), date(2026, 11, 12), ref=REF_B)
    assert tb.tuiles[0].titre == "Cas mappés" and TB.LIB_CAT["retard"] == "En retard"
    assert any("aucun en suivi" in a.texte for a in tb.alertes)


def test_signature_alertes_toutes_langues():
    with utiliser("en"):
        tb = TB.construire(jeu_b(), date(2026, 9, 1), date(2026, 11, 12), ref=REF_B)
    g = tb.groupes[0]
    sig_fr = AS.signature(it["texte_fr"] for it in g["liste"])
    AS.appliquer([g], {g["cid"]: {"etat": "resolue", "signature": sig_fr}})
    assert g["etat"] == "reapparue"


def test_riposte_en():
    with utiliser("en"):
        ind = R.indicateurs(jeu_b())
        noms = [i.nom for i in ind]
        assert "New cases already known as contacts" in noms and "Community deaths" in noms
        groupes = {i.groupe for i in ind}
        assert {"Detection", "Delays", "Ring vaccination", "Data quality"} <= groupes
        d = next(i for i in ind if i.unite != "%")
        assert d.unite == "d" and d.cible == "≤ 3 d"
        frag = R.html_indicateurs(ind)
        assert "target" in frag and "Détection" not in frag
        cb = R.courbe(jeu_b())
        svg = R.courbe_svg(cb)
        assert "Epidemic curve" in svg and "death" in svg and "semaine" not in svg
        items = R.actions_ouvertes(jeu_b(), REF_B)
        tab = R.html_actions(items)
        assert "<th>Priority</th>" in tab and "<th>HZ</th>" in tab and "d overdue" in tab and "Urgent" in tab
        pts = R.points_attention(ind, [], [], items)
        assert any("target" in p for p in pts) and all("cible" not in p for p in pts)
        assert "secondary" in R.reproduction(jeu_b(), REF_B, 5).note or "no case" in R.reproduction(jeu_b(), REF_B, 5).note
        assert 'lang="en"' in R.page_bureau("x", "")
    ind = R.indicateurs(jeu_b())
    assert ind[0].groupe == "Détection" and ind[0].nom == "Nouveaux cas déjà connus comme contacts"
    assert "<th>ZS</th>" in R.html_actions(R.actions_ouvertes(jeu_b(), REF_B))


def test_indicateurs_en():
    with utiliser("en"):
        z = IND.zones(jeu_b(), REF_B)
        assert z[0].cat["nom"] in ("Active transmission", "Spaced notification", "21 to 42 days without cases",
                                   "More than 42 days without cases")
        al = IND.alertes_foyers(jeu_b())
        assert al and al[0].niveau in ("HZ", "HA") and "HZ" in al[0].texte
        st = IND.delais(jeu_b())
        assert st[0].nom == "Symptom onset → notification" and st[0].texte().startswith("median")
    # la configuration lue n'est pas modifiée
    assert IND.config()["categories"][0]["nom"] == "Transmission active"
    al = IND.alertes_foyers(jeu_b())
    assert al[0].niveau in ("ZS", "AS") and "ZS" in al[0].texte

# -- mapping PowerPoint, rapport PowerPoint, rapports par pilier ------------------------------------------------------
def _textes_pptx(path):
    from pptx import Presentation
    out = []
    for sl in Presentation(str(path)).slides:
        for s in sl.shapes:
            if s.has_text_frame:
                out.append(s.text_frame.text)
            if getattr(s, "has_chart", False) and s.has_chart:
                ch = s.chart
                out.append(ch.chart_title.text_frame.text if ch.has_title else "")
                out += [str(c) for c in ch.plots[0].categories] + [x.name for x in ch.series]
    return "\n".join(out)


def test_mapping_pptx_en(demo, tmp_path):
    from render.pptx_exporter import add_mapping_slide, export_mapping_pptx, export_report_pptx, new_presentation
    with utiliser("en"):
        export_mapping_pptx(demo, tmp_path / "m_en.pptx")
        export_report_pptx(demo, [], tmp_path / "r_en.pptx")
        prs = new_presentation()
        add_mapping_slide(prs, demo)
        prs.save(str(tmp_path / "old_en.pptx"))
    export_mapping_pptx(demo, tmp_path / "m_fr.pptx")
    en, fr = _textes_pptx(tmp_path / "m_en.pptx"), _textes_pptx(tmp_path / "m_fr.pptx")
    for t in ("PATHWAY CHRONOLOGY", "CONTACTS TO IDENTIFY / FOLLOW UP", "IPC / DECONTAMINATION", "ACTIONS",
              "D±n: days since the retained D0", "? to count", "? people present"):
        assert t in en, t
    for t in ("CHRONOLOGIE DU PARCOURS", "à dénombrer", "jours depuis le J0", "PCI / DÉCONTAMINATION"):
        assert t not in en, t
    assert "CHRONOLOGIE DU PARCOURS" in fr and "? à dénombrer" in fr and "J±n : jours depuis le J0" in fr
    assert "PATHWAY CHRONOLOGY" in _textes_pptx(tmp_path / "r_en.pptx")
    old = _textes_pptx(tmp_path / "old_en.pptx")
    assert "PATHWAY CHRONOLOGY" in old and "PLACES & EXPOSURES" in old and "D±n: days since" in old


def _rapport_piliers(lang):
    from core import piliers as P
    with utiliser(lang):
        return P.construire(jeu() + jeu_b(), date(2026, 9, 1), date(2026, 11, 12), province="Ituri", perimetre="Ituri")


def test_rapport_piliers_en(tmp_path):
    from docx import Document
    from core import rapport_rendu as RR
    r = _rapport_piliers("en")
    assert [s.titre for s in r.sections] == ["Surveillance and investigation", "Contacts and vaccination",
                                             "Infection prevention and control (IPC)", "Laboratory and case management",
                                             "Actions and coordination", "Data quality"]
    assert r.resume[0].startswith("5 case(s) notified from ") and " in Ituri " in r.resume[0]
    assert r.sections[0].kpis[0][0] == "Cases notified" and r.sections[2].graphiques[0].categories == \
        ["Decontaminated", "Partial", "No", "Unknown"]
    assert r.non_couverts[0][0] == "A. Coverage"
    assert all("?" in v or v[0].isdigit() for _k, v in r.sections[1].kpis)     # « ? » jamais remplacé par 0
    with utiliser("en"):
        RR.rapport_docx(r, tmp_path / "r.docx")
        RR.rapport_pptx(r, tmp_path / "r.pptx")
        png = RR.graphique_png(r.sections[2].graphiques[0])
    assert png[:4] == b"\x89PNG"
    d = Document(tmp_path / "r.docx")
    txt = "\n".join([p.text for p in d.paragraphs] + [c.text for t in d.tables for row in t.rows for c in row.cells])
    for t in ("ANALYSIS REPORT BY PILLAR", "Executive summary", "Analysis questions", "Points of attention",
              "Appendix: questions not covered for lack of data", "Key indicator", "Period", "Data needed"):
        assert t in txt, t
    for t in ("RAPPORT D'ANALYSE", "Questions d'analyse", "Résumé exécutif", "Annexe"):
        assert t not in txt, t
    pp = _textes_pptx(tmp_path / "r.pptx")
    assert "Analysis report by pillar" in pp and "Key messages" in pp and "Status of IPC sites" in pp
    assert "Questions not covered and next steps" in pp and "Messages clés" not in pp


def test_rapport_piliers_fr_inchange(tmp_path):
    from docx import Document
    from core import rapport_rendu as RR
    r = _rapport_piliers("fr")
    assert r.sections[0].titre == "Surveillance et investigation" and r.sections[0].kpis[0][0] == "Cas notifiés"
    assert r.resume[0].startswith("5 cas notifiés du 01/09/2026 au 12/11/2026 en Ituri")
    RR.rapport_docx(r, tmp_path / "r.docx")
    txt = "\n".join(p.text for p in Document(tmp_path / "r.docx").paragraphs)
    assert "RAPPORT D'ANALYSE PAR PILIER" in txt and "Questions d'analyse" in txt and "Résumé exécutif" in txt
