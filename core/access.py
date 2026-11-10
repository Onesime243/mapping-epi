"""Droits d'accès aux cas selon le niveau du compte (pyramide sanitaire RDC).

| Niveau          | Voit                                              | Corrige                                   |
|-----------------|---------------------------------------------------|-------------------------------------------|
| Aire de santé   | ses propres cas                                   | ses propres cas                           |
| Zone de santé   | ses cas + tous les cas de sa ZS                   | ses cas + cas des comptes AS / ZS de sa ZS |
| Provincial      | ses cas + tous les cas de sa province             | ses propres cas                           |
| National        | tous les cas                                      | ses propres cas                           |
| Administrateur  | tous les cas                                      | tous les cas                              |

Un cas « appartient » à une ZS / province :
- par sa localisation (champs Province / ZS de la fiche),
- OU par le compte qui l'a créé (un agent d'AS de la ZS Ganga reste rattaché à Ganga).
Les deux critères se cumulent : un cas saisi par une AS de Ganga mais localisé à Bondo est visible
par la ZS de Ganga et par celle de Bondo.
"""
from __future__ import annotations

from typing import Dict, Optional

from core import pyramide
from core.models import Case
from core.users import User


def _same(a: str, b: str) -> bool:
    return bool(a) and bool(b) and pyramide.norm(a) == pyramide.norm(b)


def case_province(c: Case) -> str:
    if c.province:
        return c.province
    return (pyramide.get().province_of(c.zs) or "") if c.zs else ""


class Access:
    def __init__(self, user: User, users: Dict[str, User]):
        self.user = user
        self.users = users

    @property
    def sees_all(self) -> bool:
        return self.user.is_admin or self.user.niveau == "national"

    def _owner(self, owner: str) -> Optional[User]:
        return self.users.get(owner) if owner else None

    def _in_zone(self, c: Case, owner: str) -> bool:
        u = self.user
        if _same(c.zs, u.zs) and (not c.province or _same(c.province, u.province)):
            return True
        o = self._owner(owner)
        return bool(o) and o.niveau in ("aire", "zone") and _same(o.zs, u.zs) and _same(o.province, u.province)

    def _in_province(self, c: Case, owner: str) -> bool:
        if _same(case_province(c), self.user.province):
            return True
        o = self._owner(owner)
        return bool(o) and o.niveau in ("aire", "zone", "province") and _same(o.province, self.user.province)

    def can_view(self, c: Case, owner: str) -> bool:
        if self.sees_all or owner == self.user.username:
            return True
        if self.user.niveau == "province":
            return self._in_province(c, owner)
        if self.user.niveau == "zone":
            return self._in_zone(c, owner)
        return False

    def can_edit(self, c: Case, owner: str) -> bool:
        if self.user.is_admin or owner == self.user.username:
            return True
        if self.user.niveau == "zone" and self._in_zone(c, owner):
            o = self._owner(owner)
            # la ZS corrige les fiches de ses AS (et de ses collègues ZS), pas celles des niveaux supérieurs
            return o is None or o.niveau in ("aire", "zone")
        return False

    def can_delete(self, c: Case, owner: str) -> bool:
        return self.user.is_admin or owner == self.user.username
