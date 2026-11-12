"""Crée les icônes de l'application (assets/icons) : PNG, .ico (Windows) et .icns (Mac).

    python packaging/make_icons.py
"""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QBuffer, QByteArray, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "icons"


def draw(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 1024
    m = 64 * s
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#1F3B5A"))
    p.drawRoundedRect(QRectF(m, m, size - 2 * m, size - 2 * m), 200 * s, 200 * s)
    # chaîne : trois points reliés (cas source → cas)
    pen = QPen(QColor("#9FB7CF"), 34 * s)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    a, b, c = QPointF(280 * s, 720 * s), QPointF(500 * s, 560 * s), QPointF(740 * s, 700 * s)
    p.drawLine(a, b)
    p.drawLine(b, c)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#9FB7CF"))
    for pt in (a, c):
        p.drawEllipse(pt, 62 * s, 62 * s)
    # repère (lieu) au-dessus du point central
    cx, top = 512 * s, 170 * s
    r = 150 * s
    path = QPainterPath()
    path.moveTo(cx, 560 * s)
    path.cubicTo(cx - 40 * s, 470 * s, cx - r, 420 * s, cx - r, top + r)
    path.arcTo(QRectF(cx - r, top, 2 * r, 2 * r), 180, -180)
    path.cubicTo(cx + r, 420 * s, cx + 40 * s, 470 * s, cx, 560 * s)
    p.setBrush(QColor("#FFFFFF"))
    p.drawPath(path)
    p.setBrush(QColor("#B4554E"))
    p.drawEllipse(QPointF(cx, top + r), 64 * s, 64 * s)
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def write_ico(path: Path, sizes=(16, 24, 32, 48, 64, 128, 256)) -> None:
    imgs = [png_bytes(draw(n)) for n in sizes]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    off = 6 + 16 * len(sizes)
    entries, data = b"", b""
    for n, b in zip(sizes, imgs):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(b), off + len(data))
        data += b
    path.write_bytes(head + entries + data)


def main() -> int:
    QGuiApplication(sys.argv[:1])
    OUT.mkdir(parents=True, exist_ok=True)
    draw(1024).save(str(OUT / "mapping_epi.png"))
    draw(256).save(str(OUT / "mapping_epi_256.png"))
    write_ico(OUT / "mapping_epi.ico")
    if sys.platform == "darwin":
        with tempfile.TemporaryDirectory() as t:
            iset = Path(t) / "mapping_epi.iconset"
            iset.mkdir()
            for n in (16, 32, 128, 256, 512):
                draw(n).save(str(iset / f"icon_{n}x{n}.png"))
                draw(2 * n).save(str(iset / f"icon_{n}x{n}@2x.png"))
            subprocess.run(["iconutil", "-c", "icns", str(iset), "-o", str(OUT / "mapping_epi.icns")], check=True)
    print("icônes :", sorted(x.name for x in OUT.iterdir()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
