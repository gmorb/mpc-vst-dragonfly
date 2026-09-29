#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
# Package the built plugins as the release (run vst/build.sh first), in the Force VST repository's layout:
#   tools/package.sh      -> dist/Dragonfly-Reverb-for-MPC-OS-<VERSION>.zip and dist/SHA256SUMS
#   Dragonfly Reverb for MPC OS/
#     Dragonfly - VST - <Name>/        one self-contained folder per plugin, copied as-is into a Synths folder:
#       <Name>.so                      the plugin
#       plugin-meta.xml                its MPC plugin-list entry; file= is %payload-path%/<this folder>/<Name>.so
#       version.xml                    content id dragonfly.vst.<name>, the release version
#       <Name>.json                    parameter description (tools/param_json.py)
#       Plugin Skins/                  its page (TUI.json, Q-Links, images)
#       LICENSE, NOTICE.md             GPL-3.0 and the component notices
#     README.md, LICENSE, NOTICE.md, licenses/
# vstscanner.sh registers every <Synths>/<folder>/plugin-meta.xml; the folder name is MPC's own
# "<manufacturer> - VST - <plugin name>" page-folder name, so plugin and page live in the same place.
# See docs/DISTRIBUTION.md.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(cat VERSION)
SOURCE="${SOURCE_URL:-}"
[ -z "$SOURCE" ] && [ -n "${GITHUB_REPOSITORY:-}" ] && SOURCE="https://github.com/$GITHUB_REPOSITORY (tag v$VERSION)"
[ -z "$SOURCE" ] && SOURCE="the GitHub repository this release was published from (tag v$VERSION)"
STAGE=dist/stage; OUT="dist/Dragonfly-Reverb-for-MPC-OS-$VERSION.zip"
rm -rf dist; mkdir -p "$STAGE/Dragonfly Reverb for MPC OS"
C="$STAGE/Dragonfly Reverb for MPC OS"
V4=$(python3 -c "v='$VERSION'.split('.'); print('.'.join((v + ['0'] * 4)[:4]))")
for p in hall room plate early; do
  so=$(python3 -c "import json;print(json.load(open('vst/$p/vst.json'))['so'])")
  name=$(python3 -c "import json;print(json.load(open('vst/$p/vst.json'))['name'])")
  vendor=$(python3 -c "import json;print(json.load(open('vst/$p/vst.json'))['vendor'])")
  file="${name// /}.so"                                   # Hall.so ... EarlyRefl.so
  B="vst/$p/build"
  [ -f "$B/$so" ] || { echo "missing $B/$so: run vst/build.sh first" >&2; exit 1; }
  folder="$vendor - VST - $name"
  [ -d "$B/skin/$folder" ] || { echo "missing page folder $B/skin/$folder" >&2; exit 1; }
  D="$C/$folder"
  cp -r "$B/skin/$folder" "$D"                             # Plugin Skins/ (+ the kit's version.xml, rewritten below)
  cp "$B/$so" "$D/$file"
  sed "s|file=\"/sdcard/vst/$so\"|file=\"%payload-path%/$folder/$file\"|" "$B/pluginlist-entry.xml" > "$D/plugin-meta.xml"
  grep -q "%payload-path%/$folder/$file" "$D/plugin-meta.xml" || { echo "plugin-meta.xml for $p: bad file path" >&2; exit 1; }
  id=$(echo "$vendor.vst.$name" | tr 'A-Z' 'a-z' | tr -d ' ')
  printf "<?xml version='1.0' encoding='utf-8'?>\n<plugincontent version=\"1.0\">\n\t<identifier>%s</identifier>\n\t<version>%s</version>\n</plugincontent>\n" "$id" "$V4" > "$D/version.xml"
  python3 tools/param_json.py "$p" "$D/${name// /}.json"
  cp LICENSE NOTICE.md "$D/"
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
Works on Gen 1 Akai MPC and Force. For the Akai Force with MockbaMod (memory card at /media/662522): download
\`$(basename "$OUT")\`, copy the four \`Dragonfly - VST - ...\` folders from \`Dragonfly Reverb for MPC OS\` into the
\`Synths\` folder on the card (next to \`vstscanner.sh\`), then run \`vstscanner\` on the device.
Other custom firmware: see "Other firmware" in the release's README.md. SSH access (modded firmware) required.
NOTES
echo "$OUT ($(du -h "$OUT" | cut -f1)), $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files"
cat dist/SHA256SUMS
