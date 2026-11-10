"""Comptes utilisateurs (stockés dans la base locale).

Mots de passe hachés PBKDF2-SHA256 (240 000 itérations, sel aléatoire) :
aucun mot de passe n'est jamais enregistré en clair.
Rôles : « admin » (gère les comptes, voit et corrige tous les cas) et « agent ».
Niveaux (pyramide sanitaire), voir core/access.py pour les droits :
  national   : voit les cas de toutes les provinces
  province   : voit les cas de sa province
  zone       : voit et corrige les cas de sa zone de santé
  aire       : voit et corrige uniquement ses propres cas
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.storage import Store

ITER = 240_000
ROLES = ("agent", "admin")
NIVEAUX = {"national": "National", "province": "Provincial", "zone": "Zone de santé", "aire": "Aire de santé"}


@dataclass
class User:
    username: str
    nom: str
    role: str
    actif: bool
    zs: str
    cree_le: str
    derniere_connexion: str
    niveau: str = "aire"
    province: str = ""
    aire: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def niveau_label(self) -> str:
        return NIVEAUX.get(self.niveau, self.niveau)

    @property
    def perimetre(self) -> str:
        """Libellé du périmètre géographique, ex. « ZS Ganga (Bas-Uele) »."""
        if self.niveau == "national":
            return "Toute la RDC"
        if self.niveau == "province":
            return f"Province {self.province or '?'}"
        if self.niveau == "zone":
            return f"ZS {self.zs or '?'} ({self.province or '?'})"
        return f"AS {self.aire or '?'} – ZS {self.zs or '?'}"


def hash_password(pwd: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, ITER)
    return f"pbkdf2_sha256${ITER}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def check_password(pwd: str, stored: str) -> bool:
    try:
        algo, it, salt, dk = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), base64.b64decode(salt), int(it))
        return algo == "pbkdf2_sha256" and hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


def validate_password(pwd: str) -> Optional[str]:
    if len(pwd) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        return "Le mot de passe doit contenir au moins une lettre et un chiffre."
    return None


def validate_username(u: str) -> Optional[str]:
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", u):
        return "Identifiant : 3 à 32 caractères, minuscules, chiffres, point, tiret ou souligné."
    return None


class Users:
    def __init__(self, store: Store):
        self.store = store
        self.db = store.db

    def _row(self, r) -> User:
        niveau = r[7] or ("national" if r[2] == "admin" else "aire")
        return User(r[0], r[1] or r[0], r[2], bool(r[3]), r[4] or "", r[5] or "", r[6] or "", niveau, r[8] or "", r[9] or "")

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def list(self) -> List[User]:
        return [self._row(r) for r in self.db.execute(
            "SELECT username, nom, role, actif, zs, cree_le, derniere_connexion, niveau, province, aire FROM users ORDER BY role DESC, username")]

    def get(self, username: str) -> Optional[User]:
        r = self.db.execute("SELECT username, nom, role, actif, zs, cree_le, derniere_connexion, niveau, province, aire FROM users "
                            "WHERE username=?", (username,)).fetchone()
        return self._row(r) if r else None

    def create(self, username: str, password: str, nom: str = "", role: str = "agent", zs: str = "",
               niveau: str = "", province: str = "", aire: str = "") -> User:
        username = username.strip().lower()
        for err in (validate_username(username), validate_password(password)):
            if err:
                raise ValueError(err)
        if role not in ROLES:
            raise ValueError("Rôle inconnu.")
        if self.get(username):
            raise ValueError("Cet identifiant existe déjà.")
        niveau, province, zs, aire = normalize_scope(role, niveau, province, zs, aire)
        with self.store.lock:
            self.db.execute("INSERT INTO users(username, nom, pwd, role, actif, zs, cree_le, niveau, province, aire) "
                            "VALUES(?,?,?,?,1,?,?,?,?,?)",
                            (username, nom.strip(), hash_password(password), role, zs,
                             datetime.now().isoformat(timespec="seconds"), niveau, province, aire))
            self.db.commit()
        return self.get(username)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        username = (username or "").strip().lower()
        r = self.db.execute("SELECT pwd, actif FROM users WHERE username=?", (username,)).fetchone()
        if not r:
            check_password(password, hash_password("x"))     # temps constant
            return None
        if not r[1] or not check_password(password, r[0]):
            return None
        with self.store.lock:
            self.db.execute("UPDATE users SET derniere_connexion=? WHERE username=?",
                            (datetime.now().isoformat(timespec="seconds"), username))
            self.db.commit()
        return self.get(username)

    def set_password(self, username: str, password: str) -> None:
        err = validate_password(password)
        if err:
            raise ValueError(err)
        with self.store.lock:
            self.db.execute("UPDATE users SET pwd=? WHERE username=?", (hash_password(password), username))
            self.db.commit()

    def update(self, username: str, nom: Optional[str] = None, role: Optional[str] = None,
               actif: Optional[bool] = None, zs: Optional[str] = None) -> None:
        u = self.get(username)
        if not u:
            raise ValueError("Utilisateur introuvable.")
        if u.is_admin and (role == "agent" or actif is False) and self.admin_count() <= 1:
            raise ValueError("Impossible : il doit rester au moins un administrateur actif.")
        with self.store.lock:
            self.db.execute("UPDATE users SET nom=COALESCE(?,nom), role=COALESCE(?,role), "
                            "actif=COALESCE(?,actif), zs=COALESCE(?,zs) WHERE username=?",
                            (nom, role, None if actif is None else int(actif), zs, username))
            if role == "admin":
                self.db.execute("UPDATE users SET niveau='national' WHERE username=?", (username,))
            self.db.commit()

    def set_scope(self, username: str, niveau: str, province: str = "", zs: str = "", aire: str = "") -> None:
        """Change le niveau et le périmètre géographique d'un compte."""
        u = self.get(username)
        if not u:
            raise ValueError("Utilisateur introuvable.")
        niveau, province, zs, aire = normalize_scope(u.role, niveau, province, zs, aire)
        with self.store.lock:
            self.db.execute("UPDATE users SET niveau=?, province=?, zs=?, aire=? WHERE username=?",
                            (niveau, province, zs, aire, username))
            self.db.commit()

    def admin_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND actif=1").fetchone()[0]


