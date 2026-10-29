"""Lance le rendu PNG / PDF dans un processus séparé (Qt WebEngine), un à la fois.

Le serveur web reste léger et stable : chaque export ouvre un petit processus
qui produit le fichier puis se ferme. Même moteur que l'application de bureau,
donc des fichiers identiques.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
_lock = threading.Lock()


def render(case: dict, visual: str, fmt: str, out: Path, others: List[dict] | None = None,
           timeout: int = 150) -> Tuple[bool, str]:
    job = {"case": case, "visual": visual, "fmt": fmt, "out": str(out), "others": others or []}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(job, f)
        job_path = f.name
    env = dict(os.environ)
    env["QT_MAC_DISABLE_FOREGROUND_APPLICATION_TRANSFORM"] = "1"   # pas d'icône dans le Dock (macOS)
    if sys.platform.startswith("linux") and not env.get("DISPLAY") and not env.get("WAYLAND_DISPLAY"):
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        # serveur sans écran : pas de GPU ; le bac à sable Chromium est souvent bloqué par AppArmor (Ubuntu 24.04).
        # Le moteur n'affiche que les pages générées par l'outil lui-même.
        env.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")
    try:
        with _lock:
            p = subprocess.run([sys.executable, "-m", "web.render_worker", job_path], cwd=str(ROOT), env=env,
                               capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0 and out.exists() and out.stat().st_size > 0:
            return True, ""
        return False, (p.stderr or p.stdout or "erreur inconnue").strip()[-400:]
    except subprocess.TimeoutExpired:
        return False, "délai dépassé"
    except Exception as exc:     # PySide6 absent, etc.
        return False, str(exc)
    finally:
        try:
            os.unlink(job_path)
        except OSError:
            pass
