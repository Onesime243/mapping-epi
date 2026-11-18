"""Langue des textes produits par l'outil (interface, fiche, visuels, exports) : français ou anglais.

Règle : les textes de l'outil sont écrits en français dans le code et passent par tr("…") ; en anglais, la traduction
est cherchée dans les dictionnaires de config/en/*.py (un fichier par partie de l'outil). Un texte sans traduction
reste en français : rien ne disparaît. Les valeurs saisies (noms, lieux, notes, ID) ne passent jamais par tr() ;
les choix de liste (type d'étape, risque, symptômes…) sont enregistrés en français et seulement affichés traduits.

La langue courante est gardée dans une variable de contexte, posée par le serveur à chaque requête (langue de la
session ou du compte) : les visuels et les fichiers téléchargés sortent donc dans la langue de l'utilisateur.
"""
from __future__ import annotations

import contextvars
import importlib
import pkgutil
from contextlib import contextmanager
from typing import Dict, Optional

LANGUES = {"fr": "Français", "en": "English"}
_LANG: contextvars.ContextVar[str] = contextvars.ContextVar("mapping_epi_langue", default="fr")
_EN: Optional[Dict[str, str]] = None


def dictionnaire() -> Dict[str, str]:
    """Toutes les traductions anglaises (config/en/*.py : chaque module définit un dict EN)."""
    global _EN
    if _EN is None:
        import config.en as paquet
        d: Dict[str, str] = {}
        for m in sorted(pkgutil.iter_modules(paquet.__path__), key=lambda m: m.name):
            d.update(getattr(importlib.import_module(f"config.en.{m.name}"), "EN", {}))
        _EN = d
    return _EN


def actuelle() -> str:
    return _LANG.get()


def definir(lang: Optional[str]) -> None:
    _LANG.set(lang if lang in LANGUES else "fr")


@contextmanager
def utiliser(lang: Optional[str]):
    jeton = _LANG.set(lang if lang in LANGUES else "fr")
    try:
        yield
    finally:
        _LANG.reset(jeton)


def tr(texte: str, lang: Optional[str] = None) -> str:
    """Traduction d'un texte de l'outil (écrit en français) dans la langue courante (ou `lang`)."""
    if not texte or (lang or _LANG.get()) != "en":
        return texte
    return dictionnaire().get(texte, texte)


def trf(texte: str, **valeurs) -> str:
    """Comme tr(), pour un texte à trous : trf("{n} cas reliés", n=4) → « 4 linked cases »."""
    return tr(texte).format(**valeurs)
