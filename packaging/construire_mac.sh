#!/bin/bash
# Construit l'application Mac et son installateur .dmg (sans connexion à l'usage).
#   bash packaging/construire_mac.sh            (depuis le dossier du projet, environnement Python actif)
# Résultat : dist/MappingEpi-<version>-Mac-<arm64|x86_64>.dmg
set -e
cd "$(dirname "$0")/.."
VERSION="$(cat packaging/VERSION)"
ARCH="$(uname -m)"
PY="${PYTHON:-python}"
[ -x .venv/bin/python ] && [ -z "$PYTHON" ] && PY=.venv/bin/python
"$PY" -m PyInstaller packaging/mapping_epi.spec --noconfirm --distpath dist --workpath build
DMG="dist/MappingEpi-$VERSION-Mac-$ARCH.dmg"
STAGE="$(mktemp -d)"
cp -R "dist/Mapping Epi.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/LISEZMOI-installation.txt "$STAGE/LISEZMOI.txt"
cp LICENSE "$STAGE/LICENCE (AGPL-3.0).txt"
rm -f "$DMG"
hdiutil create -volname "Mapping Épi $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"
echo "Installateur Mac : $DMG"
