"""Onglets du formulaire de saisie (un cas = une fiche)."""
from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QProgressBar,
                               QPushButton, QSpinBox, QTextBrowser, QVBoxLayout, QWidget)

from config import theme
from core import rules
from core.models import Action, Case, ContactGroup, Event, IPCSite, LabSample, Place
from core import pyramide
from core.schema import ACTION_COLS, CONTACT_COLS, EVENT_COLS, IPC_COLS, LAB_COLS, PLACE_COLS
from ui.widgets import DateField, OptionalNumber, SearchCombo, TableEditor


def _combo(items, editable=False) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    cb.setEditable(editable)
    return cb


def _hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setObjectName("hint")
    return lab


class IdentityTab(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        f = QFormLayout()
        f.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        f.setHorizontalSpacing(16)
        f.setVerticalSpacing(10)
        box = QWidget()
        box.setMaximumWidth(760)
        box.setLayout(f)
        outer.addWidget(box)
        outer.addStretch(1)
        self.rang = QSpinBox()
        self.rang.setRange(0, 9999)
        self.rang.setSpecialValueText("?")
        self.maladie = _combo(theme.DISEASES, editable=True)
        self.statut = _combo(theme.CASE_STATUS)
        self.sexe = _combo(theme.SEXES)
        self.age = OptionalNumber(placeholder="âge (vide si inconnu)")
        self.age_unite = _combo(["ans", "mois"])
        age_row = QHBoxLayout()
        age_row.addWidget(self.age)
        age_row.addWidget(self.age_unite)
        self.profession = QLineEdit()
        self.pyr = pyramide.get()
        self.province = SearchCombo("Choisir la province…")
        self.zs = SearchCombo("Choisir la zone de santé…")
        self.aire_sante = SearchCombo("Choisir ou saisir l'aire de santé…")
        self.province.set_items(self.pyr.provinces())
        self.zs.set_items(self.pyr.zones())
        self.aire_sante.set_items(self.pyr.aires())
        self.province.changed.connect(self._province_changed)
        self.zs.changed.connect(self._zs_changed)
        self.village = QLineEdit()
        self.lat = QDoubleSpinBox()
        self.lon = QDoubleSpinBox()
        for s, lim in ((self.lat, 90), (self.lon, 180)):
            s.setRange(-lim - 1, lim)
            s.setDecimals(5)
            s.setSpecialValueText("—")
            s.setValue(s.minimum())
        gps = QHBoxLayout()
        gps.addWidget(QLabel("Lat."))
        gps.addWidget(self.lat)
        gps.addWidget(QLabel("Long."))
        gps.addWidget(self.lon)
        self.date_confirmation = DateField()
        self.issue = _combo(theme.ISSUE_CHOICES)
        self.risque_global = _combo(["Automatique"] + theme.RISK_CHOICES)
        self.investigateur = QLineEdit()
        self.date_investigation = DateField()
        self.note_pied = QLineEdit()

        f.addRow(_hint("Champs marqués * : indispensables au mapping. Une information inconnue reste inconnue : "
                       "ne rien inventer, elle s'affichera « ? »."))
        f.addRow("Rang du cas * (1er, 2e…)", self.rang)
        f.addRow("Maladie *", self.maladie)
        f.addRow("Statut", self.statut)
        f.addRow("Sexe *", self.sexe)
        f.addRow("Âge *", age_row)
        f.addRow("Profession", self.profession)
        f.addRow("Province", self.province)
        f.addRow("Zone de santé (ZS) *", self.zs)
        f.addRow("Aire de santé (AS) *", self.aire_sante)
        f.addRow("Village / quartier", self.village)
        f.addRow("Coordonnées GPS", gps)
        f.addRow("Date de confirmation *", self.date_confirmation)
        f.addRow("Issue *", self.issue)
        f.addRow("Risque global", self.risque_global)
        f.addRow("Investigateur *", self.investigateur)
        f.addRow("Date d'investigation", self.date_investigation)
        f.addRow("Note de bas de page", self.note_pied)
        for w in (self.rang,):
            w.valueChanged.connect(self.changed)
        for w in (self.lat, self.lon):
            w.valueChanged.connect(self.changed)
        for w in (self.maladie, self.statut, self.sexe, self.age_unite, self.issue, self.risque_global):
            w.currentTextChanged.connect(self.changed)
        for w in (self.province, self.zs, self.aire_sante):
            w.changed.connect(self.changed)
        for w in (self.age, self.profession, self.village,
                  self.investigateur, self.note_pied):
            w.textChanged.connect(self.changed)
        for w in (self.date_confirmation, self.date_investigation):
            w.dateChanged.connect(self.changed)

    def _province_changed(self, prov: str):
        self.zs.set_items(self.pyr.zones(prov) if prov.strip() else self.pyr.zones())
        self._zs_changed(self.zs.text())

    def _zs_changed(self, zs: str):
        prov = self.province.text()
        if zs.strip() and not prov:
            p = self.pyr.province_of(zs)
            if p:
                self.province.blockSignals(True)
                self.province.setText(p)
                self.province.blockSignals(False)
                prov = p
        self.aire_sante.set_items(self.pyr.aires(prov, zs) if zs.strip() else self.pyr.aires(prov))

    def remember_new(self):
        """Mémorise une aire de santé saisie qui n'existe pas encore dans la liste."""
        return self.pyr.remember(self.province.text(), self.zs.text(), self.aire_sante.text())

    def load(self, c: Case):
        self.rang.setValue(c.rang or 0)
        self.maladie.setCurrentText(c.maladie)
        self.statut.setCurrentText(c.statut)
        self.sexe.setCurrentText(c.sexe)
        self.age.set_value(c.age)
        self.age_unite.setCurrentText(c.age_unite)
        self.province.setText(c.province)
        self._province_changed(c.province)
        self.zs.setText(c.zs)
        self._zs_changed(c.zs)
        self.aire_sante.setText(c.aire_sante)
        for w, v in ((self.profession, c.profession), (self.village, c.village), (self.investigateur, c.investigateur),
                     (self.note_pied, c.note_pied)):
            w.setText(v)
        self.lat.setValue(c.lat if c.lat is not None else self.lat.minimum())
        self.lon.setValue(c.lon if c.lon is not None else self.lon.minimum())
        self.date_confirmation.set_value(c.date_confirmation)
        self.issue.setCurrentText(c.issue)
        self.risque_global.setCurrentText(c.risque_global or "Automatique")
        self.date_investigation.set_value(c.date_investigation)

    def save(self, c: Case):
        c.rang = self.rang.value() or None
        c.maladie = self.maladie.currentText().strip() or "Autre"
        c.statut = self.statut.currentText()
        c.sexe = self.sexe.currentText()
        c.age = self.age.value()
        c.age_unite = self.age_unite.currentText()
        c.profession = self.profession.text().strip()
        c.province, c.zs, c.aire_sante = self.pyr.canonical(self.province.text(), self.zs.text(),
                                                            self.aire_sante.text())
        c.village, c.investigateur = self.village.text().strip(), self.investigateur.text().strip()
        c.note_pied = self.note_pied.text().strip()
        c.lat = None if self.lat.value() == self.lat.minimum() else self.lat.value()
        c.lon = None if self.lon.value() == self.lon.minimum() else self.lon.value()
        c.date_confirmation = self.date_confirmation.value()
        c.issue = self.issue.currentText()
        rg = self.risque_global.currentText()
        c.risque_global = "" if rg == "Automatique" else rg
        c.date_investigation = self.date_investigation.value()


class ClinicTab(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.debut = DateField()
        self.deces = DateField()
        f.addRow("Début des symptômes (J0) *", self.debut)
        f.addRow("Date de décès", self.deces)
        lay.addLayout(f)
        lay.addWidget(_hint("J0 sert à calculer automatiquement la fenêtre d'exposition (J-21 → J-2 pour la MVE), "
                            "la période contagieuse et les jours relatifs affichés sur chaque étape."))
        box = QGroupBox("Symptômes")
        g = QGridLayout(box)
        self.checks: Dict[str, QCheckBox] = {}
        for i, s in enumerate(theme.SYMPTOMS):
            cb = QCheckBox(s + (" 🩸" if s in theme.HEMORRHAGIC else ""))
            cb.toggled.connect(self.changed)
            self.checks[s] = cb
            g.addWidget(cb, i // 3, i % 3)
        lay.addWidget(box)
        self.autres = QLineEdit()
        self.autres.setPlaceholderText("Autres symptômes (texte libre)")
        self.autres.textChanged.connect(self.changed)
        lay.addWidget(self.autres)
        lay.addStretch(1)
        self.debut.dateChanged.connect(self.changed)
        self.deces.dateChanged.connect(self.changed)

    def load(self, c: Case):
        self.debut.set_value(c.debut_symptomes)
        self.deces.set_value(c.date_deces)
        for s, cb in self.checks.items():
            cb.setChecked(s in c.symptomes)
        self.autres.setText(c.symptomes_autres)

    def save(self, c: Case):
        c.debut_symptomes = self.debut.value()
        c.date_deces = self.deces.value()
        c.symptomes = [s for s, cb in self.checks.items() if cb.isChecked()]
        c.symptomes_autres = self.autres.text().strip()


# ---------------------------------------------------------------------------


class TimelineTab(QWidget):
    changed = Signal()
    fill_gaps = Signal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(_hint("Une ligne = une étape du parcours, dans l'ordre d'affichage voulu (▲▼ pour réordonner). "
                            "Laisser « Risque » vide pour utiliser le risque suggéré. Les inconnues restent visibles."))
        self.editor = TableEditor(EVENT_COLS, Event, add_label="Ajouter une étape")
        b1 = QPushButton("Trier par date")
        b1.clicked.connect(self.sort_dates)
        b2 = QPushButton("Combler les trous (« Période à documenter »)")
        b2.clicked.connect(self.fill_gaps)
        self.editor.extra.addWidget(b1)
        self.editor.extra.addWidget(b2)
        self.editor.changed.connect(self.changed)
        lay.addWidget(self.editor)

    def sort_dates(self):
        from core.storage import parse_date

        def key(d):
            try:
                v = parse_date(d.get("date_debut"))
            except ValueError:
                v = None
            return (v is None, v or 0, d.get("heure", ""))
        self.editor.sort_by(key)

    def load(self, c: Case):
        self.editor.set_items(c.events)

    def save(self, c: Case):
        c.events = self.editor.get_items()


class SimpleTableTab(QWidget):
    changed = Signal()

    def __init__(self, cols, model, hint, add_label, attr):
        super().__init__()
        self.attr = attr
        lay = QVBoxLayout(self)
        lay.addWidget(_hint(hint))
        self.editor = TableEditor(cols, model, add_label=add_label)
        self.editor.changed.connect(self.changed)
        lay.addWidget(self.editor)

    def load(self, c: Case):
        self.editor.set_items(getattr(c, self.attr))

    def save(self, c: Case):
        setattr(c, self.attr, self.editor.get_items())


def places_tab():
    t = SimpleTableTab(PLACE_COLS,
        Place, "Lieux fréquentés et populations exposées. GPS facultatif : avec au moins deux lieux géolocalisés, "
               "la carte du parcours devient géographique.", "Ajouter un lieu", "places")
    t.prefill = QPushButton("Pré-remplir depuis la chronologie")
    t.editor.extra.addWidget(t.prefill)
    return t


def contacts_tab():
    t = SimpleTableTab(CONTACT_COLS,
        ContactGroup, "« ? » = nombre inconnu (jamais 0 par défaut). Le total « Minimum documenté » est calculé "
                      "automatiquement. La fin du suivi = dernier contact + durée de suivi de la maladie.",
        "Ajouter une catégorie", "contacts")
    t.import_btn = QPushButton("Importer une liste nominative (Excel)…")
    t.editor.extra.addWidget(t.import_btn)
    return t


def ipc_tab():
    return SimpleTableTab(IPC_COLS,
        IPCSite, "Documenter date / équipe / produit pour chaque décontamination.", "Ajouter un site", "ipc")


def lab_tab():
    return SimpleTableTab(LAB_COLS,
        LabSample, "Dates au format JJ/MM/AAAA HH:MM. Le délai prélèvement → résultat est calculé automatiquement.",
        "Ajouter un prélèvement", "labs")


class ActionsTab(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(_hint("Actions affichées sur le mapping. Si la liste est vide, les actions suggérées sont "
                            "affichées (marquées « à valider »)."))
        self.editor = TableEditor(ACTION_COLS, Action, add_label="Ajouter une action")
        self.editor.changed.connect(self.changed)
        lay.addWidget(self.editor, 3)
        box = QGroupBox("Actions suggérées par les règles (cocher puis valider)")
        bl = QVBoxLayout(box)
        self.sugg = QListWidget()
        bl.addWidget(self.sugg)
        row = QHBoxLayout()
        self.accept_btn = QPushButton("✓ Ajouter la sélection")
        self.reject_btn = QPushButton("✕ Ignorer la sélection")
        self.reset_btn = QPushButton("Rétablir les suggestions ignorées")
        for b in (self.accept_btn, self.reject_btn, self.reset_btn):
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box, 2)

    def show_suggestions(self, suggestions):
        self.sugg.clear()
        existing = set()
        for r in range(self.editor.table.rowCount()):
            it = self.editor.table.item(r, 0)
            if it:
                existing.add(it.text().strip())
        for s in suggestions:
            if s.texte in existing:
                continue
            it = QListWidgetItem(f"[{s.priorite}] {s.texte}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            it.setToolTip(s.raison)
            it.setData(Qt.UserRole, (s.texte, s.priorite))
            it.setForeground(QColor(theme.RED) if s.priorite == "Urgent" else QColor(theme.TEXT))
            self.sugg.addItem(it)

    def checked(self) -> List[tuple]:
        return [self.sugg.item(i).data(Qt.UserRole) for i in range(self.sugg.count())
                if self.sugg.item(i).checkState() == Qt.Checked]

    def load(self, c: Case):
        self.editor.set_items(c.actions)

    def save(self, c: Case):
        c.actions = self.editor.get_items()


class ChecksTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("<b>Complétude de la fiche</b>"))
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        row.addWidget(self.bar, 1)
        lay.addLayout(row)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        lay.addWidget(self.view)

    def update_from(self, c: Case, table_errors: List[str]):
        score, missing = rules.completeness(c)
        self.bar.setValue(score)
        w = rules.windows(c)
        p = rules.disease_params(c.maladie)
        cs = rules.contact_summary(c)
        grisk, why = rules.global_risk(c)
        issues = rules.check_consistency(c)
        col = {"erreur": theme.RED, "alerte": theme.ORANGE, "info": theme.BLUE}
        html = [f"<h3 style='color:{theme.NAVY}'>Synthèse automatique</h3><ul>"]
        html.append(f"<li><b>Risque global :</b> <span style='color:{theme.risk_color(grisk)}'><b>{grisk}</b></span> — {why}</li>")
        if w.exposition:
            html.append(f"<li><b>Fenêtre d'exposition probable :</b> {w.exposition[0]:%d/%m/%Y} → {w.exposition[1]:%d/%m/%Y} "
                        f"(J-{p['incubation_max']} → J-{p['incubation_min']})</li>")
        else:
            html.append("<li><b>Fenêtre d'exposition :</b> renseigner la date de début des symptômes (onglet Clinique).</li>")
        if w.contagiosite:
            html.append(f"<li><b>Période contagieuse :</b> {w.contagiosite[0]:%d/%m/%Y} → {w.contagiosite[1]:%d/%m/%Y}</li>")
        html.append(f"<li><b>Contacts :</b> {cs.phrase}"
                    + (f" Suivi : {cs.suivis}/{cs.total_connu} ({cs.pct_suivi:.0f} %)." if cs.pct_suivi is not None else "") + "</li>")
        d = rules.lab_delay_hours(c)
        if d is not None:
            html.append(f"<li><b>Délai laboratoire :</b> {d:.0f} h (seuil d'alerte {p['labo_delai_alerte_h']} h)</li>")
        html.append("</ul>")
        if table_errors:
            html.append(f"<h3 style='color:{theme.RED}'>Saisies invalides (cellules en rouge)</h3><ul>")
            html += [f"<li>{e}</li>" for e in table_errors]
            html.append("</ul>")
        html.append(f"<h3 style='color:{theme.NAVY}'>Contrôles de cohérence</h3>")
        if issues:
            html.append("<ul>")
            for i in issues:
                html.append(f"<li><span style='color:{col[i.niveau]}'><b>{i.niveau.upper()}</b></span> — {i.message}</li>")
            html.append("</ul>")
        else:
            html.append("<p style='color:#2E8B57'>Aucune incohérence détectée.</p>")
        html.append(f"<h3 style='color:{theme.NAVY}'>Informations critiques manquantes</h3>")
        html.append("<ul>" + "".join(f"<li>{m}</li>" for m in missing) + "</ul>" if missing
                    else "<p style='color:#2E8B57'>Fiche complète.</p>")
        self.view.setHtml("".join(html))
