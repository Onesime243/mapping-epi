"""Administration en ligne de commande (serveur ou poste local).

    python manage.py creer-admin            créer un compte administrateur (questions interactives)
    python manage.py creer-utilisateur      créer un compte agent
    python manage.py utilisateurs           lister les comptes
    python manage.py mot-de-passe IDENT     définir un nouveau mot de passe
    python manage.py desactiver IDENT       désactiver un compte
    python manage.py activer IDENT          réactiver un compte
    python manage.py sauvegarde DOSSIER     copie cohérente de la base + fiches JSON (archive .tar.gz)
"""
from __future__ import annotations

import getpass
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.paths import data_dir, db_path  # noqa: E402
from core.storage import Store  # noqa: E402
from core.users import Users, generate_password  # noqa: E402


def _ask_password() -> str:
    while True:
        p1 = getpass.getpass("Mot de passe (vide = en générer un) : ")
        if not p1:
            p = generate_password()
            print(f"Mot de passe généré : {p}")
            return p
        if p1 == getpass.getpass("Confirmer : "):
            return p1
        print("Les deux saisies diffèrent, recommencez.")


def create(role: str) -> int:
    us = Users(Store())
    username = input("Identifiant (ex. admin, agent.tumba) : ").strip().lower()
    nom = input("Nom complet : ").strip()
    zs = input("Zone de santé (facultatif) : ").strip() if role == "agent" else ""
    try:
        u = us.create(username, _ask_password(), nom, role, zs)
    except ValueError as exc:
        print(f"Erreur : {exc}")
        return 1
    print(f"Compte « {u.username} » ({u.role}) créé.")
    return 0


def backup(dest: str) -> int:
    dest_dir = Path(dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / "mapping_epi.sqlite"
        src = sqlite3.connect(str(db_path()))
        dst = sqlite3.connect(str(snap))
        src.backup(dst)                     # copie cohérente même pendant l'utilisation
        src.close()
        dst.close()
        out = dest_dir / f"mapping_epi_{stamp}.tar.gz"
        with tarfile.open(out, "w:gz") as tar:
            tar.add(snap, arcname="mapping_epi.sqlite")
            for name in ("cas", "pyramide_perso.csv"):
                p = data_dir() / name
                if p.exists():
                    tar.add(p, arcname=name)
    out.chmod(0o600)
    print(out)
    return 0


def main(argv) -> int:
    if not argv or argv[0] in ("-h", "--help", "aide"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "creer-admin":
        return create("admin")
    if cmd == "creer-utilisateur":
        return create("agent")
    if cmd == "sauvegarde":
        return backup(args[0] if args else str(data_dir().parent / "sauvegardes"))
    us = Users(Store())
    if cmd == "utilisateurs":
        for u in us.list():
            print(f"{u.username:24} {u.role:6} {'actif' if u.actif else 'désactivé':10} {u.nom}  "
                  f"(dernière connexion : {u.derniere_connexion or '—'})")
        return 0
    if cmd in ("mot-de-passe", "desactiver", "activer") and args:
        try:
            if cmd == "mot-de-passe":
                us.set_password(args[0], _ask_password())
            else:
                us.update(args[0], actif=(cmd == "activer"))
        except ValueError as exc:
            print(f"Erreur : {exc}")
            return 1
        print("Fait.")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
