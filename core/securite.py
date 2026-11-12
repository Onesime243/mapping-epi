"""Application de bureau : mot de passe de démarrage, sauvegardes automatiques, nouvelle version.

Le mot de passe empêche d'ouvrir l'application sur un ordinateur laissé sans surveillance. Il ne chiffre pas le
disque : pour une vraie protection en cas de vol, activer BitLocker (Windows) ou FileVault (Mac).
"""
from __future__ import annotations

import re
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional

GABARIT = "MappingEpi_sauvegarde_{:%Y-%m-%d_%H%M}.sqlite"
MOTIF = re.compile(r"^MappingEpi_sauvegarde_\d{4}-\d{2}-\d{2}_\d{4}\.sqlite$")
DEPOT = "Onesime243/mapping-epi"


# -- réglages gardés dans la base locale ----------------------------------------------------------
def _init(store) -> None:
    store.db.execute("CREATE TABLE IF NOT EXISTS reglages(cle TEXT PRIMARY KEY, valeur TEXT)")


def lire(store, cle: str, defaut: str = "") -> str:
    _init(store)
    r = store.db.execute("SELECT valeur FROM reglages WHERE cle=?", (cle,)).fetchone()
    return r[0] if r and r[0] is not None else defaut


def ecrire(store, cle: str, valeur: str) -> None:
    _init(store)
    with store.lock:
        store.db.execute("INSERT INTO reglages(cle, valeur) VALUES(?,?) ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur",
                         (cle, valeur))
        store.db.commit()


# -- mot de passe de démarrage -----------------------------------------------------------------------
def a_mot_de_passe(store) -> bool:
    return bool(lire(store, "verrou"))


def definir_mot_de_passe(store, mdp: str) -> None:
    from core.users import hash_password, validate_password
    err = validate_password(mdp)
    if err:
        raise ValueError(err)
    ecrire(store, "verrou", hash_password(mdp))


def retirer_mot_de_passe(store) -> None:
    ecrire(store, "verrou", "")


def verifier_mot_de_passe(store, mdp: str) -> bool:
    from core.users import check_password
    h = lire(store, "verrou")
    return not h or check_password(mdp, h)


# -- sauvegardes -------------------------------------------------------------------------------------------
def sauvegarder(store, dossier: Path | str, garder: int = 20) -> Path:
    """Copie cohérente de la base (fiches, historique, comptes) dans `dossier` ; garde les `garder` dernières."""
    d = Path(dossier).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    out = d / GABARIT.format(datetime.now())
    dst = sqlite3.connect(str(out))
    with store.lock:
        store.db.commit()
        src = sqlite3.connect(str(store.path))
        src.backup(dst)
        src.close()
    dst.close()
    anciennes = sorted(p for p in d.iterdir() if MOTIF.match(p.name))
    for p in anciennes[:-garder]:
        try:
            p.unlink()
        except OSError:
            pass
    ecrire(store, "derniere_sauvegarde", datetime.now().isoformat(timespec="seconds"))
    return out


def sauvegarde_due(store, heures: int = 24) -> bool:
    if not lire(store, "dossier_sauvegarde"):
        return False
    last = lire(store, "derniere_sauvegarde")
    try:
        return datetime.now() - datetime.fromisoformat(last) >= timedelta(hours=heures)
    except ValueError:
        return True


def restaurer(store, fichier: Path | str, auteur: str = ""):
    """Reprend les fiches d'une sauvegarde SANS rien écraser de plus récent (même règles qu'un paquet)."""
    from core import echanges as ECH
    from core.storage import Store
    src = Store(fichier, mirror_json=False)
    try:
        data = ECH.paquet_bytes(src.all_cases(), auteur, f"sauvegarde {Path(fichier).name}")
    finally:
        src.close()
    return ECH.importer_paquet(store, data, auteur or "restauration")


# -- nouvelle version ---------------------------------------------------------------------------------
def version_locale() -> str:
    from core.paths import ROOT
    try:
        return (ROOT / "packaging" / "VERSION").read_text().strip()
    except OSError:
        return ""


def _tuple(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def verifier_version(rappel: Callable[[str], None], timeout: int = 6) -> None:
    """En arrière-plan : si une version plus récente est publiée sur GitHub, appelle rappel(version).
    Sans internet : rien ne se passe. Aucune donnée n'est envoyée."""
    def run():
        import urllib.request
        from core.sync import _contexte_ssl
        try:
            req = urllib.request.Request(f"https://raw.githubusercontent.com/{DEPOT}/main/packaging/VERSION",
                                         headers={"User-Agent": "MappingEpi-bureau"})
            with urllib.request.urlopen(req, timeout=timeout, context=_contexte_ssl()) as r:
                distante = r.read(32).decode("utf-8", "replace").strip()
        except Exception:
            return
        loc = version_locale()
        if loc and _tuple(distante) > _tuple(loc):
            rappel(distante)
    threading.Thread(target=run, daemon=True).start()


def liste_sauvegardes(dossier: Path | str) -> List[Path]:
    d = Path(dossier)
    return sorted((p for p in d.iterdir() if MOTIF.match(p.name)), reverse=True) if d.is_dir() else []
