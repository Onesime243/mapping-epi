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
    assert rules.suggest_event_risk(before, c)[0] == "Faible"            # incubation : non contagieux
    # état du cas : phase humide (+1) et phase critique (très élevé)
    c.phase_dds = "Phase sèche"
    soins = Event(type="Soins / consultation", date_debut=date(2026, 8, 20))
    assert rules.suggest_event_risk(soins, c)[0] == "Élevé"
    c.debut_phase_humide = date(2026, 8, 19)
    lvl, why = rules.suggest_event_risk(soins, c)
    assert lvl == "Très élevé" and "phase humide" in why
    c.events = [Event(type="Hospitalisation", date_debut=date(2026, 8, 22), description="gingivorragie")]
    lvl, why = rules.suggest_event_risk(Event(type="Activité communautaire", date_debut=date(2026, 8, 23)), c)
    assert lvl == "Très élevé" and "phase critique" in why


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
    assert set(stages) <= {"infection", "incubation", "seche", "humide", "critique", "deces"}
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


def test_exposition_estimee_sans_date_rapportee():
    """Cas trouvé décédé ou en phase humide : la date d'exposition est quand même estimée."""
    from core import rules
    c = Case(maladie="MVE", date_deces=date(2026, 8, 20))
    e = rules.estimer_j0(c)
    # décès en phase critique (J7 à J16) : J0 entre le 04/08 et le 13/08
    assert (e.j0_min, e.j0_max, e.source) == (date(2026, 8, 4), date(2026, 8, 13), "décès")
    assert rules.exposition_estimee(c) == (date(2026, 7, 14), date(2026, 8, 11))
    # phase humide datée le 15/08 (J4 à J7) + décès le 20/08 : intervalle commun 08/08 → 11/08
    c.debut_phase_humide = date(2026, 8, 15)
    e = rules.estimer_j0(c)
    assert (e.j0_min, e.j0_max) == (date(2026, 8, 8), date(2026, 8, 11))
    assert "phase humide" in e.source and "décès" in e.source
    assert rules.phases(c).exposition == (date(2026, 7, 18), date(2026, 8, 9))


def test_j0_selon_phase_des_premiers_signes():
    """La date rapportée est située dans une phase : J0 retenu = date − fin de la phase (sèche 3, humide 7, critique 16)."""
    from core import rules
    c = Case(maladie="MVE", debut_symptomes=date(2026, 11, 10))
    assert rules.j0_retenu(c) == date(2026, 11, 7)                       # phase non précisée : − 3 j
    c.phase_dds = "Phase humide"
    e = rules.estimer_j0(c)
    assert (e.j0, e.j0_min, e.j0_max) == (date(2026, 11, 3), date(2026, 11, 3), date(2026, 11, 3))
    ph = rules.phases(c)
    assert ph.recul == 7 and ph.humide == date(2026, 11, 10) and ph.humide_source == "rapportée"
    c.phase_dds = "Phase critique"
    ph = rules.phases(c)
    assert ph.j0 == date(2026, 10, 25) and ph.critique == date(2026, 11, 10)
    assert rules.phase_atteinte(c) == "critique"


def test_exposition_contact_connu():
    """Contact connu : pas d'estimation depuis son propre J0, mais le dernier contact ou le cas source."""
    from core import rules
    src = Case(code_cas="SRC-1", debut_symptomes=date(2026, 10, 15), date_deces=date(2026, 10, 25),
               events=[Event(type="Enterrement", date_debut=date(2026, 10, 26))])
    c = Case(debut_symptomes=date(2026, 11, 8), contact_connu="Contact connu", id_cas_source="SRC-1")
    assert rules.phases(c).exposition_source == "à rechercher"
    assert any("dernier contact" in m for m in rules.completeness(c)[1])
    ph = rules.phases(c, source=src)
    assert ph.exposition_source == "cas source" and ph.exposition == (date(2026, 10, 15), date(2026, 10, 26))
    c.date_contact_source = date(2026, 10, 24)
    ph = rules.phases(c, source=src)
    assert ph.exposition == (date(2026, 10, 24), date(2026, 10, 24)) and ph.exposition_source == "dernier contact"


def test_risque_global_etat_des_contacts():
    from core import rules
    from core.models import ContactGroup
    c = Case(debut_symptomes=date(2026, 11, 1), phase_dds="Phase humide",
             events=[Event(type="Soins / consultation", date_debut=date(2026, 11, 2), personnes="soignants")])
    lvl, why = rules.global_risk(c)
    assert lvl == "Très élevé" and "contacts non" in why                 # phase humide sans contacts listés
    c.contacts = [ContactGroup(categorie="Famille", nombre=5)]
    c.phase_dds = "Phase sèche"
    c.contact_connu = "Non contact"
    lvl, why = rules.global_risk(c)
    assert "non connu comme contact" in why
