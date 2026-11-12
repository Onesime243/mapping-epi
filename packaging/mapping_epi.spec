# -*- mode: python ; coding: utf-8 -*-
# Construction de l'application installable (sans connexion) :
#     pyinstaller packaging/mapping_epi.spec --noconfirm
# Résultat : dist/Mapping Epi/ (Windows : Mapping Epi.exe) ou dist/Mapping Epi.app (Mac).
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
VERSION = (Path(SPECPATH) / "VERSION").read_text().strip()
NAME = "Mapping Epi"

datas = []
for rel in ("config", "assets", "render/templates", "web/templates", "web/static", "sample_data"):
    src = ROOT / rel
    for f in src.rglob("*"):
        if f.is_file() and f.suffix not in (".py", ".pyc") and "__pycache__" not in f.parts and f.name != ".DS_Store":
            datas.append((str(f), str(f.parent.relative_to(ROOT))))
datas += collect_data_files("docx") + collect_data_files("pptx")

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=["serveur_web", "web.render_worker", "web.server", "waitress", "openpyxl", "yaml",
                   "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore", "PySide6.QtPdf", "PySide6.QtSvg",
                   "PySide6.QtPrintSupport"],
    excludes=["tkinter", "pytest", "_pytest", "IPython", "matplotlib", "numpy.tests"],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon = str(ROOT / "assets" / "icons" / ("mapping_epi.icns" if sys.platform == "darwin" else "mapping_epi.ico"))
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=NAME,
    console=False,
    icon=icon,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{NAME}.app",
        icon=icon,
        bundle_identifier="cd.riposte.mappingepi",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": "Mapping Épi",
            "CFBundleName": "Mapping Épi",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "13.0",
            "NSHumanReadableCopyright": "Riposte MVE, RDC",
        },
    )
