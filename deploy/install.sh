#!/usr/bin/env bash
# =============================================================================
#  Mapping Épi — installation sur un serveur Ubuntu 24.04 (Hetzner Cloud CX23)
#
#  Une seule commande, en root, sur le serveur tout neuf :
#    curl -fsSL https://raw.githubusercontent.com/Onesime243/mapping-epi/main/deploy/install.sh | bash
#
#  Options (variables d'environnement, facultatives) :
#    DOMAINE=mapping.mondomaine.org   nom de domaine déjà pointé vers le serveur
#                                     (sinon : adresse gratuite <ip>.sslip.io)
#    EMAIL=moi@exemple.org            e-mail pour le certificat HTTPS (Let's Encrypt)
#    DEPOT=https://github.com/Onesime243/mapping-epi.git
#    BRANCHE=main
#
#  Ce que fait le script (il peut être relancé sans risque) :
#    1. mises à jour de sécurité automatiques, pare-feu (SSH + HTTP/HTTPS), fail2ban, swap 2 Go
#    2. utilisateur système « mappingepi », code dans /opt/mapping-epi
#    3. données dans /var/lib/mapping-epi (jamais dans le dépôt)
#    4. service systemd (redémarre seul), HTTPS automatique avec Caddy
#    5. sauvegarde quotidienne (14 jours conservés) dans /var/backups/mapping-epi
#    6. commande « mapping-epi » pour administrer (comptes, sauvegarde, mise à jour)
# =============================================================================
set -euo pipefail

DEPOT="${DEPOT:-https://github.com/Onesime243/mapping-epi.git}"
BRANCHE="${BRANCHE:-main}"
APP_DIR=/opt/mapping-epi
DATA_DIR=/var/lib/mapping-epi
BACKUP_DIR=/var/backups/mapping-epi
SVC_USER=mappingepi
PORT=8050

vert()  { printf '\033[1;32m%s\033[0m\n' "$*"; }
jaune() { printf '\033[1;33m%s\033[0m\n' "$*"; }
rouge() { printf '\033[1;31m%s\033[0m\n' "$*" >&2; }

[ "$(id -u)" -eq 0 ] || { rouge "Lancez ce script en root (ou avec sudo)."; exit 1; }
. /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then jaune "Système testé : Ubuntu 24.04. Système détecté : ${PRETTY_NAME:-inconnu}."; fi

export DEBIAN_FRONTEND=noninteractive

vert "[1/8] Mises à jour du système et paquets…"
apt-get update -q
apt-get -y -q upgrade
apt-get install -y -q --no-install-recommends \
  git curl ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https \
  python3 python3-venv python3-pip sqlite3 ufw fail2ban unattended-upgrades fontconfig fonts-dejavu-core
# Bibliothèques du moteur de rendu (Qt WebEngine) : installées une à une pour qu'un nom absent ne bloque rien
LIBS_QT="libnss3 libnspr4 libdbus-1-3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libgbm1
  libxkbcommon0 libxkbcommon-x11-0 libxcomposite1 libxdamage1 libxrandr2 libxfixes3 libxext6 libxrender1
  libxtst6 libxi6 libxshmfence1 libxkbfile1 libasound2t64 libegl1 libgl1 libopengl0 libglib2.0-0t64
  libx11-xcb1 libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0
  libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxcb-glx0 libfontconfig1 libfreetype6"
# shellcheck disable=SC2086
if ! apt-get install -y -q --no-install-recommends $LIBS_QT >/dev/null 2>&1; then
  for p in $LIBS_QT; do
    apt-get install -y -q --no-install-recommends "$p" >/dev/null 2>&1 \
      || apt-get install -y -q --no-install-recommends "${p%t64}" >/dev/null 2>&1 \
      || jaune "  (paquet $p indisponible, ignoré)"
  done
fi
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

vert "[2/8] Pare-feu, protection SSH et mémoire d'appoint…"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
systemctl enable --now fail2ban >/dev/null 2>&1 || true
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

vert "[3/8] Utilisateur système et dossiers…"
id "$SVC_USER" >/dev/null 2>&1 || useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin "$SVC_USER"
install -d -m 750 -o "$SVC_USER" -g "$SVC_USER" "$DATA_DIR" "$DATA_DIR/cas" "$DATA_DIR/exports"
install -d -m 700 -o root -g root "$BACKUP_DIR"

