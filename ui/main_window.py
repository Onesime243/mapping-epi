"""Fenêtre principale : liste des cas | formulaire | aperçu en direct."""
from __future__ import annotations

import logging
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QProcess, QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                               QPushButton, QScrollArea, QSplitter, QTabWidget, QTextBrowser, QToolBar, QToolButton,
                               QVBoxLayout, QWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView

from config import credits, theme
from core import rules, storage
from core.models import Action, Case, Event
from render import chains, common_places, dashboard, gantt, html_renderer as H, map_view, network
from render.pptx_exporter import export_mapping_pptx, export_report_pptx
from core.netinfo import WEB_PORT, lan_urls
from core.paths import data_dir
from core.users import Users
from ui.exporter import Exporter, pdf_pages_to_png
from ui.style import apply_theme
from ui.users_dialog import UsersDialog
from ui.forms import (ActionsTab, ChecksTab, ClinicTab, IdentityTab, TimelineTab, contacts_tab, ipc_tab, lab_tab,
                      places_tab)

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample_data" / "cas_exemple_fictif.json"


def _add(menu: QMenu, text: str, slot) -> QAction:
    a = QAction(text, menu)
    a.triggered.connect(lambda checked=False: slot())
    menu.addAction(a)
    return a


class Preview(QWebEngineView):
    """Vue web qui ajuste le zoom pour afficher la page 1280×720 entière."""
    def __init__(self):
        super().__init__()
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.page().setBackgroundColor(QColor(theme.BG))
        self._html = ""

    def set_page(self, html: str):
        if html == self._html:
            return
        self._html = html
        self.setHtml(html, QUrl.fromLocalFile(str(H.ASSETS) + "/"))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        z = min(self.width() / H.PAGE_W, self.height() / H.PAGE_H)
        self.setZoomFactor(max(0.25, min(z, 5.0)))


class _Relais(QObject):
    """Ramène dans la fenêtre les résultats des tâches en arrière-plan (synchronisation, nouvelle version)."""
    fini = Signal(bool, str)
    texte = Signal(str)


def slug(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE).strip("_")
    return s or "cas"


