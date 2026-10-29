"""Mapping Épi — point d'entrée.

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

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
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
        QMessageBox.critical(None, "Erreur", f"Une erreur est survenue (détails dans logs/app.log) :\n\n{exc}")
    except Exception:
        pass


def main() -> int:
    sys.excepthook = _excepthook
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Mapping Épi")
    app.setOrganizationName("MappingEpi")
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
