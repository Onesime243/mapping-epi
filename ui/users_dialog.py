"""Gestion des comptes de la version web (administrateur)."""
from __future__ import annotations

from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from core import pyramide
from core.users import NIVEAUX, Users, generate_password
from ui.widgets import SearchCombo


class ScopeFields:
    """Niveau + Province → ZS → AS (listes en cascade), partagé par les deux fenêtres."""

    def __init__(self, form: QFormLayout, user=None):
        self.pyr = pyramide.get()
        self.niveau = QComboBox()
        for k, label in NIVEAUX.items():
            self.niveau.addItem(label, k)
        self.province = SearchCombo("Province…")
        self.zs = SearchCombo("Zone de santé…")
        self.aire = SearchCombo("Aire de santé (facultatif)…")
        self.province.set_items(self.pyr.provinces())
        self.zs.set_items(self.pyr.zones())
        self.province.changed.connect(lambda p: self.zs.set_items(self.pyr.zones(p) if p.strip() else self.pyr.zones()))
        self.zs.changed.connect(lambda z: self.aire.set_items(self.pyr.aires(self.province.text(), z)))
        self.rows = [("Niveau", self.niveau), ("Province", self.province), ("Zone de santé", self.zs),
                     ("Aire de santé", self.aire)]
        for label, w in self.rows:
            form.addRow(label, w)
        self.form = form
        self.niveau.currentIndexChanged.connect(self._show)
        self.niveau.setCurrentIndex(self.niveau.findData(user.niveau if user else "aire"))
        if user:
            self.province.setText(user.province)
            self.zs.setText(user.zs)
            self.aire.setText(user.aire)
        self._show()

    def _show(self):
        n = self.niveau.currentData()
        need = {"Province": n in ("province", "zone", "aire"), "Zone de santé": n in ("zone", "aire"),
                "Aire de santé": n == "aire"}
        for label, w in self.rows[1:]:
            self.form.setRowVisible(w, need[label])

    def values(self):
        return self.niveau.currentData(), self.province.text(), self.zs.text(), self.aire.text()


RIGHTS = ("Aire de santé : voit et corrige ses propres cas. Zone de santé : voit tous les cas de sa ZS et corrige "
          "ceux de ses aires. Provincial : voit tous les cas de sa province. National : voit tous les cas. "
          "Administrateur : tout, plus la gestion des comptes.")


class ScopeDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Niveau du compte « {user.username} »")
        self.setMinimumWidth(460)
        f = QFormLayout(self)
        self.scope = ScopeFields(f, user)
        hint = QLabel(RIGHTS)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class NewUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau compte")
        self.setMinimumWidth(460)
        f = QFormLayout(self)
        self.username = QLineEdit()
        self.username.setPlaceholderText("ex. agent.ganga")
        self.nom = QLineEdit()
        self.nom.setPlaceholderText("Nom complet")
        self.role = QComboBox()
        self.role.addItems(["agent", "admin"])
        self.pwd = QLineEdit(generate_password())
        self.pwd.setToolTip("Mot de passe proposé : vous pouvez le remplacer (8 caractères minimum, lettres et chiffres).")
        f.addRow("Identifiant", self.username)
        f.addRow("Nom", self.nom)
        f.addRow("Rôle", self.role)
        self.scope = ScopeFields(f)
        self.role.currentTextChanged.connect(
            lambda r: r == "admin" and self.scope.niveau.setCurrentIndex(self.scope.niveau.findData("national")))
        f.addRow("Mot de passe", self.pwd)
        hint = QLabel(RIGHTS)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Créer le compte")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class UsersDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.users = Users(store)
        self.setWindowTitle("Utilisateurs de la version web")
        self.resize(820, 480)
        lay = QVBoxLayout(self)
        info = QLabel("Chaque agent reçoit un identifiant et un mot de passe. Les mots de passe sont chiffrés "
                      "(PBKDF2) dans la base locale ; notez-les au moment de la création.")
        info.setObjectName("hint")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Identifiant", "Nom", "Rôle", "Niveau", "Périmètre", "Actif",
                                              "Dernière connexion"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table)
        row = QHBoxLayout()
        for label, slot, prop in [("＋ Nouveau compte", self.add, "primary"), ("Réinitialiser le mot de passe", self.reset, ""),
                                  ("Activer / désactiver", self.toggle, ""), ("Changer le rôle", self.switch_role, ""),
                                  ("Niveau / périmètre…", self.change_scope, "")]:
            b = QPushButton(label)
            if prop:
                b.setProperty(prop, True)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        close = QPushButton("Fermer")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)
        self.refresh()
        if self.users.count() == 0:
            QMessageBox.information(self, "Premier compte", "Aucun compte n'existe encore : créez d'abord votre compte "
                                                            "administrateur.")

    def refresh(self):
        us = self.users.list()
        self.table.setRowCount(len(us))
        for r, u in enumerate(us):
            for c, v in enumerate([u.username, u.nom, u.role, u.niveau_label, u.perimetre, "oui" if u.actif else "non",
                                   (u.derniere_connexion or "jamais").replace("T", " ")]):
                it = QTableWidgetItem(v)
                if c == 5 and not u.actif:
                    it.setForeground(QColor("#C0392B"))
                self.table.setItem(r, c, it)

    def _selected(self):
        r = self.table.currentRow()
        return self.table.item(r, 0).text() if r >= 0 and self.table.item(r, 0) else None

    def _show_password(self, username, pwd):
        QGuiApplication.clipboard().setText(pwd)
        QMessageBox.information(self, "Mot de passe", f"Identifiant : {username}\nMot de passe : {pwd}\n\n"
                                "Le mot de passe a été copié dans le presse-papiers. Transmettez-le à la personne : "
                                "il ne sera plus affiché.")

    def add(self):
        d = NewUserDialog(self)
        if self.users.count() == 0:
            d.role.setCurrentText("admin")
        while d.exec():
            try:
                niveau, prov, zs, aire = d.scope.values()
                u = self.users.create(d.username.text(), d.pwd.text(), d.nom.text(), d.role.currentText(), zs,
                                      niveau, prov, aire)
            except ValueError as exc:
                QMessageBox.warning(self, "Compte", str(exc))
                continue
            self.refresh()
            self._show_password(u.username, d.pwd.text())
            break

    def reset(self):
        u = self._selected()
        if not u:
            return
        pwd = generate_password()
        if QMessageBox.question(self, "Réinitialiser", f"Générer un nouveau mot de passe pour « {u} » ?") == QMessageBox.Yes:
            self.users.set_password(u, pwd)
            self._show_password(u, pwd)

    def toggle(self):
        u = self._selected()
        if not u:
            return
        try:
            self.users.update(u, actif=not self.users.get(u).actif)
        except ValueError as exc:
            QMessageBox.warning(self, "Compte", str(exc))
        self.refresh()

    def change_scope(self):
        name = self._selected()
        if not name:
            return
        u = self.users.get(name)
        if u.is_admin:
            QMessageBox.information(self, "Niveau", "Un administrateur est toujours de niveau national.")
            return
        d = ScopeDialog(u, self)
        while d.exec():
            try:
                self.users.set_scope(name, *d.scope.values())
            except ValueError as exc:
                QMessageBox.warning(self, "Niveau", str(exc))
                continue
            self.refresh()
            break

    def switch_role(self):
        u = self._selected()
        if not u:
            return
        try:
            self.users.update(u, role="agent" if self.users.get(u).is_admin else "admin")
        except ValueError as exc:
            QMessageBox.warning(self, "Compte", str(exc))
        self.refresh()