class MainWindow(QMainWindow):
    def __init__(self, store: storage.Store):
        super().__init__()
        self.store = store
        self.web_proc: Optional[QProcess] = None

        def _resolve_source(code: str):
            from core.links import _id
            k = _id(code)
            return next((x for x in self.store.all_cases() if k and x.code_cas and _id(x.code_cas) == k), None)
        H.SOURCE_RESOLVER = _resolve_source
        self.case: Case = Case()
        self.dirty = False
        self._loading = False
        self.settings = QSettings("MappingEpi", "MappingEpi")
        self.exporter = Exporter(self)
        self.exporter.busy.connect(self._busy)
        self.setWindowTitle("Mapping Épi : parcours épidémiologique des cas")
        self.resize(1500, 900)

        # --- liste des cas -------------------------------------------------
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(6, 6, 6, 6)
        title = QLabel("Cas enregistrés")
        title.setObjectName("sideTitle")
        ll.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher (ZS, AS, lieu, nom…)")
        self.search.textChanged.connect(self.refresh_list)
        ll.addWidget(self.search)
        self.case_list = QListWidget()
        self.case_list.itemClicked.connect(self._open_from_list)
        ll.addWidget(self.case_list, 1)
        for label, slot in [("＋ Nouveau cas", self.new_case), ("Dupliquer", self.duplicate_case),
                            ("Historique / versions…", self.show_history), ("Supprimer", self.delete_case)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            if label.startswith("＋"):
                b.setProperty("primary", True)
            if label == "Supprimer":
                b.setProperty("danger", True)
            ll.addWidget(b)
        left.setMinimumWidth(270)

        # --- formulaire ----------------------------------------------------
        self.identity = IdentityTab()
        self.clinic = ClinicTab()
        self.timeline = TimelineTab()
        self.places = places_tab()
        self.contacts = contacts_tab()
        self.ipc = ipc_tab()
        self.labs = lab_tab()
        self.actions_tab = ActionsTab()
        self.checks = ChecksTab()
        self.form = QTabWidget()
        for w, name in [(self.identity, "1. Identité"), (self.clinic, "2. Clinique"), (self.timeline, "3. Chronologie"),
                        (self.places, "4. Lieux"), (self.contacts, "5. Contacts"), (self.ipc, "6. PCI"),
                        (self.labs, "7. Laboratoire"), (self.actions_tab, "8. Actions"), (self.checks, "✔ Contrôles")]:
            if w in (self.identity, self.clinic):
                sc = QScrollArea()
                sc.setWidgetResizable(True)
                sc.setFrameShape(QScrollArea.NoFrame)
                sc.setWidget(w)
                w = sc
            self.form.addTab(w, name)
        nav = QHBoxLayout()
        prev_b, next_b = QPushButton("◀ Précédent"), QPushButton("Suivant ▶")
        prev_b.clicked.connect(lambda: self.form.setCurrentIndex(max(0, self.form.currentIndex() - 1)))
        next_b.clicked.connect(lambda: self.form.setCurrentIndex(min(self.form.count() - 1, self.form.currentIndex() + 1)))
        next_b.setProperty("primary", True)
        nav.addWidget(prev_b)
        nav.addStretch(1)
        nav.addWidget(next_b)
        form_box = QWidget()
        fl = QVBoxLayout(form_box)
        fl.setContentsMargins(0, 0, 0, 0)
        self.missing_label = QLabel("")
        self.missing_label.setWordWrap(True)
        self.missing_label.setStyleSheet("color:#8E2F28; background:#FBEAE8; border:1px solid #B4554E; "
                                         "border-radius:6px; padding:6px 9px;")
        self.missing_label.hide()
        fl.addWidget(self.missing_label)
        fl.addWidget(self.form)
        fl.addLayout(nav)

        # --- aperçus -------------------------------------------------------
        self.previews: Dict[str, Preview] = {}
        self.preview_tabs = QTabWidget()
        for key, name in [("mapping", "Mapping"), ("network", "Réseau de contacts"), ("route", "Carte du parcours"),
                          ("gantt", "Frise temporelle"), ("dashboard", "Multi-cas"),
                          ("chains", "Chaînes de transmission"), ("common", "Lieux communs")]:
            p = Preview()
            self.previews[key] = p
            self.preview_tabs.addTab(p, name)
        self.preview_tabs.currentChanged.connect(lambda _: self.update_preview(force=True))
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.preview_tabs, 1)
        exp_row = QHBoxLayout()
        for label, fmt in [("⬇ PNG HD", "png"), ("⬇ PNG 4K", "png4k"), ("⬇ PDF", "pdf"), ("⬇ SVG", "svg"),
                           ("⬇ PowerPoint", "pptx")]:
            b = QPushButton(label)
            if fmt == "png":
                b.setProperty("primary", True)
            b.clicked.connect(lambda _=False, f=fmt: self.export_current(f))
            exp_row.addWidget(b)
        rep = QPushButton("⬇ Rapport complet…")
        rep.clicked.connect(self.export_report_menu)
        exp_row.addWidget(rep)
        exp_row.addStretch(1)
        self.overflow_label = QLabel("")
        self.overflow_label.setObjectName("warn")
        exp_row.addWidget(self.overflow_label)
        rl.addLayout(exp_row)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(form_box)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 2)
        split.setStretchFactor(2, 3)
        split.setSizes([280, 680, 760])
        self.setCentralWidget(split)

        self._build_toolbar()
        self.statusBar().showMessage("Prêt")

        # --- signaux -------------------------------------------------------
        for t in (self.identity, self.clinic, self.timeline, self.places, self.contacts, self.ipc, self.labs,
                  self.actions_tab):
            t.changed.connect(self.mark_dirty)
        self.timeline.fill_gaps.connect(self.fill_gaps)
        self.places.prefill.clicked.connect(self.prefill_places)
        self.contacts.import_btn.clicked.connect(self.import_contact_list)
        self.actions_tab.accept_btn.clicked.connect(self.accept_suggestions)
        self.actions_tab.reject_btn.clicked.connect(self.reject_suggestions)
        self.actions_tab.reset_btn.clicked.connect(self.reset_suggestions)

        self.preview_timer = QTimer(self, singleShot=True, interval=450)
        self.preview_timer.timeout.connect(self.update_preview)
        self.autosave = QTimer(self, interval=30_000)
        self.autosave.timeout.connect(self.autosave_now)
        self.autosave.start()

        self.refresh_list()
        if not self.store.list() and SAMPLE.exists():
            demo = storage.load_json(SAMPLE)
            self.store.save(demo, version=True, commentaire="Cas de démonstration")
            self.refresh_list()
        last = self.settings.value("last_case")
        first = self.store.list()
        if last and self.store.load(last):
            self.load_case(self.store.load(last))
        elif first:
            self.load_case(self.store.load(first[0][0]))
        else:
            self.load_case(Case())
        self.set_theme(self.settings.value("theme") or "systeme")
        self.statusBar().showMessage(f"Données locales : {data_dir()}", 8000)

        # synchronisation automatique (toutes les 15 min si activée), sauvegarde quotidienne, nouvelle version
        self._sync_en_cours = False
        self.sync_timer = QTimer(self, interval=15 * 60_000)
        self.sync_timer.timeout.connect(lambda: self.synchroniser(silencieux=True))
        if self.settings.value("sync_auto", "false") == "true" and self.settings.value("sync_jeton"):
            self.sync_timer.start()
            QTimer.singleShot(20_000, lambda: self.synchroniser(silencieux=True))
        from core import securite as SEC
        if SEC.sauvegarde_due(self.store):
            QTimer.singleShot(5000, lambda: self.sauvegarder_maintenant(silencieux=True))
        self._signal = _Relais()
        self._signal.texte.connect(self._nouvelle_version)
        SEC.verifier_version(lambda v: self._signal.texte.emit(v))

    # ------------------------------------------------------------------
    def _build_toolbar(self):
        tb = QToolBar("Principal")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)

        def act(label, slot, shortcut=None, tip=""):
            a = QAction(label, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            if tip:
                a.setToolTip(tip)
            tb.addAction(a)
            return a
        act("Nouveau", self.new_case, "Ctrl+N")
        act("Enregistrer", self.save_version, "Ctrl+S", "Enregistre et crée une version dans l'historique")
        tb.addSeparator()
        act("Ouvrir JSON…", self.open_json, "Ctrl+O")
        act("Exporter JSON…", self.save_json)
        imp = QToolButton()
        imp.setText("Excel ▾")
        imp.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(imp)
        _add(m, "Importer une fiche Excel…", self.import_excel)
        _add(m, "Importer un narratif Word / PowerPoint…", self.import_narratif)
        _add(m, "Exporter la fiche en Excel…", self.export_excel)
        _add(m, "Enregistrer un modèle Excel vierge…", self.excel_template)
        imp.setMenu(m)
        tb.addWidget(imp)
        tb.addSeparator()
        exp = QToolButton()
        exp.setText("Exporter le mapping ▾")
        exp.setPopupMode(QToolButton.InstantPopup)
        m2 = QMenu(exp)
        _add(m2, "PNG Full HD (1920×1080)", lambda: self.export_visual("mapping", "png"))
        _add(m2, "PNG 4K (3840×2160)", lambda: self.export_visual("mapping", "png4k"))
        _add(m2, "PDF 16:9 (vectoriel)", lambda: self.export_visual("mapping", "pdf"))
        _add(m2, "PDF A4 paysage", lambda: self.export_visual("mapping", "pdfa4"))
        _add(m2, "SVG", lambda: self.export_visual("mapping", "svg"))
        _add(m2, "PowerPoint modifiable (.pptx)", lambda: self.export_visual("mapping", "pptx"))
        m2.addSeparator()
        _add(m2, "Rapport complet PDF (4 visuels)", lambda: self.export_report("pdf"))
        _add(m2, "Rapport complet PowerPoint (4 visuels)", lambda: self.export_report("pptx"))
        exp.setMenu(m2)
        tb.addWidget(exp)
        tb.addSeparator()
        rip = QToolButton()
        rip.setText("Riposte ▾")
        rip.setPopupMode(QToolButton.InstantPopup)
        m5 = QMenu(rip)
        _add(m5, "Indicateurs clés et courbe épidémique…", self.show_indicateurs)
        _add(m5, "Suivi des actions…", self.show_actions)
        m5.addSeparator()
        _add(m5, "Liste des cas (Excel)…", self.export_liste_cas)
        _add(m5, "Rapport de situation (Word)…", self.export_rapport_situation)
        m5.addSeparator()
        _add(m5, "Exporter un paquet de fiches (.zip)…", self.export_paquet)
        _add(m5, "Importer un paquet de fiches (.zip)…", self.import_paquet)
        m5.addSeparator()
        _add(m5, "Synchronisation avec le serveur…", self.reglage_sync)
        _add(m5, "Synchroniser maintenant", lambda: self.synchroniser(silencieux=False))
        _add(m5, "Doublons possibles…", self.show_doublons)
        _add(m5, "Carte des cas…", self.show_carte)
        rip.setMenu(m5)
        tb.addWidget(rip)
        sec = QToolButton()
        sec.setText("Sécurité ▾")
        sec.setPopupMode(QToolButton.InstantPopup)
        m6 = QMenu(sec)
        _add(m6, "Mot de passe au démarrage…", self.reglage_mot_de_passe)
        m6.addSeparator()
        _add(m6, "Sauvegarde automatique (dossier, clé USB)…", self.reglage_sauvegarde)
        _add(m6, "Sauvegarder maintenant", lambda: self.sauvegarder_maintenant(silencieux=False))
        _add(m6, "Reprendre les fiches d'une sauvegarde…", self.restaurer_sauvegarde)
        sec.setMenu(m6)
        tb.addWidget(sec)
        tb.addSeparator()
        th = QToolButton()
        th.setText("Thème ▾")
        th.setPopupMode(QToolButton.InstantPopup)
        m3 = QMenu(th)
        _add(m3, "Clair", lambda: self.set_theme("clair"))
        _add(m3, "Sombre", lambda: self.set_theme("sombre"))
        _add(m3, "Comme le système", lambda: self.set_theme("systeme"))
        th.setMenu(m3)
        tb.addWidget(th)
        tb.addSeparator()
        act("Utilisateurs…", self.manage_users, tip="Comptes de la version web (identifiant + mot de passe)")
        web = QToolButton()
        web.setText("Version web ▾")
        web.setPopupMode(QToolButton.InstantPopup)
        m4 = QMenu(web)
        _add(m4, "Démarrer le serveur web (réseau local)", self.start_web)
        _add(m4, "Ouvrir la version web dans le navigateur", self.open_web)
        _add(m4, "Arrêter le serveur web", self.stop_web)
        web.setMenu(m4)
        tb.addWidget(web)
        act("Dossier de données", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir()))),
            tip="Ouvre le dossier local où toutes les données sont gardées")
        act("Aide", self.show_help, "F1")

    # ------------------------------------------------------------------ cas
    def refresh_list(self):
        self.case_list.clear()
        for cid, titre, updated in self.store.list(self.search.text().strip()):
            it = QListWidgetItem(titre)
            it.setData(Qt.UserRole, cid)
            it.setToolTip(f"Modifié le {updated[:16].replace('T', ' ')}")
            self.case_list.addItem(it)
            if cid == self.case.id:
                it.setSelected(True)

    def _open_from_list(self, item):
        cid = item.data(Qt.UserRole)
        if cid == self.case.id:
            return
        self.collect()
        if self.dirty:
            self.store.save(self.case)
        c = self.store.load(cid)
        if c:
            self.load_case(c)

    def load_case(self, c: Case):
        self._loading = True
        self.case = c
        for t in (self.identity, self.clinic, self.timeline, self.places, self.contacts, self.ipc, self.labs,
                  self.actions_tab):
            t.load(c)
        self._loading = False
        self.dirty = False
        self.settings.setValue("last_case", c.id)
        self._update_place_names()
        self.update_preview(force=True)
        self.statusBar().showMessage(f"Cas ouvert : {c.titre_court()}", 4000)

    def collect(self) -> Case:
        c = self.case
        for t in (self.identity, self.clinic, self.timeline, self.places, self.contacts, self.ipc, self.labs,
                  self.actions_tab):
            t.save(c)
        return c

    def table_errors(self) -> List[str]:
        out = []
        for name, t in [("Chronologie", self.timeline), ("Lieux", self.places), ("Contacts", self.contacts),
                        ("PCI", self.ipc), ("Laboratoire", self.labs), ("Actions", self.actions_tab)]:
            out += [f"{name} : {e}" for e in t.editor.errors]
        return out

    def mark_dirty(self):
        if self._loading:
            return
        self.dirty = True
        self.preview_timer.start()

    def new_case(self):
        self.collect()
        if self.dirty:
            self.store.save(self.case)
        c = Case(investigateur=self.case.investigateur, zs=self.case.zs, province=self.case.province,
                 maladie=self.case.maladie)
        self.store.save(c)
        self.load_case(c)
        self.refresh_list()
        self.form.setCurrentIndex(0)

    def duplicate_case(self):
        c = self.collect().model_copy(deep=True)
        import uuid
        c.id = uuid.uuid4().hex
        c.rang = None
        self.store.save(c, version=True, commentaire="Copie")
        self.load_case(c)
        self.refresh_list()

    def delete_case(self):
        if QMessageBox.question(self, "Supprimer", f"Supprimer la fiche « {self.case.titre_court()} » ?\n"
                                "Les versions enregistrées restent dans l'historique.") != QMessageBox.Yes:
            return
        self.store.delete(self.case.id)
        rows = self.store.list()
        self.load_case(self.store.load(rows[0][0]) if rows else Case())
        self.refresh_list()

    def save_version(self):
        self.collect()
        errs = self.table_errors()
        comment, ok = QInputDialog.getText(self, "Enregistrer une version", "Commentaire (facultatif) :")
        if not ok:
            return
        self.identity.remember_new()
        self.store.save(self.case, version=True, commentaire=comment)
        self.dirty = False
        self.refresh_list()
        msg = "Version enregistrée."
        if errs:
            msg += f" Attention : {len(errs)} saisie(s) invalide(s), voir l'onglet Contrôles."
        self.statusBar().showMessage(msg, 6000)

    def autosave_now(self):
        if self.dirty:
            try:
                self.collect()
                self.store.save(self.case)
                self.dirty = False
                self.refresh_list()
                self.statusBar().showMessage(f"Sauvegarde automatique {datetime.now():%H:%M:%S}", 3000)
            except Exception:
                log.exception("Échec de la sauvegarde automatique")

    def show_history(self):
        self.collect()
        dlg = QDialog(self)
        dlg.setWindowTitle("Historique des versions")
        dlg.resize(620, 420)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        for vid, ts, auteur, com in self.store.versions(self.case.id):
            it = QListWidgetItem(f"{ts.replace('T', ' ')} · {auteur}" + (f" · {com}" if com else ""))
            it.setData(Qt.UserRole, vid)
            lst.addItem(it)
        lay.addWidget(lst)
        info = QTextBrowser()
        lay.addWidget(info)
        row = QHBoxLayout()
        cmp_b, rest_b = QPushButton("Comparer avec la fiche actuelle"), QPushButton("Restaurer cette version")
        row.addWidget(cmp_b)
        row.addWidget(rest_b)
        row.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(dlg.reject)
        row.addWidget(close)
        lay.addLayout(row)

        def selected():
            it = lst.currentItem()
            return self.store.load_version(it.data(Qt.UserRole)) if it else None

        def compare():
            v = selected()
            if v:
                info.setHtml("<ul>" + "".join(f"<li>{d}</li>" for d in storage.diff_cases(v, self.case)) + "</ul>")

        def restore():
            v = selected()
            if v and QMessageBox.question(dlg, "Restaurer", "Remplacer la fiche actuelle par cette version ?") == QMessageBox.Yes:
                self.store.save(self.case, version=True, commentaire="Avant restauration")
                self.load_case(v)
                self.store.save(v, version=True, commentaire="Restauration")
                self.refresh_list()
                dlg.accept()
        cmp_b.clicked.connect(compare)
        rest_b.clicked.connect(restore)
        lst.itemDoubleClicked.connect(lambda _: compare())
        if not lst.count():
            info.setPlainText("Aucune version enregistrée : utilisez « Enregistrer » (Ctrl+S).")
        dlg.exec()

    # ------------------------------------------------------------- assistants
    def _update_place_names(self):
        c = self.case
        names = [p.nom for p in c.places] + [e.lieu for e in c.events] + [e.lieu_arrivee for e in c.events]
        names = [n for n in names if n and "→" not in n]
        for t in (self.timeline, self.places, self.contacts, self.ipc):
            t.editor.set_place_names(names)

    def fill_gaps(self):
        self.collect()
        gaps = rules.coverage_gaps(self.case)
        if not gaps:
            QMessageBox.information(self, "Chronologie", "Aucune période non couverte détectée.")
            return
        for a, b in gaps:
            self.case.events.append(Event(date_debut=a, date_fin=b, type="Période à documenter",
                                          titre="Période à documenter", description="Activités et contacts à reconstituer",
                                          risque="Inconnu", lieu="?"))
        self.timeline.load(self.case)
        self.timeline.sort_dates()
        self.mark_dirty()
        self.statusBar().showMessage(f"{len(gaps)} période(s) à documenter ajoutée(s).", 5000)

    def prefill_places(self):
        self.collect()
        new = rules.places_from_events(self.case)
        if not new:
            QMessageBox.information(self, "Lieux", "Tous les lieux de la chronologie sont déjà listés.")
            return
        self.case.places.extend(new)
        self.places.load(self.case)
        self.mark_dirty()
        self.statusBar().showMessage(f"{len(new)} lieu(x) ajouté(s) depuis la chronologie.", 5000)

    def import_contact_list(self):
        path, _ = QFileDialog.getOpenFileName(self, "Liste nominative des contacts", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            groups = storage.import_contact_list(path)
        except Exception as exc:
            QMessageBox.warning(self, "Import", f"Lecture impossible : {exc}\n\nColonnes attendues : Nom, Catégorie, "
                                               "Lieu, Dernier contact, Suivi (oui/non), Risque.")
            return
        self.collect()
        by_cat = {g.categorie.lower(): g for g in self.case.contacts}
        for g in groups:
            if g.categorie.lower() in by_cat:
                old = by_cat[g.categorie.lower()]
                old.nombre, old.suivis = g.nombre, g.suivis
                old.dernier_contact = g.dernier_contact or old.dernier_contact
                old.lieu = old.lieu or g.lieu
            else:
                self.case.contacts.append(g)
        self.contacts.load(self.case)
        self.mark_dirty()
        self.statusBar().showMessage(f"{sum(g.nombre or 0 for g in groups)} contacts importés en {len(groups)} catégorie(s).", 6000)

    def accept_suggestions(self):
        self.collect()
        for texte, prio in self.actions_tab.checked():
            self.case.actions.append(Action(texte=texte, priorite=prio, auto=True))
        self.actions_tab.load(self.case)
        self.mark_dirty()

    def reject_suggestions(self):
        self.collect()
        for texte, _ in self.actions_tab.checked():
            if texte not in self.case.suggestions_rejetees:
                self.case.suggestions_rejetees.append(texte)
        self.mark_dirty()
        self.update_preview(force=True)

    def reset_suggestions(self):
        self.collect()
        self.case.suggestions_rejetees = []
        self.mark_dirty()
        self.update_preview(force=True)

    # --------------------------------------------------------------- aperçu
    def current_key(self) -> str:
        return list(self.previews)[self.preview_tabs.currentIndex()]

    def visual_html(self, key: str) -> str:
        c = self.case
        if key == "mapping":
            return H.render_mapping_html(c)
        if key == "network":
            return network.render_html(c)
        if key == "route":
            return map_view.render_html(c)
        if key == "gantt":
            return gantt.render_html(c)
        if key == "chains":
            return chains.render_html(self._all_cases(), c)
        if key == "common":
            return common_places.render_html(self._all_cases(), c)
        return dashboard.render_html(self._all_cases(), c.zs)

    def visual_svg(self, key: str) -> str:
        c = self.case
        return {"mapping": lambda: H.html_to_svg_wrapper(H.render_mapping_html(c)),
                "network": lambda: network.render_svg(c), "route": lambda: map_view.render_svg(c),
                "gantt": lambda: gantt.render_svg(c),
                "dashboard": lambda: dashboard.render_svg(self._all_cases(), c.zs),
                "chains": lambda: chains.render_svg(self._all_cases(), c),
                "common": lambda: common_places.render_svg(self._all_cases(), c)}[key]()

    def _all_cases(self) -> List[Case]:
        others = [x for x in self.store.all_cases() if x.id != self.case.id]
        return others + [self.case]

    def update_preview(self, force: bool = False):
        if self._loading:
            return
        try:
            self.collect()
        except Exception as exc:
            log.exception("Lecture du formulaire")
            self.statusBar().showMessage(f"Saisie invalide : {exc}", 6000)
            return
        c = self.case
        self._update_place_names()
        w = rules.windows(c)
        self.timeline.editor.set_computed("_suggere", [
            (f"{lvl}" + (" ✓" if not e.risque else ""), why, theme.risk_color(lvl))
            for e in c.events for lvl, why in [rules.suggest_event_risk(e, c, w)]])
        self.places.editor.set_computed("_suggere", [
            (rules.suggest_place_risk(p.model_copy(update={"risque": ""}), c), "", None) for p in c.places])
        self.contacts.editor.set_computed("_fin", [
            ((rules.contact_followup_end(g, c).strftime("%d/%m/%Y") if rules.contact_followup_end(g, c) else "?"),
             "Dernier contact + durée de suivi", None) for g in c.contacts])
        self.labs.editor.set_computed("_delai", [
            (f"{(l.resultat_le - l.prelevement).total_seconds() / 3600:.0f} h" if l.prelevement and l.resultat_le else "?",
             "", None) for l in c.labs])
        self.actions_tab.show_suggestions(rules.suggest_actions(c))
        self.checks.update_from(c, self.table_errors())
        manquants = rules.completeness(c)[1]
        self.missing_label.setText(f"À compléter ({len(manquants)}) : " + " • ".join(manquants))
        self.missing_label.setVisible(bool(manquants))
        key = self.current_key()
        view = self.previews[key]
        try:
            view.set_page(self.visual_html(key))
        except Exception as exc:
            log.exception("Rendu de l'aperçu")
            self.statusBar().showMessage(f"Erreur de rendu : {exc}", 8000)
            return
        if key == "mapping":
            QTimer.singleShot(1200, self._check_overflow)
        else:
            self.overflow_label.setText("")

    def _check_overflow(self):
        def got(items):
            if items:
                self.overflow_label.setText(f"⚠ {len(items)} zone(s) de texte trop longue(s) : raccourcir le texte")
                self.overflow_label.setToolTip("\n".join(items))
            else:
                self.overflow_label.setText("")
        self.previews["mapping"].page().runJavaScript("window.__overflow ? window.__overflow() : []", 0, got)

    # --------------------------------------------------------------- exports
    def _default_name(self, key: str, ext: str) -> str:
        c = self.case
        base = {"mapping": "Mapping", "network": "Reseau", "route": "Parcours", "gantt": "Frise", "dashboard": "MultiCas",
                "chains": "Chaines_transmission", "common": "Lieux_communs",
                "report": "Rapport"}[key]
        rang = f"Cas{c.rang}" if c.rang else "Cas"
        last_dir = self.settings.value("export_dir") or str(Path.home())
        return str(Path(last_dir) / f"{base}_{slug(c.maladie)}_{slug(c.zs or 'ZS')}_{rang}_{date.today():%Y%m%d}.{ext}")

    def _ask_path(self, key: str, ext: str, filt: str) -> Optional[Path]:
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", self._default_name(key, ext), filt)
        if not path:
            return None
        p = Path(path)
        if p.suffix.lower() != "." + ext:
            p = p.with_suffix("." + ext)
        self.settings.setValue("export_dir", str(p.parent))
        return p

    def export_current(self, fmt: str):
        self.export_visual(self.current_key(), fmt)

    def export_visual(self, key: str, fmt: str):
        self.collect()
        if fmt == "pptx" and key != "mapping":
            QMessageBox.information(self, "PowerPoint", "Le PowerPoint modifiable concerne le mapping. Pour les autres "
                                                        "visuels, utilisez « Rapport complet PowerPoint » (images HD) ou PNG.")
            return
        ext = {"png": "png", "png4k": "png", "pdf": "pdf", "pdfa4": "pdf", "svg": "svg", "pptx": "pptx"}[fmt]
        filt = {"png": "Image PNG (*.png)", "pdf": "PDF (*.pdf)", "svg": "SVG (*.svg)", "pptx": "PowerPoint (*.pptx)"}[ext]
        path = self._ask_path(key, ext, filt)
        if not path:
            return
        try:
            if fmt == "svg":
                path.write_text(self.visual_svg(key), encoding="utf-8")
                self._done(True, path)
            elif fmt == "pptx":
                export_mapping_pptx(self.case, path)
                self._done(True, path)
            elif fmt in ("pdf", "pdfa4"):
                html = self.visual_html(key)
                if fmt == "pdfa4":
                    html = H.with_css(html, H.A4_CSS)
                self.exporter.to_pdf(html, path, self._done, a4=(fmt == "pdfa4"))
            else:
                self.exporter.to_png(self.visual_html(key), path, 3840 if fmt == "png4k" else 1920, self._done)
        except Exception as exc:
            log.exception("Export")
            QMessageBox.critical(self, "Export", f"Échec de l'export : {exc}")

    def export_report_menu(self):
        m = QMenu(self)
        _add(m, "PDF 16:9 (4 visuels)", lambda: self.export_report("pdf"))
        _add(m, "PDF A4 paysage (4 visuels)", lambda: self.export_report("pdfa4"))
        _add(m, "PowerPoint (mapping modifiable + 3 visuels HD)", lambda: self.export_report("pptx"))
        m.exec(QCursor.pos())

    def export_report(self, fmt: str):
        self.collect()
        c = self.case
        svgs = [network.render_svg(c), map_view.render_svg(c), gantt.render_svg(c)]
        ext = "pptx" if fmt == "pptx" else "pdf"
        path = self._ask_path("report", ext, "PowerPoint (*.pptx)" if ext == "pptx" else "PDF (*.pdf)")
        if not path:
            return
        if fmt in ("pdf", "pdfa4"):
            html = H.render_report_html(c, svgs)
            if fmt == "pdfa4":
                html = H.with_css(html, H.A4_CSS)
            self.exporter.to_pdf(html, path, self._done, a4=(fmt == "pdfa4"))
            return
        tmp = Path(tempfile.mkdtemp(prefix="rapport_"))
        pdf = tmp / "visuels.pdf"
        html = H.page("".join(f'<div class="page"><div class="svgpage">{s}</div></div>' for s in svgs), "Visuels") \
            .replace("html, body { width: 1280px; height: 720px; overflow: hidden; }", "html, body { width: 1280px; }")

        def after(ok: bool, _p: Path):
            if not ok:
                self._done(False, path)
                return
            try:
                imgs = pdf_pages_to_png(pdf, tmp, 2560)
                export_report_pptx(c, imgs, path)
                self._done(True, path)
            except Exception as exc:
                log.exception("Rapport PPTX")
                QMessageBox.critical(self, "Export", f"Échec : {exc}")
        self.exporter.to_pdf(html, pdf, after)

    def _done(self, ok: bool, path: Path):
        if ok:
            box = QMessageBox(self)
            box.setWindowTitle("Export terminé")
            box.setText(f"Fichier enregistré :\n{path}")
            open_b = box.addButton("Ouvrir", QMessageBox.AcceptRole)
            folder_b = box.addButton("Ouvrir le dossier", QMessageBox.ActionRole)
            box.addButton("Fermer", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is open_b:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            elif box.clickedButton() is folder_b:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
        else:
            QMessageBox.critical(self, "Export", f"L'export a échoué : {path}")

    def _busy(self, on: bool):
        if on:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.statusBar().showMessage("Export en cours…")
        else:
            QApplication.restoreOverrideCursor()
            self.statusBar().showMessage("Export terminé", 3000)

    # ------------------------------------------------------------- fichiers
    def open_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une fiche", "", "Fiche JSON (*.json)")
        if not path:
            return
        try:
            c = storage.load_json(path)
        except Exception as exc:
            QMessageBox.critical(self, "Ouvrir", f"Fichier illisible : {exc}")
            return
        if self.store.load(c.id) and QMessageBox.question(
                self, "Ouvrir", "Cette fiche existe déjà. L'importer comme une copie ?") == QMessageBox.Yes:
            import uuid
            c.id = uuid.uuid4().hex
        self.store.save(c, version=True, commentaire=f"Import {Path(path).name}")
        self.load_case(c)
        self.refresh_list()

    def save_json(self):
        self.collect()
        path = self._ask_path("mapping", "json", "Fiche JSON (*.json)")
        if path:
            storage.save_json(self.case, path)
            self.statusBar().showMessage(f"Fiche exportée : {path}", 5000)

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importer une fiche Excel", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            c = storage.import_excel(path)
        except storage.ExcelImportError as exc:
            QMessageBox.warning(self, "Import Excel", "Fiche importée avec des valeurs ignorées :\n\n" + "\n".join(exc.errors[:20]))
            c = exc.case
        except Exception as exc:
            QMessageBox.critical(self, "Import Excel", f"Lecture impossible : {exc}")
            return
        self.store.save(c, version=True, commentaire=f"Import {Path(path).name}")
        self.load_case(c)
        self.refresh_list()

    def import_narratif(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importer un narratif", "",
                                              "Narratif (*.docx *.pptx *.ppt)")
        if not path:
            return
        from core import narratif
        try:
            res = narratif.importer(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import du narratif", f"Lecture impossible : {exc}")
            return
        c = res.case
        self.store.save(c, version=True, commentaire=f"Import narratif {Path(path).name}")
        self.load_case(c)
        self.refresh_list()
        msg = "Trouvé : " + ", ".join(res.trouves) + "."
        if res.manquants:
            msg += "\n\nÀ compléter : " + ", ".join(res.manquants) + "."
        QMessageBox.information(self, "Narratif importé", msg + "\n\nVérifiez chaque onglet.")

    def export_excel(self):
        self.collect()
        path = self._ask_path("mapping", "xlsx", "Excel (*.xlsx)")
        if path:
            storage.export_excel(self.case, path)
            self._done(True, path)

    def excel_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "Modèle Excel", str(Path.home() / "Modele_fiche_cas.xlsx"), "Excel (*.xlsx)")
        if path:
            storage.export_excel_template(path)
            self._done(True, Path(path))

    # ------------------------------------------------------------- divers
    def set_theme(self, name: str):
        self.settings.setValue("theme", name)
        applied = apply_theme(name)
        self.statusBar().showMessage(f"Thème : {applied}", 2500)

    # ------------------------------------------------------------ riposte
    def _cas_enregistres(self) -> List[Case]:
        self.autosave_now()
        return self.store.all_cases()

    def _fenetre_html(self, titre: str, rendu, choix=None):
        """Fenêtre affichant une page HTML ; `rendu(valeur du choix)` renvoie la page."""
        dlg = QDialog(self)
        dlg.setWindowTitle(titre)
        dlg.resize(1180, 820)
        lay = QVBoxLayout(dlg)
        view = QWebEngineView()
        combo = None
        if choix:
            combo = QComboBox()
            for lib, val in choix:
                combo.addItem(lib, val)
            combo.setCurrentIndex(1 if len(choix) > 1 else 0)
            combo.currentIndexChanged.connect(lambda _i: view.setHtml(rendu(combo.currentData())))
            row = QHBoxLayout()
            row.addWidget(QLabel("Indicateurs calculés sur :"))
            row.addWidget(combo)
            row.addStretch(1)
            lay.addLayout(row)
        lay.addWidget(view, 1)
        view.setHtml(rendu(combo.currentData() if combo else None))
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def show_indicateurs(self):
        from core import riposte as RIP
        cases = self._cas_enregistres()
        cb = RIP.courbe(cases)

        def rendu(periode):
            recents = RIP.filtrer(cases, periode, date.today())
            corps = (f'<p class="hint">{len(cases)} cas au total ; indicateurs sur {len(recents)} cas '
                     f'{"notifiés dans les " + str(periode) + " derniers jours" if periode else "(toute la période)"}. '
                     "Cibles indicatives, à valider par la coordination.</p>"
                     f'<div class="card">{RIP.html_indicateurs(RIP.indicateurs(recents))}</div>'
                     '<div class="card"><h2 style="margin-top:0">Courbe épidémique : cas par semaine de début de la '
                     f'maladie</h2>{RIP.courbe_svg(cb)}</div>')
            return RIP.page_bureau("Indicateurs clés de la riposte", corps)
        self._fenetre_html("Indicateurs clés et courbe épidémique", rendu,
                           [("7 derniers jours", 7), ("21 derniers jours", 21), ("42 derniers jours", 42),
                            ("toute la période", None)])

    def show_actions(self):
        from core import riposte as RIP
        items = RIP.actions_ouvertes(self._cas_enregistres())
        b = RIP.bilan_actions(items)
        corps = (f'<p class="hint">{b["ouvertes"]} action(s) ouverte(s) · {b["retard"]} en retard · {b["urgentes"]} '
                 f'urgente(s) · {b["sans_responsable"]} sans responsable · {b["sans_echeance"]} sans échéance. '
                 "Pour modifier une action, ouvrez la fiche du cas (onglet Actions).</p>"
                 f'<div class="card">{RIP.html_actions(items)}</div>')
        self._fenetre_html("Suivi des actions", lambda _v: RIP.page_bureau("Suivi des actions", corps))

    def export_liste_cas(self):
        from core import echanges as ECH
        path, _ = QFileDialog.getSaveFileName(self, "Liste des cas", str(Path.home() / f"Liste_des_cas_{date.today()}.xlsx"),
                                              "Excel (*.xlsx)")
        if path:
            ECH.liste_cas_xlsx(self._cas_enregistres(), path, "application de bureau")
            self._done(True, Path(path))

    def export_rapport_situation(self):
        from core import echanges as ECH
        path, _ = QFileDialog.getSaveFileName(self, "Rapport de situation",
                                              str(Path.home() / f"Rapport_situation_MVE_{date.today()}.docx"),
                                              "Word (*.docx)")
        if path:
            ECH.rapport_docx(self._cas_enregistres(), path, "application de bureau", 21)
            self._done(True, Path(path))

    def export_paquet(self):
        from core import echanges as ECH
        path, _ = QFileDialog.getSaveFileName(self, "Paquet de fiches",
                                              str(Path.home() / f"Paquet_fiches_MappingEpi_{date.today()}.zip"),
                                              "Paquet de fiches (*.zip)")
        if path:
            cases = self._cas_enregistres()
            Path(path).write_bytes(ECH.paquet_bytes(cases, storage.current_user(), "application de bureau"))
            QMessageBox.information(self, "Paquet de fiches", (
                f"{len(cases)} fiche(s) dans le paquet :\n{path}\n\nTransmettez ce fichier (clé USB, e-mail, WhatsApp) : "
                "il s'importe dans un autre ordinateur ou sur le serveur (menu Données). Il contient des données de "
                "santé : ne le partagez qu'avec l'équipe de la riposte."))

    def import_paquet(self):
        from core import echanges as ECH
        path, _ = QFileDialog.getOpenFileName(self, "Importer un paquet de fiches", str(Path.home()),
                                              "Paquet de fiches (*.zip)")
        if not path:
            return
        self.autosave_now()
        try:
            b = ECH.importer_paquet(self.store, Path(path).read_bytes(), storage.current_user())
        except ValueError as exc:
            QMessageBox.warning(self, "Paquet de fiches", str(exc))
            return
        self.refresh_list()
        cur = self.store.load(self.case.id)
        if cur and cur.model_dump_json() != self.case.model_dump_json():
            self.load_case(cur)
        QMessageBox.information(self, "Paquet importé", b.texte())

    # ---------------------------------------------------- doublons, carte
    def show_doublons(self):
        from core import doublons as DB
        from core import riposte as RIP
        import html as _h
        ds = DB.doublons(self._cas_enregistres())
        rows = "".join(f"<tr><td>{_h.escape(d.certitude)}</td><td>{_h.escape(d.a.code_cas or d.a.titre_court())}</td>"
                       f"<td>{_h.escape(d.b.code_cas or d.b.titre_court())}</td><td>{_h.escape(d.a.zs)}</td>"
                       f"<td>{_h.escape(d.raison)}</td></tr>" for d in ds)
        corps = ('<p class="hint">Rien n\'est supprimé automatiquement : ouvrez les deux fiches dans la liste, gardez la '
                 "plus complète et supprimez l'autre (récupérable dans l'historique).</p><div class='card'>"
                 + ("<table class='list'><tr><th>Certitude</th><th>Fiche 1</th><th>Fiche 2</th><th>ZS</th><th>Raison</th></tr>"
                    + rows + "</table>" if ds else "<p class='muted'>Aucun doublon possible.</p>") + "</div>")
        self._fenetre_html("Doublons possibles", lambda _v: RIP.page_bureau("Doublons possibles", corps))

    def show_carte(self):
        from core import carte as CARTE
        from core import riposte as RIP
        cases = self._cas_enregistres()

        def rendu(periode):
            sel = RIP.filtrer(cases, periode, date.today())
            ct = CARTE.construire(sel)
            sans = (f"<p class='hint'>{len(ct.sans_position)} cas sans position (ni GPS, ni coordonnées de leur aire "
                    "ou zone de santé).</p>" if ct.sans_position else "")
            corps = (f"<p class='hint'>{len(sel)} cas · {ct.n_coord} aire(s) de santé avec coordonnées "
                     f"(fichier {CARTE.fichier()}).</p><div class='card'>{CARTE.svg(ct)}</div>{sans}")
            return RIP.page_bureau("Carte des cas", corps)
        self._fenetre_html("Carte des cas", rendu, [("21 derniers jours", 21), ("42 derniers jours", 42),
                                                    ("toute la période", None)])

    # ---------------------------------------------------- synchronisation
    def reglage_sync(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Synchronisation avec le serveur")
        lay = QVBoxLayout(dlg)
        lab = QLabel("Sur le site, ouvrez « Mon compte » puis « Créer un jeton ». Collez ici l'adresse du site et le "
                     "jeton. Les fiches de cet ordinateur sont envoyées au serveur, puis celles de votre périmètre "
                     "sont reçues. Rien n'est effacé : la version la plus récente de chaque fiche l'emporte.")
        lab.setWordWrap(True)
        lay.addWidget(lab)
        url = QLineEdit(self.settings.value("sync_url", "") or "")
        url.setPlaceholderText("https://adresse-du-site")
        jet = QLineEdit(self.settings.value("sync_jeton", "") or "")
        jet.setEchoMode(QLineEdit.Password)
        jet.setPlaceholderText("mepi_…")
        auto = QCheckBox("Synchroniser automatiquement toutes les 15 minutes quand internet est disponible")
        auto.setChecked(self.settings.value("sync_auto", "false") == "true")
        for t, w in (("Adresse du site", url), ("Jeton", jet)):
            lay.addWidget(QLabel(t))
            lay.addWidget(w)
        lay.addWidget(auto)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        self.settings.setValue("sync_url", url.text().strip())
        self.settings.setValue("sync_jeton", jet.text().strip())
        self.settings.setValue("sync_auto", "true" if auto.isChecked() else "false")
        if auto.isChecked() and jet.text().strip():
            self.sync_timer.start()
        else:
            self.sync_timer.stop()
        if url.text().strip() and jet.text().strip():
            self.synchroniser(silencieux=False)

    def synchroniser(self, silencieux: bool = True):
        url, jeton = self.settings.value("sync_url", ""), self.settings.value("sync_jeton", "")
        if not url or not jeton:
            if not silencieux:
                self.reglage_sync()
            return
        if self._sync_en_cours:
            return
        self._sync_en_cours = True
        self.autosave_now()
        self.statusBar().showMessage("Synchronisation en cours…")
        relais = _Relais(self)
        relais.fini.connect(lambda ok, msg: self._sync_fini(ok, msg, silencieux))

        def run():
            from core import sync as SYNC
            try:
                envoi, recu = SYNC.synchroniser(self.store, url, jeton)
                relais.fini.emit(True, f"Envoi : {envoi}\nRéception : {recu}")
            except Exception as exc:
                relais.fini.emit(False, str(exc))
        import threading
        threading.Thread(target=run, daemon=True).start()

    def _sync_fini(self, ok: bool, msg: str, silencieux: bool):
        self._sync_en_cours = False
        self.settings.setValue("sync_dernier", datetime.now().isoformat(timespec="seconds") if ok else
                               self.settings.value("sync_dernier", ""))
        self.refresh_list()
        cur = self.store.load(self.case.id)
        if ok and cur and not self.dirty and cur.model_dump_json() != self.case.model_dump_json():
            self.load_case(cur)
        self.statusBar().showMessage(("Synchronisé " + datetime.now().strftime("%H:%M")) if ok else
                                     f"Synchronisation impossible : {msg}", 10000)
        if not silencieux:
            (QMessageBox.information if ok else QMessageBox.warning)(
                self, "Synchronisation", msg if ok else f"Synchronisation impossible : {msg}")

    # ---------------------------------------------------- sécurité
    def reglage_mot_de_passe(self):
        from core import securite as SEC
        if SEC.a_mot_de_passe(self.store):
            mdp, ok = QInputDialog.getText(self, "Mot de passe", "Mot de passe actuel (pour le changer ou le retirer) :",
                                           QLineEdit.Password)
            if not ok:
                return
            if not SEC.verifier_mot_de_passe(self.store, mdp):
                QMessageBox.warning(self, "Mot de passe", "Mot de passe incorrect.")
                return
            if QMessageBox.question(self, "Mot de passe", "Retirer le mot de passe au démarrage ?\n(Non : le changer)") \
                    == QMessageBox.Yes:
                SEC.retirer_mot_de_passe(self.store)
                QMessageBox.information(self, "Mot de passe", "Mot de passe retiré.")
                return
        n1, ok = QInputDialog.getText(self, "Mot de passe au démarrage",
                                      "Nouveau mot de passe (8 caractères, lettres et chiffres) :", QLineEdit.Password)
        if not ok or not n1:
            return
        n2, ok = QInputDialog.getText(self, "Mot de passe au démarrage", "Confirmez le mot de passe :", QLineEdit.Password)
        if not ok:
            return
        if n1 != n2:
            QMessageBox.warning(self, "Mot de passe", "Les deux mots de passe ne correspondent pas.")
            return
        try:
            SEC.definir_mot_de_passe(self.store, n1)
        except ValueError as exc:
            QMessageBox.warning(self, "Mot de passe", str(exc))
            return
        QMessageBox.information(self, "Mot de passe", (
            "Le mot de passe sera demandé à chaque ouverture de l'application. Notez-le : sans lui, seule une "
            "personne ayant accès au dossier de données peut récupérer les fiches.\n\nPour protéger les données en "
            "cas de vol de l'ordinateur, activez aussi le chiffrement du disque (BitLocker sous Windows, FileVault "
            "sur Mac)."))

    def reglage_sauvegarde(self):
        from core import securite as SEC
        d = QFileDialog.getExistingDirectory(self, "Dossier des sauvegardes automatiques (clé USB, disque externe…)",
                                             SEC.lire(self.store, "dossier_sauvegarde") or str(Path.home()))
        if not d:
            return
        SEC.ecrire(self.store, "dossier_sauvegarde", d)
        self.sauvegarder_maintenant(silencieux=False)

    def sauvegarder_maintenant(self, silencieux: bool = True):
        from core import securite as SEC
        d = SEC.lire(self.store, "dossier_sauvegarde")
        if not d:
            if not silencieux:
                self.reglage_sauvegarde()
            return
        self.autosave_now()
        try:
            out = SEC.sauvegarder(self.store, d)
        except Exception as exc:
            log.exception("Sauvegarde")
            self.statusBar().showMessage(f"Sauvegarde impossible ({exc}) : la clé USB est-elle branchée ?", 12000)
            if not silencieux:
                QMessageBox.warning(self, "Sauvegarde", f"Sauvegarde impossible dans {d} :\n{exc}")
            return
        self.statusBar().showMessage(f"Sauvegarde : {out}", 8000)
        if not silencieux:
            QMessageBox.information(self, "Sauvegarde", (
                f"Sauvegarde enregistrée :\n{out}\n\nUne sauvegarde est faite chaque jour et à la fermeture ; les 20 "
                "dernières sont gardées. Ce fichier contient des données de santé : gardez la clé USB en lieu sûr."))

    def restaurer_sauvegarde(self):
        from core import securite as SEC
        path, _ = QFileDialog.getOpenFileName(self, "Reprendre les fiches d'une sauvegarde",
                                              SEC.lire(self.store, "dossier_sauvegarde") or str(Path.home()),
                                              "Sauvegarde Mapping Épi (*.sqlite)")
        if not path:
            return
        self.autosave_now()
        try:
            b = SEC.restaurer(self.store, path, storage.current_user())
        except Exception as exc:
            QMessageBox.warning(self, "Sauvegarde", f"Fichier illisible : {exc}")
            return
        self.refresh_list()
        QMessageBox.information(self, "Sauvegarde", "Fiches reprises (rien de plus récent n'est écrasé) : " + b.texte())

    def _nouvelle_version(self, v: str):
        if self.settings.value("version_signalee") == v:
            self.statusBar().showMessage(f"Nouvelle version {v} disponible.", 10000)
            return
        self.settings.setValue("version_signalee", v)
        QMessageBox.information(self, "Nouvelle version", (
            f"Une nouvelle version de Mapping Épi ({v}) est disponible.\n\nDemandez l'installateur à votre "
            "coordination, puis installez-le par-dessus l'ancien : les fiches sont conservées."))

    # ------------------------------------------------------- utilisateurs
    def manage_users(self):
        UsersDialog(self.store, self).exec()

    # --------------------------------------------------------- serveur web
    def start_web(self):
        if self.web_proc and self.web_proc.state() != QProcess.NotRunning:
            self._show_web_urls()
            return
        if Users(self.store).count() == 0:
            QMessageBox.information(self, "Version web", "Créez d'abord au moins un compte administrateur "
                                                          "(bouton « Utilisateurs… »).")
            self.manage_users()
            if Users(self.store).count() == 0:
                return
        self.web_proc = QProcess(self)
        self.web_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.web_proc.setWorkingDirectory(str(ROOT))
        self.web_proc.readyReadStandardOutput.connect(
            lambda: log.info("web: %s", bytes(self.web_proc.readAllStandardOutput()).decode("utf-8", "replace").strip()))
        from core.paths import commande
        cmd = commande("serveur-web", "--port", str(WEB_PORT))
        self.web_proc.start(cmd[0], cmd[1:])
        if not self.web_proc.waitForStarted(5000):
            QMessageBox.critical(self, "Version web", "Le serveur n'a pas pu démarrer (voir le journal web.log).")
            return
        QTimer.singleShot(1500, self._show_web_urls)

    def _show_web_urls(self):
        urls = "\n".join(lan_urls(WEB_PORT))
        QMessageBox.information(self, "Version web démarrée", (
            "Le serveur web fonctionne tant que cette application reste ouverte.\n\n"
            f"Sur cet ordinateur :\n  http://localhost:{WEB_PORT}\n\n"
            f"Pour les autres appareils du même réseau (Wi-Fi) :\n  {urls}\n\n"
            "Les agents se connectent avec l'identifiant et le mot de passe créés dans « Utilisateurs… ».\n"
            f"Toutes les données restent dans : {data_dir()}"))

    def open_web(self):
        QDesktopServices.openUrl(QUrl(f"http://localhost:{WEB_PORT}"))

    def stop_web(self):
        if self.web_proc and self.web_proc.state() != QProcess.NotRunning:
            self.web_proc.terminate()
            if not self.web_proc.waitForFinished(3000):
                self.web_proc.kill()
            self.statusBar().showMessage("Serveur web arrêté.", 4000)

    def show_help(self):
        QMessageBox.information(self, "Aide", (
            "<h3>Mapping Épi</h3>"
            "<ol><li>Créer un cas (Nouveau) ou en choisir un dans la liste à gauche.</li>"
            "<li>Remplir les onglets 1 à 8 ; l'aperçu se met à jour automatiquement.</li>"
            "<li>Consulter « Contrôles » : incohérences, complétude, fenêtres épidémiologiques.</li>"
            "<li>Exporter le visuel affiché (PNG, PDF, SVG, PowerPoint) ou le rapport complet.</li></ol>"
            "<p><b>Règle d'or :</b> une information inconnue reste « ? ». Ne jamais remplacer par 0.</p>"
            "<p>Dates : JJ/MM/AAAA (clic droit sur un champ date pour l'effacer). "
            "Heures labo : JJ/MM/AAAA HH:MM.</p>"
            "<p>Sauvegarde automatique toutes les 30 s ; Ctrl+S crée une version dans l'historique.</p>"
            f"<hr><p style='color:#5F6B7A'>{credits.INSTITUTION}<br>{credits.EQUIPE}<br>Pour tout contact : "
            + ", ".join(f"<a href='mailto:{m}'>{m}</a>" for m in credits.CONTACTS) + "</p>"))

    def closeEvent(self, e):
        self.stop_web()
        try:
            self.collect()
            if self.dirty:
                self.store.save(self.case)
        except Exception:
            log.exception("Sauvegarde à la fermeture")
        try:
            from core import securite as SEC
            d = SEC.lire(self.store, "dossier_sauvegarde")
            if d and Path(d).is_dir():
                SEC.sauvegarder(self.store, d)
        except Exception:
            log.exception("Sauvegarde automatique à la fermeture")
        super().closeEvent(e)
