"""Champs obligatoires avant l'enregistrement d'une fiche (config/champs_obligatoires.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from core.models import Case

ROOT = Path(__file__).resolve().parent.parent
_CHAMPS: Optional[List[Tuple[str, str]]] = None
VIDES = (None, "", "Inconnu", "Inconnue", "?")


def champs() -> List[Tuple[str, str]]:
    global _CHAMPS
    if _CHAMPS is None:
        with open(ROOT / "config" / "champs_obligatoires.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _CHAMPS = [(c["cle"], c.get("libelle") or c["cle"]) for c in data.get("champs", []) if hasattr(Case, c["cle"])
                   or c["cle"] in Case.model_fields]
    return _CHAMPS


def manquants(c: Case) -> List[str]:
    out = []
    for cle, lib in champs():
        v = getattr(c, cle, None)
        if isinstance(v, str):
            v = v.strip()
        if v in VIDES:
            out.append(lib)
    return out


def complet(c: Case) -> bool:
    return not manquants(c)


def message(m: List[str]) -> str:
    return ("Enregistrement impossible : champ(s) obligatoire(s) manquant(s) : " + ", ".join(m) +
            ". La saisie est gardée en brouillon.")
