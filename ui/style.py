"""Thèmes clair et sombre de l'application de bureau (feuilles de style Qt).

Contrôles plus grands et plus lisibles : hauteur minimale 36 px, police 14 px,
onglets et boutons aérés, focus bien visible.
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

PALETTES = {
    "clair": {
        "bg": "#F3F5F8", "panel": "#FFFFFF", "panel2": "#F8FAFC", "border": "#D3DAE3", "text": "#1B2430",
        "muted": "#5F6B7A", "accent": "#1F5FA8", "accent_text": "#FFFFFF", "accent_soft": "#E3EDF9",
        "input": "#FFFFFF", "hover": "#EAF0F7", "header": "#1F3A5F", "header_text": "#FFFFFF",
        "danger": "#C0392B", "sel": "#CFE0F5", "sel_text": "#10233D", "alt": "#F7F9FC",
    },
    "sombre": {
        "bg": "#161B22", "panel": "#1E252F", "panel2": "#232B36", "border": "#334052", "text": "#E7ECF2",
        "muted": "#9AA6B5", "accent": "#4C8DDB", "accent_text": "#FFFFFF", "accent_soft": "#22344B",
        "input": "#11161D", "hover": "#2A3442", "header": "#0F1A2A", "header_text": "#E7ECF2",
        "danger": "#E5675A", "sel": "#2C4A70", "sel_text": "#FFFFFF", "alt": "#1A2029",
    },
}


def qss(c: dict) -> str:
    return f"""
* {{ font-size: 14px; }}
QMainWindow, QDialog, QWidget {{ background: {c['bg']}; color: {c['text']}; }}
QToolBar {{ background: {c['header']}; border: 0; padding: 6px 8px; spacing: 6px; }}
QToolBar QToolButton {{ color: {c['header_text']}; background: transparent; padding: 8px 14px; border-radius: 7px;
    font-weight: 600; }}
QToolBar QToolButton:hover {{ background: rgba(255,255,255,0.14); }}
QToolBar QToolButton:pressed {{ background: rgba(255,255,255,0.24); }}
QToolBar::separator {{ background: rgba(255,255,255,0.25); width: 1px; margin: 6px 6px; }}
QStatusBar {{ background: {c['panel']}; color: {c['muted']}; border-top: 1px solid {c['border']}; }}
QLabel {{ background: transparent; }}

QPushButton {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 8px;
    padding: 8px 16px; min-height: 22px; font-weight: 600; }}
