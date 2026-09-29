#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
"""catalog_entries.py --repo OWNER/NAME --author "NAME" [-o DIR]

Writes the four MPC OS Plugin Catalog registry entries (catalog/plugins/<id>.json in sd88me/mpc-vst-plugins),
one per plugin, each picking its own zip from this repo's releases with asset_pattern. Add them to the catalog
with one pull request (see docs/CATALOG.md). The ids must match tools/package.sh's --id values; never change them."""
import argparse
import json
import os

PLUGINS = [
    ("dragonfly-hall", "Dragonfly Hall", "Hall-*-mpc-armv7.zip", ["hall", "modulation", "presets"],
     "Lush hall reverb with early reflections, modulation and 25 presets in 5 banks; the original Dragonfly UI "
     "with its spectrogram."),
    ("dragonfly-room", "Dragonfly Room", "Room-*-mpc-armv7.zip", ["room", "presets"],
     "Small-to-medium room reverb with low boost and damping, 25 presets in 5 banks; the original Dragonfly UI "
     "with its spectrogram."),
    ("dragonfly-plate", "Dragonfly Plate", "Plate-*-mpc-armv7.zip", ["plate", "presets"],
     "Plate reverb with three algorithms (Simple, Nested, Tank) and 8 presets; the original Dragonfly UI with "
     "its spectrogram."),
    ("dragonfly-early-reflections", "Dragonfly Early Reflections", "Early-Refl-*-mpc-armv7.zip", ["early-reflections", "room"],
     "Early reflections only, 8 reflection types from Abrupt Echo to Home Studio; the original Dragonfly UI."),
]

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True, help="this repo on GitHub, owner/name (the releases' source_repo)")
ap.add_argument("--author", required=True, help="how the catalog should name you, the porter")
ap.add_argument("-o", "--out", default="catalog-entries")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
for pid, name, pattern, tags, summary in PLUGINS:
    e = {"id": pid, "name": name,
         "author": "%s (port); Dragonfly Reverb by Michael Willis and Rob van den Berg" % a.author,
         "repo": a.repo, "kind": "effect", "license": "GPL-3.0-or-later",
         "summary": summary, "style": "reverb", "tags": ["dragonfly"] + tags,
         "homepage": "https://github.com/%s" % a.repo, "asset_pattern": pattern}
    path = os.path.join(a.out, pid + ".json")
    json.dump(e, open(path, "w"), indent=2)
    print(path)
