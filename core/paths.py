"""Emplacement du dossier de données LOCAL.

Toutes les données (cas, versions, comptes utilisateurs, exports, listes
personnalisées) sont gardées dans UN dossier local, partagé par l'application
de bureau et le serveur web :

    <projet>/donnees/
        mapping_epi.sqlite      cas + historique des versions + comptes
        cas/<id>.json           copie lisible de chaque fiche (sauvegarde)
        exports/                fichiers générés par la version web
        pyramide_perso.csv      aires de santé ajoutées à la saisie
        secret.key              clé de session du serveur web

Version installée (Windows .exe, Mac .app) : le dossier du programme n'est pas
modifiable, les données vont dans le dossier de l'utilisateur :
    Windows : %LOCALAPPDATA%\\Mapping Epi\\donnees
    Mac     : ~/Library/Application Support/Mapping Epi/donnees

Pour utiliser un autre dossier (disque externe, dossier synchronisé…),
définir la variable d'environnement MAPPING_EPI_DONNEES.
Ce dossier n'est jamais envoyé sur GitHub (.gitignore).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
# vrai dans la version installée (PyInstaller) : ROOT pointe alors vers les fichiers du programme, en lecture seule
FROZEN = bool(getattr(sys, "frozen", False))


def user_dir() -> Path:
    """Dossier de l'utilisateur pour la version installée."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "Mapping Epi"


def logs_dir() -> Path:
    d = (user_dir() / "journaux") if FROZEN else (ROOT / "logs")
    d.mkdir(parents=True, exist_ok=True)
    return d


def commande(role: str, *args: str) -> List[str]:
    """Commande pour lancer un processus interne : « serveur-web » ou « rendu ».
    Version installée : le programme lui-même avec une option ; sinon Python et le script."""
    if FROZEN:
        return [sys.executable, f"--{role}", *args]
    if role == "serveur-web":
        return [sys.executable, str(ROOT / "serveur_web.py"), *args]
    return [sys.executable, "-m", "web.render_worker", *args]


def data_dir() -> Path:
    defaut = (user_dir() / "donnees") if FROZEN else (ROOT / "donnees")
    d = Path(os.environ.get("MAPPING_EPI_DONNEES") or defaut).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    (d / "cas").mkdir(exist_ok=True)
    (d / "exports").mkdir(exist_ok=True)
    _migrate_old(d)
    return d


def db_path() -> Path:
    return data_dir() / "mapping_epi.sqlite"


def _migrate_old(d: Path) -> None:
    """Reprend la base de la version 1.0 (dossier data/) si elle existe."""
    old = ROOT / "data" / "mapping_epi.sqlite"
    new = d / "mapping_epi.sqlite"
    if old.exists() and not new.exists():
        import sqlite3
        src = sqlite3.connect(str(old))
        dst = sqlite3.connect(str(new))
        src.backup(dst)          # copie cohérente même avec le journal WAL
        src.close()
        dst.close()
        try:
            shutil.move(str(old.parent), str(ROOT / "data_ancienne_version"))
        except OSError:
            pass