def normalize_scope(role: str, niveau: str, province: str, zs: str, aire: str) -> tuple:
    """Vérifie et met à l'orthographe de référence le périmètre d'un compte.

    Un administrateur est toujours de niveau national. Sans niveau précisé, un agent
    est de niveau « aire » (il ne voit que ses propres cas), comme avant la v1.2.
    """
    from core import pyramide
    province, zs, aire = (province or "").strip(), (zs or "").strip(), (aire or "").strip()
    if role == "admin":
        niveau = "national"
    niveau = niveau or "aire"
    if niveau not in NIVEAUX:
        raise ValueError("Niveau inconnu.")
    pyr = pyramide.get()
    if zs and not province:
        province = pyr.province_of(zs) or ""
    province, zs, aire = pyr.canonical(province, zs, aire)
    if niveau == "national":
        return niveau, "", "", ""
    if niveau == "aire":
        # un compte d'aire ne voit que ses propres cas : son AS sert à pré-remplir les nouvelles fiches
        return niveau, province, zs, aire
    if not province:
        raise ValueError("Choisissez la province du compte.")
    if niveau == "province":
        return niveau, province, "", ""
    if not zs:
        raise ValueError("Choisissez la zone de santé du compte.")
    return niveau, province, zs, ""


def generate_password() -> str:
    """Mot de passe lisible (sans caractères ambigus) pour un nouveau compte."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    while True:
        p = "".join(secrets.choice(alphabet) for _ in range(10))
        if not validate_password(p):
            return p
