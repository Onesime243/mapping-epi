"""Suivi des alertes du tableau de bord : nouvelle → prise en charge → résolue (→ réapparue).

Les alertes elles-mêmes restent calculées par les règles (core/tableau_bord.py) ; on garde seulement, pour chaque
cas, l'état décidé par un super-administrateur, qui l'a décidé, quand, une note courte, et la « signature » des
alertes au moment de la résolution. Une alerte résolue qui est encore vraie au calcul suivant revient en
« réapparue » (la fiche montre toujours le problème) ; une alerte de nature nouvelle revient en « nouvelle ».
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

ETATS = ("nouvelle", "prise", "resolue")


def init(store) -> None:
    store.db.execute("""CREATE TABLE IF NOT EXISTS alertes_suivi(
        cid TEXT PRIMARY KEY, etat TEXT NOT NULL, par TEXT, le TEXT, note TEXT, signature TEXT)""")
    store.db.execute("""CREATE TABLE IF NOT EXISTS alertes_historique(
        id INTEGER PRIMARY KEY AUTOINCREMENT, cid TEXT, code TEXT, etat TEXT, par TEXT, le TEXT, note TEXT, resume TEXT)""")
    store.db.commit()


def type_alerte(texte: str) -> str:
    """Nature d'une alerte, sans ses chiffres : « 12 contacts … aucun en suivi » → « contacts … aucun en suivi »."""
    t = re.sub(r"\([^)]*\)", " ", (texte or "").lower())
    t = re.sub(r"[\d.,%]+", " ", t)
    return " ".join(t.split())


def signature(textes: Iterable[str]) -> str:
    return "|".join(sorted({type_alerte(t) for t in textes if t}))


def etats(store) -> Dict[str, dict]:
    init(store)
    cols = ("cid", "etat", "par", "le", "note", "signature")
    return {r[0]: dict(zip(cols, r)) for r in store.db.execute(f"SELECT {', '.join(cols)} FROM alertes_suivi")}


def marquer(store, cid: str, etat: str, par: str, textes: List[str], code: str = "", note: str = "") -> None:
    if etat not in ETATS:
        raise ValueError(etat)
    init(store)
    le = datetime.now().isoformat(timespec="seconds")
    note = (note or "").strip()[:200]
    with store.lock:
        store.db.execute("INSERT INTO alertes_suivi(cid, etat, par, le, note, signature) VALUES(?,?,?,?,?,?) "
                         "ON CONFLICT(cid) DO UPDATE SET etat=excluded.etat, par=excluded.par, le=excluded.le, "
                         "note=excluded.note, signature=excluded.signature",
                         (cid, etat, par, le, note, signature(textes)))
        store.db.execute("INSERT INTO alertes_historique(cid, code, etat, par, le, note, resume) VALUES(?,?,?,?,?,?,?)",
                         (cid, code, etat, par, le, note, " ; ".join(textes)[:300]))
        store.db.commit()


def resolues_depuis(store, jours: int = 7) -> List[dict]:
    init(store)
    depuis = (datetime.now() - timedelta(days=jours)).isoformat(timespec="seconds")
    cols = ("cid", "code", "par", "le", "note", "resume")
    return [dict(zip(cols, r)) for r in store.db.execute(
        "SELECT cid, code, par, le, note, resume FROM alertes_historique WHERE etat='resolue' AND le >= ? "
        "ORDER BY le DESC", (depuis,))]


def appliquer(groupes: List[dict], suivi: Dict[str, dict]) -> None:
    """Ajoute à chaque groupe (un cas en alerte) son état affiché : nouvelle, prise, reapparue, resolue."""
    for g in groupes:
        s = suivi.get(g["cid"])
        g["suivi"] = s
        textes = [it["texte"] for it in g["liste"]]
        if not s or s["etat"] == "nouvelle":
            g["etat"] = "nouvelle"
        elif s["etat"] == "prise":
            g["etat"] = "prise"
        else:                                   # résolue : encore vraie ?
            avant = set((s.get("signature") or "").split("|")) - {""}
            maintenant = {type_alerte(t) for t in textes}
            g["etat"] = "reapparue" if maintenant and maintenant <= avant else "nouvelle"
