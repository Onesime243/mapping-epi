"""Modèles de données (pydantic v2).

Principe : une valeur inconnue reste explicitement inconnue.
- un nombre de contacts inconnu est `None` (affiché « ? »), différent de 0 ;
- une date inconnue est `None` (affichée « ? »).
"""
from __future__ import annotations

import datetime as _dt
import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _id() -> str:
    return uuid.uuid4().hex[:10]



NOTE_PIED_DEFAUT = "TASK FORCE PRÉSIDENTIELLE EBOLA 17 - Système de Gestion de l'Incident MVE 17"
_ANCIENNE_NOTE = "À mettre à jour à chaque nouvelle information d'investigation."

class Event(BaseModel):
    id: str = Field(default_factory=_id)
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    heure: str = ""                 # ex. "23h", "04h", "15–17h"
    heure_approx: bool = False      # affiche "~23h"
    date_incertaine: bool = False
    lieu: str = ""
    lieu_arrivee: str = ""          # pour un déplacement « A → B »
    type: str = "Autre"
    titre: str = ""
    description: str = ""
    transport: str = ""
    personnes: str = ""             # personnes présentes / accompagnants
    contact_corps: bool = False     # contact avec le corps / toilette mortuaire
    liquides: bool = False          # liquides biologiques (saignements, vomissements…)
    sans_pci: bool = False          # soins ou contact sans mesures PCI
    securise: bool = False          # enterrement digne et sécurisé / transport sécurisé
    risque: str = ""                # vide = risque suggéré automatiquement


class Place(BaseModel):
    id: str = Field(default_factory=_id)
    nom: str = ""
    type: str = "Autre"
    population: str = ""            # population exposée
    nombre: Optional[int] = None
    risque: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None


class ContactGroup(BaseModel):
    id: str = Field(default_factory=_id)
    categorie: str = ""
    lien: str = ""
    nombre: Optional[int] = None    # None = « ? »
    suivis: Optional[int] = None
    risque: str = "Haut"
    lieu: str = ""
    dernier_contact: Optional[date] = None
    libelle_nombre: str = ""        # suffixe affiché, ex. « listés »


class IPCSite(BaseModel):
    id: str = Field(default_factory=_id)
    site: str = ""
    statut: str = "Non"
    date: Optional[_dt.date] = None
    equipe: str = ""
    produit: str = ""


class LabSample(BaseModel):
    id: str = Field(default_factory=_id)
    type: str = "Swab"
    laboratoire: str = ""
    prelevement: Optional[datetime] = None
    envoi: Optional[datetime] = None
    reception: Optional[datetime] = None
    resultat_le: Optional[datetime] = None
    resultat: str = ""              # Positif / Négatif / En attente


class Action(BaseModel):
    id: str = Field(default_factory=_id)
    texte: str = ""
    priorite: str = "Important"
    responsable: str = ""
    echeance: Optional[date] = None
    statut: str = "À faire"
    auto: bool = False              # issue d'une suggestion automatique


class Case(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    code_cas: str = ""                      # identifiant alphanumérique (ex. N° EPID : RDC-HUE-WAM-26-001)
    rang: Optional[int] = None
    maladie: str = "MVE"
    sexe: str = "Inconnu"
    age: Optional[int] = None
    age_unite: str = "ans"
    profession: str = ""
    province: str = ""
    zs: str = ""
    aire_sante: str = ""
    village: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    statut: str = "Confirmé"
    date_confirmation: Optional[date] = None
    issue: str = "Inconnu"
    investigateur: str = ""
    date_investigation: Optional[date] = None

    debut_symptomes: Optional[date] = None   # date RAPPORTÉE par l'équipe (J0), jamais recalculée
    debut_phase_humide: Optional[date] = None   # vide = détectée dans la chronologie ou estimée (J0 + 4)
    contact_connu: str = "Inconnu"           # Contact connu / Contact connu suivi / Non contact / Inconnu
    symptomes: List[str] = Field(default_factory=list)
    symptomes_autres: str = ""
    date_deces: Optional[date] = None

    risque_global: str = ""         # vide = calculé automatiquement

    events: List[Event] = Field(default_factory=list)

    @field_validator("note_pied")
    @classmethod
    def _note_pied(cls, v):
        # Les cas déjà enregistrés avec l'ancien texte standard reçoivent le nouveau.
        v = (v or "").strip()
        return NOTE_PIED_DEFAUT if (not v or v.startswith(_ANCIENNE_NOTE)) else v

    @field_validator("symptomes")
    @classmethod
    def _symptomes(cls, v):
        from config.theme import SYMPTOM_ALIASES
        out: List[str] = []
        for s in v or []:
            s = SYMPTOM_ALIASES.get(str(s).strip(), str(s).strip())
            if s and s not in out:
                out.append(s)
        return out

    places: List[Place] = Field(default_factory=list)
    contacts: List[ContactGroup] = Field(default_factory=list)
    ipc: List[IPCSite] = Field(default_factory=list)
    labs: List[LabSample] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    suggestions_rejetees: List[str] = Field(default_factory=list)

    note_pied: str = NOTE_PIED_DEFAUT
    modifie_le: Optional[datetime] = None
    modifie_par: str = ""

    # ------------------------------------------------------------------
    def titre_court(self) -> str:
        rang = self.code_cas.strip() or (f"Cas {self.rang}" if self.rang else "Cas")
        return f"{rang} – {self.maladie} – ZS {self.zs or '?'} ({self.aire_sante or '?'})"

    def sorted_events(self) -> List[Event]:
        def key(e: Event):
            return (e.date_debut or date.max, _hour_key(e.heure), e.date_fin or e.date_debut or date.max)
        return sorted(self.events, key=key)


def _hour_key(h: str) -> int:
    digits = ""
    for ch in h or "":
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    try:
        return int(digits[:2])
    except ValueError:
        return -1