QPushButton:hover {{ background: {c['hover']}; border-color: {c['accent']}; }}
QPushButton:pressed {{ background: {c['accent_soft']}; }}
QPushButton:focus {{ border: 2px solid {c['accent']}; }}
QPushButton[primary="true"] {{ background: {c['accent']}; color: {c['accent_text']}; border-color: {c['accent']}; }}
QPushButton[primary="true"]:hover {{ background: {c['accent']}; border-color: {c['text']}; }}
QPushButton[danger="true"] {{ color: {c['danger']}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {c['input']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 7px;
    padding: 6px 10px; min-height: 24px; selection-background-color: {c['sel']}; selection-color: {c['sel_text']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QComboBox:focus {{
    border: 2px solid {c['accent']}; }}
QLineEdit::placeholder {{ color: {c['muted']}; }}
QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {{ width: 28px; border: 0; }}
QComboBox QAbstractItemView {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']};
    selection-background-color: {c['sel']}; selection-color: {c['sel_text']}; padding: 4px; outline: 0; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 22px; }}

QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 10px; background: {c['panel']}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {c['muted']}; padding: 10px 16px; margin-right: 2px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600; }}
QTabBar::tab:selected {{ background: {c['panel']}; color: {c['accent']}; border: 1px solid {c['border']};
    border-bottom: 3px solid {c['accent']}; }}
QTabBar::tab:hover:!selected {{ color: {c['text']}; background: {c['hover']}; }}

QTableWidget, QTableView, QListWidget, QTextBrowser {{ background: {c['panel']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 8px; gridline-color: {c['border']};
    alternate-background-color: {c['alt']}; selection-background-color: {c['sel']}; selection-color: {c['sel_text']}; }}
QTableWidget QLineEdit, QTableWidget QComboBox, QTableWidget QDateEdit, QTableWidget QDateTimeEdit {{
    border-radius: 0; padding: 2px 6px; min-height: 0; }}
QHeaderView::section {{ background: {c['panel2']}; color: {c['text']}; padding: 8px 8px; border: 0;
    border-right: 1px solid {c['border']}; border-bottom: 1px solid {c['border']}; font-weight: 700; }}
QListWidget::item {{ padding: 9px 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {c['sel']}; color: {c['sel_text']}; }}
QListWidget::item:hover:!selected {{ background: {c['hover']}; }}

QGroupBox {{ border: 1px solid {c['border']}; border-radius: 10px; margin-top: 18px; padding: 14px 10px 10px;
    background: {c['panel']}; font-weight: 700; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {c['accent']}; }}
QCheckBox {{ spacing: 9px; padding: 3px 0; background: transparent; }}
QCheckBox::indicator {{ width: 20px; height: 20px; }}
QProgressBar {{ border: 1px solid {c['border']}; border-radius: 8px; text-align: center; height: 22px;
    background: {c['input']}; color: {c['text']}; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 7px; }}
QSplitter::handle {{ background: {c['border']}; }}
QSplitter::handle:horizontal {{ width: 2px; }}
QScrollBar:vertical {{ width: 12px; background: transparent; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 6px; min-height: 30px; }}
QScrollBar:horizontal {{ height: 12px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 6px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QMenu {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 6px; }}
QMenu::item {{ padding: 8px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c['sel']}; color: {c['sel_text']}; }}
QToolTip {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 6px; }}
QCalendarWidget QWidget {{ alternate-background-color: {c['panel2']}; }}
QCalendarWidget QToolButton {{ color: {c['text']}; background: transparent; padding: 6px 10px; font-weight: 700; }}
QCalendarWidget QAbstractItemView:enabled {{ background: {c['panel']}; color: {c['text']};
    selection-background-color: {c['accent']}; selection-color: #FFFFFF; }}
QCalendarWidget QAbstractItemView:disabled {{ color: {c['muted']}; }}
QCalendarWidget #qt_calendar_navigationbar {{ background: {c['panel2']}; }}
#hint {{ color: {c['muted']}; font-size: 13px; padding: 2px 0 8px 0; }}
#sideTitle {{ font-size: 15px; font-weight: 800; color: {c['text']}; padding: 4px 0; }}
#warn {{ color: {c['danger']}; font-weight: 600; }}
"""


def system_prefers_dark() -> bool:
    app = QApplication.instance()
    try:
        from PySide6.QtCore import Qt
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return app.palette().color(QPalette.Window).lightness() < 128


def apply_theme(name: str) -> str:
    """name : 'clair', 'sombre' ou 'systeme'. Retourne le thème réellement appliqué."""
    app = QApplication.instance()
    if name == "systeme":
        name = "sombre" if system_prefers_dark() else "clair"
    c = PALETTES[name]
    app.setStyle(QStyleFactory.create("Fusion"))
    pal = QPalette()
    for role, key in [(QPalette.Window, "bg"), (QPalette.WindowText, "text"), (QPalette.Base, "input"),
                      (QPalette.AlternateBase, "alt"), (QPalette.Text, "text"), (QPalette.Button, "panel"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "accent"),
                      (QPalette.HighlightedText, "accent_text"), (QPalette.ToolTipBase, "panel"),
                      (QPalette.ToolTipText, "text"), (QPalette.PlaceholderText, "muted")]:
        pal.setColor(role, QColor(c[key]))
    app.setPalette(pal)
    app.setStyleSheet(qss(c))
    return name
