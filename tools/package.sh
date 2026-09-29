#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
# Package the built plugins as the release collection (run vst/build.sh first).
#   tools/package.sh      -> dist/Dragonfly-Reverb-for-MPC-OS-<VERSION>.zip and dist/SHA256SUMS
# Layout, for vstscanner.sh (Force VST distribution): per plugin a dragonfly.vst.<Name>/ folder with the .so and a
# plugin-meta.xml whose file= path uses %payload-path%, plus its page folder "Dragonfly - VST - <name>/".
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(cat VERSION)
SOURCE="${SOURCE_URL:-}"
[ -z "$SOURCE" ] && [ -n "${GITHUB_REPOSITORY:-}" ] && SOURCE="https://github.com/$GITHUB_REPOSITORY (tag v$VERSION)"
[ -z "$SOURCE" ] && SOURCE="the GitHub repository this release was published from (tag v$VERSION)"
STAGE=dist/stage; OUT="dist/Dragonfly-Reverb-for-MPC-OS-$VERSION.zip"
rm -rf dist; mkdir -p "$STAGE/Dragonfly Reverb for MPC OS"
C="$STAGE/Dragonfly Reverb for MPC OS"
declare -A FOLDER=([hall]=Hall [room]=Room [plate]=Plate [early]=EarlyReflections)
for p in hall room plate early; do
  so=$(python3 -c "import json;print(json.load(open('vst/$p/vst.json'))['so'])")
  B="vst/$p/build"
  [ -f "$B/$so" ] || { echo "missing $B/$so: run vst/build.sh first" >&2; exit 1; }
  D="$C/dragonfly.vst.${FOLDER[$p]}"; mkdir -p "$D"
  cp "$B/$so" "$D/"
  sed "s|file=\"/sdcard/vst/$so\"|file=\"%payload-path%/dragonfly.vst.${FOLDER[$p]}/$so\"|" "$B/pluginlist-entry.xml" > "$D/plugin-meta.xml"
  grep -q '%payload-path%' "$D/plugin-meta.xml" || { echo "plugin-meta.xml for $p has no %payload-path%" >&2; exit 1; }
  skin=$(find "$B/skin" -mindepth 1 -maxdepth 1 -type d -name 'Dragonfly - VST - *')
  cp -r "$skin" "$C/"
done
cp LICENSE NOTICE.md "$C/"
mkdir -p "$C/licenses"
cp LICENSE "$C/licenses/GPL-3.0.txt"
cp src/dragonfly/common/freeverb/COPYING "$C/licenses/freeverb3-GPL-2.0.txt"
cp src/dragonfly/common/freeverb/AUTHORS "$C/licenses/freeverb3-AUTHORS.txt"
sed -e "s|@VERSION@|$VERSION|" -e "s|@SOURCE@|$SOURCE|" packaging/README.md > "$C/README.md"
find "$STAGE" -exec touch -d "2026-01-01 00:00:00" {} +      # stable zip bytes for the same inputs
(cd "$STAGE" && find "Dragonfly Reverb for MPC OS" -type f | LC_ALL=C sort | zip -q -X -@ "../$(basename "$OUT")")
rm -rf "$STAGE"
(cd dist && sha256sum "$(basename "$OUT")" > SHA256SUMS)
# release notes: this version's CHANGELOG.md section, then install notes
awk -v v="$VERSION" '/^## /{on = ($2 == v)} on && !/^## /' CHANGELOG.md > dist/RELEASE_NOTES.md
[ -s dist/RELEASE_NOTES.md ] || { echo "CHANGELOG.md has no '## $VERSION' section" >&2; exit 1; }
cat >> dist/RELEASE_NOTES.md <<NOTES

### Install
Works on Gen 1 Akai MPC and Force. For the Akai Force with MockbaMod (memory card at /media/662522): download \`$(basename "$OUT")\`, copy the eight folders from \`Dragonfly Reverb for MPC OS\` into the \`Synths\` folder on your
SD card (next to \`vstscanner.sh\`), then run \`sh /media/662522/Synths/vstscanner.sh\` on the device.
Other custom firmware, or no 662522 card: see "Other firmware" in the collection's README.md (the scanner then takes the plugin folder and the MPC.settings path as arguments). Gen 1 Force / MPC with SSH access (modded firmware) required.
NOTES
echo "$OUT ($(du -h "$OUT" | cut -f1)), $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files"
cat dist/SHA256SUMS
