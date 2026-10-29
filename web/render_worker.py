"""Processus de rendu (appelé par web/render_client.py) : python -m web.render_worker job.json"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.models import Case  # noqa: E402
from render import dashboard, gantt, html_renderer as H, map_view, network  # noqa: E402
from render.pptx_exporter import export_report_pptx  # noqa: E402


def visual_html(c: Case, key: str, others) -> str:
    if key == "mapping":
        return H.render_mapping_html(c)
    if key == "dashboard":
        return H.render_svg_page(dashboard.render_svg(others or [c], c.zs), "Multi-cas")
    mod = {"network": network, "route": map_view, "gantt": gantt}[key]
    return H.render_svg_page(mod.render_svg(c), key)


def main() -> int:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    app = QApplication(sys.argv[:1])
    from ui.exporter import Exporter, pdf_pages_to_png
    c = Case.model_validate(job["case"])
    others = [Case.model_validate(o) for o in job.get("others", [])]
    out = Path(job["out"])
    fmt, key = job["fmt"], job["visual"]
    ex = Exporter()
    result = {"ok": False}

    def finish(ok, _p=None):
        result["ok"] = bool(ok)
        app.quit()

    def start():
        if fmt in ("png", "png4k"):
            ex.to_png(visual_html(c, key, others), out, 3840 if fmt == "png4k" else 1920, finish)
        elif fmt in ("pdf", "pdfa4"):
            html = visual_html(c, key, others)
            if fmt == "pdfa4":
                html = H.with_css(html, H.A4_CSS)
            ex.to_pdf(html, out, finish, a4=(fmt == "pdfa4"))
        elif fmt == "rapport-pdf":
            ex.to_pdf(H.render_report_html(c, [network.render_svg(c), map_view.render_svg(c), gantt.render_svg(c)]),
                      out, finish)
        elif fmt == "rapport-pptx":
            tmp = Path(tempfile.mkdtemp(prefix="rapport_"))
            svgs = [network.render_svg(c), map_view.render_svg(c), gantt.render_svg(c)]
            html = H.page("".join(f'<div class="page"><div class="svgpage">{s}</div></div>' for s in svgs),
                          "Visuels").replace("html, body { width: 1280px; height: 720px; overflow: hidden; }",
                                             "html, body { width: 1280px; }")

            def after(ok, _p):
                if ok:
                    export_report_pptx(c, pdf_pages_to_png(tmp / "v.pdf", tmp, 2560), out)
                finish(ok)
            ex.to_pdf(html, tmp / "v.pdf", after)
        else:
            finish(False)

    QTimer.singleShot(0, start)
    QTimer.singleShot(120_000, lambda: finish(False))
    app.exec()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
