from datetime import date

from core import rules
from core.models import Case, ContactGroup, Event


def test_contact_summary_is_computed(demo):
    s = rules.contact_summary(demo)
    assert s.haut_risque_connu == 41
    assert s.termes == [24, 11, 6]
    assert s.categories_inconnues == 5
    assert s.phrase.startswith("Minimum documenté : 41 contacts à haut risque (24 + 11 + 6).")


def test_unknown_is_not_zero():
    c = Case(contacts=[ContactGroup(categorie="Motards", nombre=None), ContactGroup(categorie="Famille", nombre=0)])
    s = rules.contact_summary(c)
    assert s.categories_inconnues == 1
    assert s.total_connu == 0


def test_windows_mve(demo):
    w = rules.windows(demo)
    # J0 rapporté 19/07 → J0 retenu 16/07 (la maladie a commencé 3 jours avant)
    assert w.j0 == date(2026, 7, 16)
    assert w.exposition == (date(2026, 6, 25), date(2026, 7, 14))
    assert w.contagiosite == (date(2026, 7, 16), date(2026, 7, 29))   # jusqu'à l'enterrement


def test_event_phase_and_relative_day(demo):
    w = rules.windows(demo)
    ev = demo.events[0]
    assert rules.event_phase(ev, w) == "exposition"
    assert rules.relative_day(date(2026, 7, 16), w.j0) == "J0"
    assert rules.relative_day(date(2026, 7, 19), w.j0) == "J+3"


def test_risk_rules():
    c = Case(debut_symptomes=date(2026, 8, 18))
    burial = Event(type="Enterrement", date_debut=date(2026, 8, 29))
    assert rules.suggest_event_risk(burial, c)[0] == "Très élevé"
    safe = Event(type="Enterrement", date_debut=date(2026, 8, 29), securise=True)
    assert rules.suggest_event_risk(safe, c)[0] == "Contrôlé"
    hosp = Event(type="Hospitalisation", date_debut=date(2026, 8, 27), liquides=True)
    lvl, why = rules.suggest_event_risk(hosp, c)
    assert lvl == "Très élevé" and "liquides" in why
    before = Event(type="Soins / consultation", date_debut=date(2026, 8, 10))
    assert rules.suggest_event_risk(before, c)[0] == "Modéré"


def test_global_risk_auto(demo):
    demo.risque_global = ""
    assert rules.global_risk(demo)[0] == "Très élevé"


def test_consistency_detects_errors():
    c = Case(debut_symptomes=date(2026, 8, 18), date_deces=date(2026, 8, 10), issue="Décès",
             events=[Event(type="Hospitalisation", date_debut=date(2026, 8, 12)),
                     Event(type="Autre", date_debut=date(2026, 8, 20), date_fin=date(2026, 8, 19))])
    msgs = " | ".join(i.message for i in rules.check_consistency(c))
    assert "décès est daté avant l'hospitalisation" in msgs
    assert "fin précède" in msgs


def test_suggested_actions(demo):
    texts = [s.texte for s in rules.suggest_actions(demo)]
    assert "Boucler tous les contacts" in texts
    assert any(t.startswith("PCI / décontamination") for t in texts)
    assert "Identifier et suivre les motards" in texts
    demo.suggestions_rejetees = ["Boucler tous les contacts"]
    assert "Boucler tous les contacts" not in [s.texte for s in rules.suggest_actions(demo)]


def test_places_from_events():
    c = Case(events=[Event(lieu="Monzombo"), Event(lieu="HGR Tumba", type="Hospitalisation"), Event(lieu="Monzombo")])
    names = [p.nom for p in rules.places_from_events(c)]
    assert names == ["Monzombo", "HGR Tumba"]


def test_completeness(demo):
    score, missing = rules.completeness(demo)
    assert 80 <= score <= 100
    assert any("non dénombrée" in m for m in missing)


def test_phases_humide_detectee_et_dds_conservee(demo):
    from datetime import timedelta
    from core import rules
    ph = rules.phases(demo)
    assert ph.j0_rapporte == demo.debut_symptomes        # la date rapportée est conservée telle quelle
    j0 = demo.debut_symptomes - timedelta(days=3)        # J0 retenu
    assert ph.j0 == j0 and ph.recul == 3
    assert ph.exposition == (j0 - timedelta(days=21), j0 - timedelta(days=2))
    assert ph.humide and ph.humide >= j0
    stages = [rules.event_stage(e, ph) for e in demo.sorted_events() if e.date_debut]
    assert set(stages) <= {"infection", "incubation", "seche", "humide", "deces"}
    demo.debut_phase_humide = j0 + timedelta(days=1)
    assert rules.phases(demo).humide_source == "saisie"


def test_contact_connu_excel(demo, tmp_path):
    from core import storage
    demo.contact_connu = "Non contact"
    p = tmp_path / "c.xlsx"
    storage.export_excel(demo, p)
    assert storage.import_excel(p).contact_connu == "Non contact"


def test_contact_source_et_personnes_obligatoires(demo):
    from core import rules
    demo.contact_connu = "Contact connu"
    demo.id_cas_source = ""
    msgs = [i.message for i in rules.check_consistency(demo)]
    assert any("cas source" in m for m in msgs)
    demo.events[0].personnes = ""
    demo.events[0].type = "Exposition"
    assert demo.events[0] in rules.personnes_manquantes(demo)
    from render.html_renderer import render_mapping_html
    html = render_mapping_html(demo)
    assert "ID du cas source : à compléter" in html and "Personnes : à compléter" in html
    demo.id_cas_source = "RDC-TUM-26-001"
    assert "ID du cas source : à compléter" not in render_mapping_html(demo)
