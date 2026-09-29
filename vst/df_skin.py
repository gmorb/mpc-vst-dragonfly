#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
"""df_skin.py -- the MPC pages, laid out after the original Dragonfly UIs (mpc-vst-dragonfly).

One design per plugin (DESIGNS below), taken from upstream's UI.cpp positions (vendored as UI.cpp.ref) scaled to
MPC's 1280x628 plugin page. The live spectrogram can't exist on MPC, so its column goes to the other panels.
  df_skin.py layout <p>   writes vst/<p>/layout.conf for mpc-vst-plugins' gen_vst.py (controls, Q-Links, TUI.json)
  df_skin.py paint <p>    after gen_vst.py: df_paint.py repaints every image in the original's style and lays
                          out the knob/fader/list components as the original draws them (see df_paint.py)
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "src", "dragonfly", "artwork")
W, H, Y_OFF = 1280, 628, 86

# Live text (MPC's Titillium Web; JUCE heights = ascent+descent): values under each control.
VALUE_PX, VALUE_H = 28.0, 36
# Baked text (the original's NotoSans, px = em size): control names, list items, panel titles.
NAME_PX, NAME_H = 20, 36
LIST_PX, TITLE_PX = 21, 22
KNOB_R = 42                 # the kit's knob frame is 2r+10 = 94 px; the knob itself is drawn 84 px across
KNOB_CW = 104               # knob cell width (the original's 75 px knob spacing, scaled)
# Faders: per design "fader": (r, segments) -> segments of 2r+10 px squares stacked into the original's tall
# slider (4 thin ones side by side on Hall/Room; 2 wider ones on Plate/Early, as the originals).
LIST_ROW = 35               # the kit's option row (33 px) + gap

BG = (61, 61, 61)
PANEL = (80, 80, 80)
WHITE = (230, 230, 230)
DIM = (150, 150, 150)
BLACK = (0, 0, 0)

# Page designs (page coords). panels: (x0, y0, x1, y1, title). "spectrogram": the panel index that shows the
# original's spectrogram, rendered per preset at build time (df_paint.py). Controls are placed in their panel:
#   ("knobs", panel, [keys])      evenly across the panel, as the original spaces them
#   ("faders", panel, [keys])     the original's level sliders
#   ("list", key, x, y, w, rows, cols, visible_by_bank)   an option list (the original's Selection widget)
BANKS = {
    "hall": {
        "upstream": "dragonfly-hall-reverb", "logo": ((0, 0, 310, 112), (8, 10, 431, 190)),
        "panels": [(487, 9, 821, 200, ""), (835, 9, 1272, 200, ""), (8, 218, 243, 619, ""),
                   (257, 218, 473, 410, ""), (257, 428, 473, 619, ""), (939, 218, 1272, 410, ""),
                   (939, 428, 1272, 619, ""), (487, 218, 925, 619, "")],
        "controls": [("list", "bank", 438, 20, 150, 5, 1, False), ("list", "preset", 594, 20, 224, 5, 1, True),
                     ("knobs", 1, ["diffuse", "modulation", "spin", "wander"]),
                     ("faders", 2, ["dry_level", "early_level", "early_send", "late_level"]),
                     ("knobs", 3, ["size", "width"]), ("knobs", 4, ["delay", "decay"]),
                     ("knobs", 5, ["high_cut", "high_xo", "high_mult"]), ("knobs", 6, ["low_cut", "low_xo", "low_mult"])],
        "fader": (17, 6), "spectrogram": 7,
        "qlinks": [("MAIN", "dry_level,early_level,early_send,late_level,size,width,delay,decay,"
                            "diffuse,modulation,spin,wander,preset"),
                   ("EQ", "high_cut,high_xo,high_mult,low_cut,low_xo,low_mult,preset")],
    },
    "room": {
        "upstream": "dragonfly-room-reverb", "logo": ((0, 0, 340, 112), (8, 10, 470, 190)),
        "panels": [(487, 9, 922, 200, ""), (939, 9, 1272, 200, ""), (8, 218, 243, 619, ""),
                   (257, 218, 473, 410, ""), (257, 428, 473, 619, ""), (939, 218, 1272, 410, ""),
                   (939, 428, 1272, 619, ""), (487, 218, 925, 619, "")],
        "controls": [("list", "bank", 487, 20, 139, 5, 1, False), ("list", "preset", 640, 20, 276, 5, 1, True),
                     ("knobs", 1, ["diffuse", "spin", "wander"]),
                     ("faders", 2, ["dry_level", "early_level", "early_send", "late_level"]),
                     ("knobs", 3, ["size", "width"]), ("knobs", 4, ["predelay", "decay"]),
                     ("knobs", 5, ["in_high_cut", "early_damp", "late_damp"]),
                     ("knobs", 6, ["in_low_cut", "low_boost", "boost_freq"])],
        "fader": (17, 6), "spectrogram": 7,
        "qlinks": [("MAIN", "dry_level,early_level,early_send,late_level,size,width,predelay,decay,"
                            "diffuse,spin,wander,preset"),
                   ("TONE", "in_high_cut,early_damp,late_damp,in_low_cut,low_boost,boost_freq,preset")],
    },
    "plate": {
        "upstream": "dragonfly-plate-reverb", "logo": ((0, 0, 322, 118), (8, 8, 600, 196)),
        "panels": [(626, 9, 1043, 200, "Presets"), (1062, 9, 1272, 200, "Reverb Type"), (9, 218, 180, 619, ""),
                   (815, 218, 1272, 410, ""), (815, 428, 1272, 619, ""), (199, 218, 796, 619, "")],
        "controls": [("list", "preset", 645, 47, 195, 4, 2, False), ("list", "algorithm", 1082, 64, 180, 3, 1, False),
                     ("faders", 2, ["dry_level", "early_level"]),
                     ("knobs", 3, ["width", "predelay", "decay"]), ("knobs", 4, ["low_cut", "high_cut", "early_damp"])],
        "fader": (27, 4), "spectrogram": 5,
        "qlinks": [("PLATE", "dry_level,early_level,width,predelay,decay,low_cut,high_cut,early_damp,preset,algorithm")],
    },
    "early": {
        "upstream": "dragonfly-early-reflections", "logo": ((0, 0, 448, 117), (8, 8, 740, 198)),
        "panels": [(14, 218, 270, 619, ""), (298, 218, 767, 619, "<Reflection Type"), (796, 218, 1266, 410, ""),
                   (796, 428, 1266, 619, "")],
        "controls": [("faders", 0, ["dry_level", "early_level"]), ("list", "program", 318, 262, 355, 8, 1, False),
                     ("knobs", 2, ["size", "width"]), ("knobs", 3, ["low_cut", "high_cut"])],
        "fader": (27, 4),
        "qlinks": [("EARLY", "dry_level,early_level,size,width,low_cut,high_cut,program")],
    },
}
DESIGNS = BANKS


def params(p):
    return {q["key"]: q for q in json.load(open(os.path.join(HERE, p, "params.json")))["params"]}


def options(p, key):
    return params(p)[key].get("options", [])


def geometry(p):
    """Every panel and control in page coords."""
    d = DESIGNS[p]
    prm = params(p)
    panels = [{"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "title": t} for x0, y0, x1, y1, t in d["panels"]]
    controls = []
    knob_s = 2 * KNOB_R + 10
    fader_r, segs = d["fader"]
    fader_s = 2 * fader_r + 10
    for c in d["controls"]:
        if c[0] == "list":
            _, key, x, y, w, rows, cols, by_bank = c
            controls.append({"kind": "list", "key": key, "x": x, "y": y, "w": w, "rows": rows, "cols": cols,
                             "by_bank": by_bank, "n": len(prm[key]["options"])})
            continue
        kind, pi, keys = c
        q = panels[pi]
        for i, k in enumerate(keys):
            cx = q["x"] + q["w"] * (i + 0.5) / len(keys)
            if kind == "knobs":
                ch = NAME_H + knob_s + VALUE_H
                top = q["y"] + (q["h"] - ch) / 2.0
                controls.append({"kind": "knob", "key": k, "cx": int(cx), "cy": int(top + NAME_H + knob_s / 2),
                                 "top": int(top), "cw": KNOB_CW, "s": knob_s, "name": prm[k]["name"]})
            else:
                track = segs * fader_s
                ch = 2 * 26 + 8 + track + VALUE_H + 4
                top = q["y"] + (q["h"] - ch) / 2.0
                controls.append({"kind": "fader", "key": k, "cx": int(cx), "top": int(top),
                                 "track_y": int(top + 2 * 26 + 8), "s": fader_s, "cw": min(max(56, fader_s + 20), int(q["w"] / len(keys)) - 2),
                                 "segs": segs, "r": fader_r,
                                 "name": prm[k]["name"]})
    return {"panels": panels, "controls": controls, "logo": d["logo"]}


def colours(p):
    """Knob/fill colour, border colour, title colour: sampled from the upstream artwork."""
    up = DESIGNS[p]["upstream"]
    knob = Image.open(os.path.join(ART, up, "knob.png")).convert("RGBA")
    kc = knob.getpixel((knob.width // 2, knob.height // 2))[:3]
    bg = Image.open(os.path.join(ART, up, "background.png")).convert("RGB")
    lb = DESIGNS[p]["logo"][0]
    count = {}
    for yy in range(lb[3] + 4, bg.height):
        for xx in range(0, bg.width, 2):
            c = bg.getpixel((xx, yy))
            if max(c) - min(c) > 25 and max(c) > 120:
                count[c] = count.get(c, 0) + 1
    border = max(count, key=count.get)
    count = {}
    for yy in range(lb[1], lb[3]):
        for xx in range(int(lb[2] * 0.3), lb[2]):
            c = bg.getpixel((xx, yy))
            if max(c) - min(c) > 30 and max(c) > 140:
                count[c] = count.get(c, 0) + 1
    title = max(count, key=count.get)
    return kc, border, title


def hexs(c):
    return "%02x%02x%02x" % tuple(c)


def write_layout(p):
    """The kit builds the components (and Q-Links) from this; df_paint.py then places and paints them."""
    g = geometry(p)
    kc, border, title = colours(p)
    L = ["# Dragonfly %s -- MPC page. GENERATED by vst/df_skin.py from its DESIGNS: edit that, not this file." % p,
         "# Positions here only seed the kit; df_paint.py places every component as the original UI draws it.",
         "theme_bg=%s" % hexs(BG), "theme_panel=%s" % hexs(PANEL), "theme_line=%s" % hexs(border),
         "theme_ink=%s" % hexs(WHITE), "theme_ink_dim=%s" % hexs(DIM), "theme_ink_faint=6e6e6e",
         "theme_accent=%s" % hexs(title), "theme_accent_hi=%s" % hexs(title), "theme_knob_face=%s" % hexs(kc),
         "theme_knob_ring=%s" % hexs(WHITE), "theme_knob_dot=%s" % hexs(WHITE), "theme_bar=%s" % hexs(PANEL),
         "theme_seg_active=%s" % hexs(PANEL), "theme_seg_inactive=%s" % hexs(PANEL),
         "theme_seg_active_tx=ffffff", "theme_btn_text=ffffff", "theme_tab_on=%s" % hexs(border),
         "theme_tab_on_tx=ffffff", "theme_lcd=%s" % hexs(PANEL), "theme_box=%s" % hexs(PANEL)]
    track = []
    for name, keys in DESIGNS[p]["qlinks"]:
        for k in keys.split(","):
            if k not in track:
                track.append(k)
    L += ["qlinks_track = " + ",".join(track[:16]), "", "[tab %s]" % p.upper()]
    for c in g["controls"]:
        if c["kind"] == "knob":
            L.append('knob cx=%d cy=%d r=%d label="%s" key=%s' % (c["cx"], c["cy"] + Y_OFF, KNOB_R, c["name"], c["key"]))
        elif c["kind"] == "fader":
            L.append('knob cx=%d cy=%d r=%d label="%s" key=%s' % (c["cx"], c["track_y"] + Y_OFF + 100, c["r"],
                                                                    c["name"], c["key"]))
        else:
            L.append('enum_h cx=%d cy=%d label="" key=%s sw=%d rows=%d' % (
                c["x"] + c["w"] // 2, c["y"] + 16 + Y_OFF, c["key"], c["w"], c["rows"]))
    for name, keys in DESIGNS[p]["qlinks"]:
        L.append('qlinks "%s" = %s' % (name, keys))
    open(os.path.join(HERE, p, "layout.conf"), "w").write("\n".join(L) + "\n")
    os.makedirs(os.path.join(HERE, p, "build"), exist_ok=True)
    json.dump(g, open(os.path.join(HERE, p, "build", "geometry.json"), "w"), indent=1)
    return g


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("layout", "paint"):
        sys.exit("usage: df_skin.py layout|paint <hall|room|plate|early>")
    os.makedirs(os.path.join(HERE, sys.argv[2], "build"), exist_ok=True)
    if sys.argv[1] == "layout":
        write_layout(sys.argv[2])
    else:
        import df_paint
        df_paint.paint(sys.argv[2], geometry(sys.argv[2]), colours(sys.argv[2]))
