"""Mapping Épi : point d'entrée.

Lancement :  python app.py
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# version installée sans console (Windows) : sorties standard absentes
for _n in ("stdout", "stderr"):
    if getattr(sys, _n) is None:
        setattr(sys, _n, open(os.devnull, "w", encoding="utf-8"))

# version installée : le même exécutable sert aussi de serveur web et de processus de rendu
if len(sys.argv) > 1 and sys.argv[1] in ("--serveur-web", "--rendu"):
    _role = sys.argv.pop(1)
    if _role == "--serveur-web":
        import serveur_web
        sys.exit(serveur_web.main())
    from web import render_worker
    sys.exit(render_worker.main())

from core.paths import logs_dir  # noqa: E402

LOG_DIR = logs_dir()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    handlers=[RotatingFileHandler(LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger("mapping_epi")

# QtWebEngine refuse de démarrer en root sous Linux sans cette option
if sys.platform.startswith("linux") and hasattr(os, "geteuid") and os.geteuid() == 0:
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from core.storage import Store  # noqa: E402


def _excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    log.error("Erreur non gérée :\n%s", text)
    try:
        QMessageBox.critical(None, "Erreur", f"Une erreur est survenue (détails dans {LOG_DIR / 'app.log'}) :\n\n{exc}")
    except Exception:
        pass


def main() -> int:
    sys.excepthook = _excepthook
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Mapping Épi")
    app.setOrganizationName("MappingEpi")
    from PySide6.QtGui import QIcon
    icon = ROOT / "assets" / "icons" / "mapping_epi.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    for f in (ROOT / "assets" / "fonts").glob("Inter-*.otf"):
        QFontDatabase.addApplicationFont(str(f))
    if "Inter" in QFontDatabase.families():
        app.setFont(QFont("Inter", 10))
    from ui.main_window import MainWindow
    store = Store()
    win = MainWindow(store)
    win.show()
    code = app.exec()
    store.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
