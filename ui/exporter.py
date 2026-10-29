"""Moteur d'export Qt : HTML → PDF vectoriel (QtWebEngine) → PNG haute résolution (QtPdf).

Passer par le PDF garantit que le PNG est identique à l'aperçu, net à toute
résolution (1920×1080, 3840×2160…) et indépendant de l'écran.
"""
from __future__ import annotations

import logging
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Deque, Optional

from PySide6.QtCore import QMarginsF, QObject, QSize, QSizeF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWebEngineWidgets import QWebEngineView

from render.html_renderer import ASSETS

log = logging.getLogger(__name__)


def layout_169() -> QPageLayout:
    return QPageLayout(QPageSize(QSizeF(960, 540), QPageSize.Unit.Point, "16:9", QPageSize.SizeMatchPolicy.ExactMatch),
                       QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0))


def layout_a4() -> QPageLayout:
    return QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Landscape, QMarginsF(0, 0, 0, 0))


@dataclass
class Job:
    html: str
    pdf_path: Path
    layout: QPageLayout
    done: Callable[[bool, Path], None]


class Exporter(QObject):
    """File d'attente d'impressions PDF sur une vue web invisible."""
    busy = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWebEngineView()
        self.view.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.view.resize(1280, 720)
        self.view.show()
        self.page = self.view.page()
        self.page.loadFinished.connect(self._loaded)
        self.page.pdfPrintingFinished.connect(self._printed)
        self.queue: Deque[Job] = deque()
        self.current: Optional[Job] = None
        self._polls = 0
        self.tmp = Path(tempfile.mkdtemp(prefix="mapping_epi_"))

    # -- API ------------------------------------------------------------
    def to_pdf(self, html: str, path: Path, done: Callable[[bool, Path], None], a4: bool = False):
        self.queue.append(Job(html, Path(path), layout_a4() if a4 else layout_169(), done))
        self._next()

    def to_png(self, html: str, path: Path, width: int, done: Callable[[bool, Path], None]):
        pdf = self.tmp / (Path(path).stem + ".pdf")

        def after(ok: bool, _p: Path):
            if not ok:
                done(False, Path(path))
                return
            done(pdf_to_png(pdf, Path(path), width), Path(path))
        self.to_pdf(html, pdf, after)

    # -- interne ----------------------------------------------------------
    def _next(self):
        if self.current or not self.queue:
            return
        self.current = self.queue.popleft()
        self.busy.emit(True)
        self.page.setHtml(self.current.html, QUrl.fromLocalFile(str(ASSETS) + "/"))

    def _loaded(self, ok: bool):
        if not self.current:
            return
        if not ok:
            self._finish(False)
            return
        self._polls = 0
        self._poll()

    def _poll(self):
        def got(val):
            self._polls += 1
            if val or self._polls > 40:
                QTimer.singleShot(80, self._print)
            else:
                QTimer.singleShot(75, self._poll)
        self.page.runJavaScript("window.__fitDone === true", 0, got)

    def _print(self):
        if self.current:
            self.page.printToPdf(str(self.current.pdf_path), self.current.layout)

    def _printed(self, path: str, ok: bool):
        self._finish(ok)

    def _finish(self, ok: bool):
        job, self.current = self.current, None
        if job:
            try:
                job.done(ok, job.pdf_path)
            except Exception:  # pragma: no cover
                log.exception("Erreur dans le rappel d'export")
        if not self.queue:
            self.busy.emit(False)
        self._next()


def pdf_to_png(pdf: Path, png: Path, width: int, page: int = 0) -> bool:
    doc = QPdfDocument()
    doc.load(str(pdf))
    if doc.status() != QPdfDocument.Status.Ready or doc.pageCount() == 0:
        log.error("Impossible de lire %s", pdf)
        return False
    size = doc.pagePointSize(page)
    height = round(width * size.height() / size.width())
    img = doc.render(page, QSize(width, height))
    ok = img.save(str(png), "PNG")
    doc.close()
    return ok


def pdf_pages_to_png(pdf: Path, out_dir: Path, width: int) -> list:
    doc = QPdfDocument()
    doc.load(str(pdf))
    out = []
    for p in range(doc.pageCount()):
        size = doc.pagePointSize(p)
        img = doc.render(p, QSize(width, round(width * size.height() / size.width())))
        f = out_dir / f"page_{p + 1}.png"
        img.save(str(f), "PNG")
        out.append(f)
    doc.close()
    return out
