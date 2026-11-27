"""Rapports journaliers des points d'entrée et de contrôle (PoE / PoC) : seule donnée saisie hors des fiches.
Fichier JSON dans le dossier de données (jamais de nom de voyageur : des nombres seulement)."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import date
from typing import List, Optional

from core.paths import data_dir

_VERROU = threading.Lock()
CHAMPS_N = ("voyageurs", "screenes", "alertes", "investiguees")


def _fichier():
    return data_dir() / "poe_poc.json"


def charger() -> List[dict]:
    f = _fichier()
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []


def _ecrire(rows: List[dict]) -> None:
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _n(v) -> Optional[int]:
    v = str(v if v is not None else "").strip().replace(" ", "")
    if not v:
        return None                       # vide = inconnu, jamais 0
    n = int(v)
    if n < 0:
        raise ValueError("nombre négatif")
    return n


def ajouter(form: dict, auteur: str) -> dict:
    d = date.fromisoformat(str(form.get("date", "")).strip())
    point = str(form.get("point", "")).strip()[:80]
    if not point:
        raise ValueError("point manquant")
    r = {"id": uuid.uuid4().hex[:10], "date": d.isoformat(), "point": point,
         "zs": str(form.get("zs", "")).strip()[:60], "auteur": auteur}
    for k in CHAMPS_N:
        r[k] = _n(form.get(k))
    if r["voyageurs"] is not None and r["screenes"] is not None and r["screenes"] > r["voyageurs"]:
        raise ValueError("plus de screenés que de voyageurs")
    if r["alertes"] is not None and r["investiguees"] is not None and r["investiguees"] > r["alertes"]:
        raise ValueError("plus d'alertes investiguées que d'alertes")
    with _VERROU:
        rows = charger()
        rows.append(r)
        _ecrire(rows)
    return r


def supprimer(rid: str) -> bool:
    with _VERROU:
        rows = charger()
        rest = [r for r in rows if r.get("id") != rid]
        if len(rest) == len(rows):
            return False
        _ecrire(rest)
    return True
