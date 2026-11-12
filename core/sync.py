"""Synchronisation de l'application de bureau avec le serveur.

Côté serveur : jetons personnels (créés depuis « Mon compte »). Le jeton n'est montré qu'une fois ; seule son
empreinte (SHA-256) est gardée. Un jeton agit avec les droits du compte qui l'a créé et peut être révoqué.
Côté bureau : l'application envoie ses fiches (paquet) puis reçoit les fiches visibles par ce compte, avec les
mêmes règles que l'import d'un paquet (rien n'est perdu, la version la plus récente l'emporte).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from typing import List, Optional, Tuple

PREFIXE = "mepi_"


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.strip().encode("utf-8")).hexdigest()


def init(store) -> None:
    store.db.execute("""CREATE TABLE IF NOT EXISTS sync_jetons(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, nom TEXT, empreinte TEXT UNIQUE NOT NULL,
        cree_le TEXT, dernier_usage TEXT, actif INTEGER NOT NULL DEFAULT 1)""")
    store.db.commit()


def creer_jeton(store, username: str, nom: str = "") -> str:
    init(store)
    jeton = PREFIXE + secrets.token_urlsafe(30)
    with store.lock:
        store.db.execute("INSERT INTO sync_jetons(username, nom, empreinte, cree_le) VALUES(?,?,?,?)",
                         (username, (nom or "Ordinateur")[:60], _empreinte(jeton),
                          datetime.now().isoformat(timespec="seconds")))
        store.db.commit()
    return jeton


def jetons(store, username: str) -> List[dict]:
    init(store)
    cols = ("id", "nom", "cree_le", "dernier_usage")
    return [dict(zip(cols, r)) for r in store.db.execute(
        "SELECT id, nom, cree_le, dernier_usage FROM sync_jetons WHERE username=? AND actif=1 ORDER BY id DESC",
        (username,))]


def revoquer(store, username: str, jid: int) -> None:
    init(store)
    with store.lock:
        store.db.execute("UPDATE sync_jetons SET actif=0 WHERE id=? AND username=?", (int(jid), username))
        store.db.commit()


def verifier(store, jeton: str) -> Optional[str]:
    """Nom du compte du jeton, ou None."""
    if not jeton or not jeton.startswith(PREFIXE):
        return None
    init(store)
    r = store.db.execute("SELECT id, username FROM sync_jetons WHERE empreinte=? AND actif=1",
                         (_empreinte(jeton),)).fetchone()
    if not r:
        return None
    with store.lock:
        store.db.execute("UPDATE sync_jetons SET dernier_usage=? WHERE id=?",
                         (datetime.now().isoformat(timespec="seconds"), r[0]))
        store.db.commit()
    return r[1]


# ---------------------------------------------------------------------------
# client (application de bureau)
# ---------------------------------------------------------------------------
def _contexte_ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _requete(url: str, jeton: str, data: Optional[bytes] = None, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET",
                                 headers={"Authorization": f"Bearer {jeton}", "User-Agent": "MappingEpi-bureau",
                                          "Content-Type": "application/zip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_contexte_ssl()) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8")).get("error", "")
        except Exception:
            msg = ""
        raise RuntimeError(msg or f"le serveur a répondu {exc.code}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"serveur injoignable ({exc.reason})") from None


def synchroniser(store, url: str, jeton: str) -> Tuple[str, str]:
    """Envoie puis reçoit. Renvoie (bilan de l'envoi, bilan de la réception)."""
    from core import echanges as ECH
    base = url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    envoi = json.loads(_requete(base + "/api/sync/envoyer", jeton,
                                ECH.paquet_bytes([c for c in store.all_cases() if not c.exemple()], "bureau",
                                                 "application de bureau")))
    recu = ECH.importer_paquet(store, _requete(base + "/api/sync/recevoir", jeton), envoi.get("compte", "serveur"))
    return envoi.get("bilan", ""), recu.texte()
