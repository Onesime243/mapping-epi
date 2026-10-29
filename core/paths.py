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

Pour utiliser un autre dossier (disque externe, dossier synchronisé…),
définir la variable d'environnement MAPPING_EPI_DONNEES.
Ce dossier n'est jamais envoyé sur GitHub (.gitignore).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    d = Path(os.environ.get("MAPPING_EPI_DONNEES") or (ROOT / "donnees")).expanduser()
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
