"""Langue de l'interface web (français par défaut, anglais).

Les textes sont écrits en français dans les gabarits et passés à t("…") (ou tf("… {n} …", n=…) pour un texte à
trous) ; côté Python, le serveur utilise tr() / trf() de core/langue.py. En anglais, la traduction est cherchée dans
les dictionnaires config/en/*.py (pages et messages : config/en/ui.py) ; un texte sans traduction reste en français
(rien ne disparaît). Toute l'interface passe par ce mécanisme : pages, menus, messages, fiche, visuels et fichiers
produits. La langue est gardée pour le compte (table preferences) et dans la session.
"""
from __future__ import annotations

import re
from typing import Optional

LANGUES = {"fr": "Français", "en": "English"}

from core.langue import dictionnaire as _dico  # noqa: E402

EN = _dico()      # toutes les traductions (config/en/*.py)

_NB = re.compile(r"^(\d+) ")


def t(texte: str, lang: Optional[str]) -> str:
    """Traduction de `texte` (français) dans la langue `lang` ; à défaut, le texte français."""
    if lang != "en" or not texte:
        return texte
    return _dico().get(texte, texte)


# -- préférence du compte ---------------------------------------------------------------------------
def _init(store) -> None:
    store.db.execute("CREATE TABLE IF NOT EXISTS preferences(username TEXT, cle TEXT, valeur TEXT, "
                     "PRIMARY KEY(username, cle))")


def langue_du_compte(store, username: str) -> Optional[str]:
    _init(store)
    r = store.db.execute("SELECT valeur FROM preferences WHERE username=? AND cle='langue'", (username,)).fetchone()
    return r[0] if r and r[0] in LANGUES else None


def enregistrer_langue(store, username: str, lang: str) -> None:
    if lang not in LANGUES:
        return
    _init(store)
    with store.lock:
        store.db.execute("INSERT INTO preferences(username, cle, valeur) VALUES(?, 'langue', ?) "
                         "ON CONFLICT(username, cle) DO UPDATE SET valeur=excluded.valeur", (username, lang))
        store.db.commit()
