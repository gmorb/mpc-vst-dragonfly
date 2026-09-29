#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
"""param_json.py <plugin> <out.json> -- the plugin's parameter description, in the Force VST repository's
<Name>.json format (as its DISTRHO and AirWindows plugins ship): every VST parameter by index, with its name, range,
unit, type, option names and display format. Built from vst/<p>/params.json (upstream's DistrhoPluginInfo.h) and
vst/<p>/build/formats.h (upstream's UI.cpp formats); names of the upstream enum come from DistrhoPluginInfo.h."""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p, out = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(ROOT, "vst", p, "vst.json")))
params = json.load(open(os.path.join(ROOT, "vst", p, "params.json")))["params"]
fh = open(os.path.join(ROOT, "vst", p, "build", "formats.h")).read()
formats = [None if m == "NULL" else m.strip('"') for m in re.findall(r'^\s*("(?:[^"\\]|\\.)*"|NULL),', fh, re.M)]
info = open(os.path.join(ROOT, "src", "dragonfly", "plugins", cfg["upstream"], "DistrhoPluginInfo.h")).read()
enum = re.search(r"enum\s+Parameters\s*\{(.*?)\}", info, re.S).group(1)
labels = [n.strip().split("=")[0].strip() for n in re.sub(r"//[^\n]*", "", enum).split(",") if n.strip()]
labels = [n for n in labels if n != "paramCount"]
UNITS = {"%": "pct", "Hz": "Hz", "ms": "ms", "s": "s", "m": "m", "X": "x"}

doc = {"name": cfg["name"], "numParams": len(params), "parameters": {}}
for i, q in enumerate(params):
    opts = q.get("options")
    dsp = i < len(labels)
    e = {"index": i, "caseLabel": labels[i] if dsp else q["key"], "name": q["name"],
         "label": None if opts else (q.get("unit") or None), "variable": q["key"], "transform": "value"}
    if opts:
        e.update({"range": [0, len(opts) - 1], "displayExpr": None, "displayRange": None, "type": "steps",
                  "displayValues": opts, "unit": "enum",
                  "display": {"format": "list", "note": "%d options" % len(opts)}})
    else:
        fmt = formats[i] if dsp and i < len(formats) else None
        e.update({"range": [q["min"], q["max"]], "displayExpr": None, "displayRange": [q["min"], q["max"]],
                  "type": "slider" if fmt == "%i%%" else "knob", "displayValues": None,
                  "unit": UNITS.get(q.get("unit", ""), q.get("unit") or None),
                  "display": {"format": fmt, "note": "printf format of the original Dragonfly UI"}})
    e["default"] = q.get("default")
    if q["key"] == "preset":
        e["display"]["note"] = "picking one loads all its settings"
    if q["key"] == "bank":
        e["display"]["note"] = "picking a bank loads the preset last picked in it (as the original UI)"
    e.update({"confidence": 1.0,
              "evidence": ["Dragonfly Reverb %s: DistrhoPluginInfo.h%s" % (cfg["upstream"], ", UI.cpp" if dsp else "")
                           if dsp else "mpc-vst-dragonfly wrapper: %s" % q["key"]],
              "override_safe": True})
    doc["parameters"][str(i)] = e
json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False)