vert "[4/8] Récupération du code ($DEPOT, branche $BRANCHE)…"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch -q origin "$BRANCHE"
  git -C "$APP_DIR" reset -q --hard "origin/$BRANCHE"
else
  rm -rf "$APP_DIR"
  git clone -q --depth 1 --branch "$BRANCHE" "$DEPOT" "$APP_DIR"
fi
install -d -o "$SVC_USER" -g "$SVC_USER" "$APP_DIR/logs"

vert "[5/8] Environnement Python (quelques minutes la première fois)…"
[ -d "$APP_DIR/.venv" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/deploy/requirements-serveur.txt"
chown -R root:root "$APP_DIR"
chown -R "$SVC_USER:$SVC_USER" "$APP_DIR/logs"

vert "[6/8] Service systemd…"
install -m 644 "$APP_DIR/deploy/mapping-epi.service" /etc/systemd/system/mapping-epi.service
install -m 755 "$APP_DIR/deploy/mapping-epi" /usr/local/bin/mapping-epi
install -m 644 "$APP_DIR/deploy/mapping-epi-sauvegarde.cron" /etc/cron.d/mapping-epi-sauvegarde
systemctl daemon-reload
systemctl enable --now mapping-epi >/dev/null
systemctl restart mapping-epi

vert "[7/8] HTTPS avec Caddy…"
if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q && apt-get install -y -q caddy
fi
IP4="$(curl -4fsS https://api.ipify.org || hostname -I | awk '{print $1}')"
if [ -z "${DOMAINE:-}" ]; then
  if [ -f /etc/mapping-epi/domaine ]; then DOMAINE="$(cat /etc/mapping-epi/domaine)"; else DOMAINE="mapping-epi.${IP4//./-}.sslip.io"; fi
fi
install -d -m 755 /etc/mapping-epi
echo "$DOMAINE" > /etc/mapping-epi/domaine
{
  if [ -n "${EMAIL:-}" ]; then printf '{\n\temail %s\n}\n\n' "$EMAIL"; fi
  sed -e "s|__DOMAINE__|${DOMAINE}|g" -e "s|__PORT__|${PORT}|g" "$APP_DIR/deploy/Caddyfile.modele"
} > /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile >/dev/null
[ -d /var/log/caddy ] && chown -R caddy:caddy /var/log/caddy
systemctl enable caddy >/dev/null 2>&1 || true
systemctl restart caddy
sleep 2
if ! systemctl is-active --quiet caddy; then
  rouge "Caddy (HTTPS) n'a pas démarré. Détails : journalctl -u caddy -n 30"
  exit 1
fi

vert "[8/8] Vérification…"
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/sante" >/dev/null 2>&1; then break; fi
  sleep 1
done
if curl -fsS "http://127.0.0.1:${PORT}/sante" >/dev/null 2>&1; then
  vert "Application démarrée."
else
  rouge "L'application ne répond pas. Voir : journalctl -u mapping-epi -n 50"
  exit 1
fi

NB_COMPTES="$(sudo -u "$SVC_USER" MAPPING_EPI_DONNEES="$DATA_DIR" "$APP_DIR/.venv/bin/python" -c \
  'import sys; sys.path.insert(0,"/opt/mapping-epi"); from core.storage import Store; from core.users import Users; print(Users(Store()).count())' 2>/dev/null || echo 0)"

echo
vert "=================================================================="
vert "  Mapping Épi est en ligne :  https://${DOMAINE}"
vert "=================================================================="
echo "  (le certificat HTTPS peut prendre une minute à être délivré)"
echo
if [ "${NB_COMPTES}" = "0" ]; then
  jaune "  Étape suivante : créez votre compte administrateur :"
  echo  "      mapping-epi creer-admin"
  echo
fi
echo "  Commandes utiles :"
echo "      mapping-epi creer-admin | creer-utilisateur | utilisateurs"
echo "      mapping-epi sauvegarde      (copie immédiate)"
echo "      mapping-epi mise-a-jour     (dernière version depuis GitHub)"
echo "      mapping-epi etat | journal"
