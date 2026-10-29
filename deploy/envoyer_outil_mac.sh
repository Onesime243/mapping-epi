#!/bin/bash
# Envoie un outil provincial Ebola (Nord-Kivu, Tshopo…) depuis le Mac vers le serveur Hetzner, puis l’installe.
# Usage (Terminal du Mac) : bash envoyer_outil_mac.sh DOSSIER_OUTIL NOM PORT [SERVEUR]
#   ex. bash envoyer_outil_mac.sh ~/Documents/…/Ebola_NK_Hub nord-kivu 8790 root@37.27.154.249
# Le mot de passe root du serveur est demandé une seule fois (à taper vous-même).
set -e
DOSSIER="${1:?Dossier de l’outil}"; NOM="${2:?Nom (ex. nord-kivu)}"; PORT="${3:?Port (ex. 8790)}"
SERVEUR="${4:-root@37.27.154.249}"
cd "$DOSSIER"
[ -f scripts/serveur.py ] || { echo "Ce dossier ne contient pas d’outil (scripts/serveur.py introuvable)."; exit 1; }
CTL="/tmp/ssh-outil-$$"
SSH=(ssh -o ControlMaster=auto -o ControlPath="$CTL" -o ControlPersist=120 -o StrictHostKeyChecking=accept-new "$SERVEUR")
trap 'ssh -o ControlPath="$CTL" -O exit "$SERVEUR" >/dev/null 2>&1 || true' EXIT

echo "Connexion à $SERVEUR (tapez le mot de passe root du serveur si demandé)…"
DEJA="$("${SSH[@]}" "test -f /srv/outils/$NOM/config/comptes.json && echo oui || echo non")"
PARTIES=(scripts tableau requirements.txt)
if [ "$DEJA" = "non" ]; then
  PARTIES+=(config donnees)
  echo "Première installation : code, comptes et données sont envoyés."
else
  echo
  echo "L’outil « $NOM » existe déjà sur le serveur, avec les fichiers déposés par les zones depuis Internet."
  read -r -p "Remplacer les DONNÉES et COMPTES du serveur par ceux de ce Mac ? (o/N) " R
  if [ "$R" = "o" ] || [ "$R" = "O" ]; then PARTIES+=(config donnees); echo "Code + données envoyés."
  else echo "Seul le code (scripts, pages) est mis à jour ; les données du serveur sont conservées."; fi
fi
TAILLE="$(du -sch "${PARTIES[@]}" 2>/dev/null | tail -1 | cut -f1)"
echo "Envoi de $TAILLE (les rapports seront refaits sur le serveur)…"
COPYFILE_DISABLE=1 tar czf - --exclude='__pycache__' --exclude='.DS_Store' --exclude='._*' --exclude='~$*' "${PARTIES[@]}" \
  | "${SSH[@]}" "mkdir -p /srv/outils/$NOM && tar xzf - -C /srv/outils/$NOM"
echo "Installation sur le serveur…"
"${SSH[@]}" "grep -q installer-outil /usr/local/bin/mapping-epi || mapping-epi mise-a-jour >/dev/null; mapping-epi installer-outil $NOM $PORT"
