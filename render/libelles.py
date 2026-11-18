"""Affichage des visuels dans la langue de l'utilisateur (voir core/langue.py et config/en/visuels.py).

Les textes de l'outil passent par tr() / trf(). Ce module ajoute ce qui ne se traduit pas mot à mot :
- jour("J+4") : repères de jours (J0, J±n) ; en anglais D0, D±n ;
- val(x) : choix de liste enregistrés en français (type d'étape, risque, statut…) ; « ? » et vide restent tels quels ;
- regle(texte) : phrases produites par core/rules.py (raisons, actions suggérées, synthèse des contacts) ;
- cas(c) : étiquette courte d'un cas (« Cas 3 » devient « Case 3 ») ; un ID saisi n'est jamais traduit.
Rien n'est traduit en français : chaque fonction renvoie son entrée telle quelle.
"""
from __future__ import annotations

import re
from typing import Optional

from core.langue import actuelle, tr, trf

__all__ = ["tr", "trf", "en", "jour", "val", "regle", "cas", "cas_long", "titre_zone"]


def en() -> bool:
    return actuelle() == "en"


_JOUR = re.compile(r"(?<![A-Za-zÀ-ÿ])J(?=[0-9+\-−~±])")


def jour(texte: str) -> str:
    """« J0 », « J+4 », « J-21 → J-2 », « J0 ~12/08 » : J devient D en anglais (« D0 », « D+4 »)."""
    if not texte or not en():
        return texte
    return _JOUR.sub("D", texte)


def val(x: Optional[str]) -> str:
    """Valeur de liste enregistrée en français, affichée traduite (« ? » et vide inchangés)."""
    if not x or x == "?":
        return x or ""
    return tr(x)


# phrases à trous produites par core/rules.py : (motif, gabarit anglais) ; les morceaux saisis restent intacts
_MOTIFS = [
    (r"Étape la plus à risque : (?P<a>.+)", "Highest-risk step: {a}"),
    (r"phase (?P<p>humide|critique) atteinte et contacts non \(entièrement\) listés",
     "{p} phase reached and contacts not (fully) listed"),
    (r"Minimum documenté : (?P<n>\d+) contacts à haut risque(?P<d>.*?)\.(?P<r>.*)",
     "Documented minimum: {n} high-risk contacts{d}.{r}"),
    (r"Identifier (?P<a>.+)", "Identify {a}"),
    (r"Suivi quotidien (?P<n>\d+) jours des contacts", "Daily follow-up of contacts for {n} days"),
    (r"PCI / décontamination : (?P<a>.+)", "IPC / decontamination: {a}"),
    (r"Documenter date / équipe / produit : (?P<a>.+)", "Document date / team / product: {a}"),
    (r"Analyser le délai laboratoire \((?P<n>\d+) h\)", "Analyse the laboratory delay ({n} h)"),
    (r"Vacciner / suivre le personnel soignant : (?P<a>.+)", "Vaccinate / follow up health workers: {a}"),
    (r"Durée de suivi pour (?P<a>.+)", "Follow-up duration for {a}"),
]
_MOTIFS = [(re.compile(m + r"\Z", re.S), g) for m, g in _MOTIFS]
_PHASE_EN = {"humide": "Wet", "critique": "Critical"}


def _un(texte: str) -> str:
    t = texte.strip()
    if not t:
        return texte
    d = tr(t)
    if d != t:
        return d
    for m, g in _MOTIFS:
        r = m.match(t)
        if r:
            parts = {k: (v or "") for k, v in r.groupdict().items()}
            if "p" in parts:
                parts["p"] = _PHASE_EN.get(parts["p"], parts["p"])
            if "a" in parts and g.startswith("Identify"):
                parts["a"] = " / ".join(val(x.strip()) for x in parts["a"].split(" / "))
            if "a" in parts and g.startswith("Highest"):
                parts["a"] = val(parts["a"])
            if "r" in parts:
                parts["r"] = (" " + regle(parts["r"].strip())) if parts["r"].strip() else ""
            return g.format(**parts)
    return texte


def regle(texte: Optional[str]) -> str:
    """Phrase produite par les règles (raisons séparées par « ; », actions suggérées) dans la langue courante."""
    if not texte or not en():
        return texte or ""
    morceaux = texte.split(" ; ")
    out = " ; ".join(_un(m) for m in morceaux)
    if out == texte and ". " in texte:            # deux phrases à la suite (synthèse des contacts)
        out = " ".join(_un(p if p.endswith(".") else p) for p in re.split(r"(?<=\.) ", texte))
    return jour(out).replace(" ; ", "; ")


def cas(c) -> str:
    """Étiquette courte d'un cas (ID saisi, sinon « Cas <rang> » / « Cas <AS> <J0> »)."""
    from core.lieux import case_label
    lab = case_label(c)
    if en() and not (c.code_cas or "").strip() and lab.startswith("Cas "):
        lab = "Case " + lab[4:]
    return lab


def cas_long(c) -> str:
    return f"{cas(c)} · {tr('ZS')} {c.zs or '?'}"


def titre_zone(titre: str) -> str:
    """Titre fixe suivi d'un lieu saisi (« LIEUX LES PLUS FRÉQUENTÉS | Bunia ») : seule la partie fixe est traduite."""
    if not titre or not en():
        return titre
    tete, sep, reste = titre.partition(" | ")
    return tr(tete) + sep + reste
