#!/usr/bin/env python3
"""df_skin.py -- the Dragonfly look for the MPC pages (mpc-vst-dragonfly).

One page spec per plugin (PAGES below) drives both halves, so artwork and controls always line up:
  df_skin.py layout <p>   writes vst/<p>/layout.conf for mpc-vst-plugins' gen_vst.py (geometry, Q-Links, TUI.json)
  df_skin.py paint <p>    after gen_vst.py: repaints every image of vst/<p>/build/skin/... in the original
                          plugin's style (upstream artwork: logo/title, knob and fader look, colours, NotoSans)
                          and restyles MPC's live text (bigger, white) in TUI.json.
Why a post-pass: the kit only takes custom images with its headless-Chromium renderer; this keeps the kit's
proven components and geometry and swaps pixels and text styles only (the layout is still the kit's).
The page is 1280x628 (page coords here; layout.conf is shadow coords = page y + 86).
"""
import json
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "src", "dragonfly", "artwork")
W, H, Y_OFF = 1280, 628, 86

# Text sizes (px). Live text is MPC's Titillium Web; baked text is upstream's NotoSans.
NAME_PX, VALUE_PX, FIELD_PX = 30.0, 28.0, 34.0   # JUCE font heights (ascent+descent): capitals ~13, 12, 15 px
NAME_H, VALUE_H = 36, 36
LIST_PX, POPOPT_PX, HEAD_PX = 21, 19, 22

BG = (61, 61, 61)
PANEL = (80, 80, 80)
WHITE = (230, 230, 230)
DIM = (160, 160, 160)
BLACK = (0, 0, 0)

KNOB_R = 38          # layout radius -> the kit's filmstrip frame is 2r+10 square
FADER_W = 40         # track width inside the square fader frame


# --------------------------------------------------------------------------------------------------------------
# Page specs. Rows of panels; each panel holds cells (knobs/faders) or one special control.
#   ("cells", [keys...], kind)  kind "knob" or "fader"
#   ("popup", key, bank_titles) ("list", key, rows, sw, title)
# --------------------------------------------------------------------------------------------------------------
PAGES = {
    "hall": {
        "upstream": "dragonfly-hall-reverb", "logo_box": (0, 0, 310, 112),
        "header_h": 150, "header": [("popup", "preset", ["Rooms", "Studios", "Small Halls", "Medium Halls", "Large Halls"])],
        "rows": [
            [("cells", ["dry_level", "early_level", "early_send", "late_level"], "fader"),
             ("cells", ["size", "width"], "knob"), ("cells", ["delay", "decay"], "knob")],
            [("cells", ["diffuse", "modulation", "spin", "wander"], "knob"),
             ("cells", ["high_cut", "high_xo", "high_mult"], "knob"),
             ("cells", ["low_cut", "low_xo", "low_mult"], "knob")],
        ],
        "fader_s": 118,
        "qlinks": [("MAIN", "dry_level,early_level,early_send,late_level,size,width,delay,decay,"
                            "diffuse,modulation,spin,wander,high_cut,high_xo,high_mult,low_cut"),
                   ("EQ", "high_cut,high_xo,high_mult,low_cut,low_xo,low_mult,preset")],
    },
    "room": {
        "upstream": "dragonfly-room-reverb", "logo_box": (0, 0, 340, 112),
        "header_h": 150, "header": [("popup", "preset", ["Small", "Medium", "Large", "Halls", "Effects"])],
        "rows": [
            [("cells", ["dry_level", "early_level", "early_send", "late_level"], "fader"),
             ("cells", ["size", "width"], "knob"), ("cells", ["predelay", "decay"], "knob")],
            [("cells", ["diffuse", "spin", "wander"], "knob"),
             ("cells", ["in_high_cut", "early_damp", "late_damp"], "knob"),
             ("cells", ["in_low_cut", "low_boost", "boost_freq"], "knob")],
        ],
        "fader_s": 118,
        "qlinks": [("MAIN", "dry_level,early_level,early_send,late_level,size,width,predelay,decay,"
                            "diffuse,spin,wander,in_high_cut,early_damp,late_damp,in_low_cut,low_boost"),
                   ("TONE", "in_high_cut,early_damp,late_damp,in_low_cut,low_boost,boost_freq,preset")],
    },
    "plate": {
        "upstream": "dragonfly-plate-reverb", "logo_box": (0, 0, 322, 118),
        "header_h": 196, "header": [("list", "preset", 4, 214, "Presets"), ("list", "algorithm", 3, 180, "Reverb Type")],
        "rows": [
            [("cells", ["dry_level", "early_level"], "fader"), ("cells", ["width", "predelay", "decay"], "knob")],
            [None, ("cells", ["low_cut", "high_cut", "early_damp"], "knob")],
        ],
        "fader_s": 196,
        "qlinks": [("PLATE", "dry_level,early_level,width,predelay,decay,low_cut,high_cut,early_damp,preset,algorithm")],
    },
    "early": {
        "upstream": "dragonfly-early-reflections", "logo_box": (0, 0, 448, 117),
        "header_h": 150, "header": [],
        "rows": [
            [("cells", ["dry_level", "early_level"], "fader"), ("list", "program", 8, 300, "Reflection Type"),
             ("cells", ["size", "width"], "knob")],
            [None, None, ("cells", ["low_cut", "high_cut"], "knob")],
        ],
        "fader_s": 196,
        "qlinks": [("EARLY", "dry_level,early_level,size,width,low_cut,high_cut,program")],
    },
}

# Names as the original UI prints them (MPC shows the param name from the plugin elsewhere).
LABELS = {
    "dry_level": "Dry Level", "early_level": "Early Level", "early_send": "Early Send", "late_level": "Late Level",
    "size": "Size", "width": "Width", "delay": "Predelay", "predelay": "Predelay", "decay": "Decay",
    "diffuse": "Diffuse", "modulation": "Modulation", "spin": "Spin", "wander": "Wander",
    "high_cut": "High Cut", "high_xo": "High Cross", "high_mult": "High Mult",
    "low_cut": "Low Cut", "low_xo": "Low Cross", "low_mult": "Low Mult",
    "in_high_cut": "High Cut", "in_low_cut": "Low Cut", "early_damp": "Early Damp", "late_damp": "Late Damp",
    "low_boost": "Low Boost", "boost_freq": "Boost Freq",
}
PLUGIN_LABELS = {"plate": {"early_level": "Wet Level", "early_damp": "Dampen"},
                 "early": {"early_level": "Wet Level"}}

GAP, PAD, MARGIN = 10, 12, 8
LIST_ROW, LIST_GAP = 33, 2     # the kit's option segment height and gap
LIST_TITLE_H = 40


def label_for(p, key):
    return PLUGIN_LABELS.get(p, {}).get(key, LABELS.get(key, key))


def geometry(p):
    """Every panel and control in page coords. Returns dict(panels=[...], controls=[...])."""
    spec = PAGES[p]
    panels, controls = [], []
    hh = spec["header_h"]
    fs = spec["fader_s"]
    knob_s = 2 * KNOB_R + 10

    def cell_h(kind):
        return NAME_H + (fs if kind == "fader" else knob_s) + VALUE_H

    # header: logo/title at the left, special controls in panels to the right
    lb = spec["logo_box"]
    scale = (hh - 8) / float(lb[3] - lb[1])
    logo_w = int((lb[2] - lb[0]) * scale)
    x = MARGIN + logo_w + GAP
    items = spec["header"]
    if items:
        avail = W - MARGIN - x
        widths = []
        for it in items:
            if it[0] == "list":
                cols = -(-len_options(p, it[1]) // it[2])
                widths.append(cols * it[3] + (cols - 1) * 2 + 2 * PAD)
            else:
                widths.append(None)
        fixed = sum(w for w in widths if w) + GAP * (len(items) - 1)
        flex = [i for i, w in enumerate(widths) if w is None]
        for i in flex:
            widths[i] = (avail - fixed) // len(flex)
        if not flex:   # right-align fixed-width lists
            x = W - MARGIN - fixed
        for it, pw in zip(items, widths):
            panels.append({"x": x, "y": MARGIN, "w": pw, "h": hh - MARGIN, "title": it[-1] if it[0] == "list" else "Preset"})
            if it[0] == "popup":
                fw = 244   # = option width; the field itself is widened in paint
                controls.append({"kind": "popup", "key": it[1], "cx": x + pw // 2, "cy": MARGIN + (hh - MARGIN) // 2 + 14,
                                 "w": fw, "h": 58, "banks": it[2], "field_w": pw - 2 * PAD - 150})
            else:
                n = len_options(p, it[1])
                rows = it[2]
                lh = rows * (LIST_ROW + LIST_GAP) - LIST_GAP
                top = MARGIN + LIST_TITLE_H + ((hh - MARGIN - LIST_TITLE_H) - lh) // 2
                controls.append({"kind": "list", "key": it[1], "cx": x + pw // 2, "cy": top + LIST_ROW // 2,
                                 "rows": rows, "sw": it[3], "n": n})
            x += pw + GAP

    # body rows. A row is laid out on its own (fixed-width fader/list panels, knob panels share the rest by
    # cell count) unless the page has a None panel (= the panel above spans down): then every row uses the
    # first row's columns.
    rows = spec["rows"]
    body_top = hh + GAP
    row_h = (H - MARGIN - body_top - GAP * (len(rows) - 1)) // len(rows)

    def row_widths(row):
        ws = []
        for it in row:
            if it is None or it[0] == "cells" and it[2] == "knob":
                ws.append(None)
            elif it[0] == "cells":
                ws.append(len(it[1]) * max(fs, 112) + 2 * PAD)
            else:
                ws.append(it[3] + 2 * PAD + 20)
        total = W - 2 * MARGIN - GAP * (len(row) - 1)
        fixed = sum(w_ for w_ in ws if w_)
        flex = [i for i, w_ in enumerate(ws) if w_ is None]
        n = [max(1, len(row[i][1])) if row[i] else 1 for i in flex]
        for i, k in zip(flex, n):
            ws[i] = int((total - fixed) * k / float(sum(n)))
        xs = [MARGIN]
        for w_ in ws[:-1]:
            xs.append(xs[-1] + w_ + GAP)
        ws[-1] = W - MARGIN - xs[-1]
        return xs, ws

    columns = any(it is None for row in rows for it in row)
    if columns:
        xs0, ws0 = row_widths(rows[0])
    for ri, row in enumerate(rows):
        y = body_top + ri * (row_h + GAP)
        xs, ws = (xs0, ws0) if columns else row_widths(row)
        for ci, it in enumerate(row):
            if it is None:
                continue
            span = 1
            while columns and ri + span < len(rows) and rows[ri + span][ci] is None:
                span += 1
            place_panel(p, panels, controls, it, xs[ci], y, ws[ci], row_h * span + GAP * (span - 1), cell_h, fs, knob_s)
    return {"panels": panels, "controls": controls, "logo": (MARGIN, 4, logo_w, hh - 8)}


def place_panel(p, panels, controls, it, x, y, pw, ph, cell_h, fs, knob_s):
    if it[0] == "list":
        panels.append({"x": x, "y": y, "w": pw, "h": ph, "title": it[4]})
        n = len_options(p, it[1])
        rows = it[2]
        lh = rows * (LIST_ROW + LIST_GAP) - LIST_GAP
        top = y + LIST_TITLE_H + ((ph - LIST_TITLE_H) - lh) // 2
        controls.append({"kind": "list", "key": it[1], "cx": x + pw // 2, "cy": top + LIST_ROW // 2, "rows": rows,
                         "sw": it[3], "n": n})
        return
    keys, kind = it[1], it[2]
    panels.append({"x": x, "y": y, "w": pw, "h": ph, "title": ""})
    cw = (pw - 2 * PAD) // len(keys)
    ch = cell_h(kind)
    s = fs if kind == "fader" else knob_s
    top = y + (ph - ch) // 2
    for i, k in enumerate(keys):
        cx = x + PAD + cw * i + cw // 2
        controls.append({"kind": kind, "key": k, "cx": cx, "cy": top + NAME_H + s // 2, "cw": min(cw, max(s, 150)),
                         "s": s, "label": label_for(p, k)})


_opts_cache = {}


def len_options(p, key):
    return len(options(p, key))


def options(p, key):
    if p not in _opts_cache:
        _opts_cache[p] = {q["key"]: q for q in json.load(open(os.path.join(HERE, p, "params.json")))["params"]}
    return _opts_cache[p][key].get("options", [])


# --------------------------------------------------------------------------------------------------------------
# phase 1: layout.conf
# --------------------------------------------------------------------------------------------------------------
def colours(p):
    """Knob/fill colour, border colour, title colour: sampled from the upstream artwork."""
    up = PAGES[p]["upstream"]
    knob = Image.open(os.path.join(ART, up, "knob.png")).convert("RGBA")
    kc = knob.getpixel((knob.width // 2, knob.height // 2))[:3]
    bg = Image.open(os.path.join(ART, up, "background.png")).convert("RGB")
    lb = PAGES[p]["logo_box"]
    count = {}
    for yy in range(lb[3] + 4, bg.height):          # panel borders: saturated-ish, not grey, below the header
        for xx in range(0, bg.width, 2):
            c = bg.getpixel((xx, yy))
            if max(c) - min(c) > 25 and max(c) > 120:
                count[c] = count.get(c, 0) + 1
    border = max(count, key=count.get)
    count = {}
    title_box = (lb[2] * 0.3, 0, lb[2], lb[3])
    for yy in range(int(title_box[1]), int(title_box[3])):
        for xx in range(int(title_box[0]), int(title_box[2])):
            c = bg.getpixel((xx, yy))
            if max(c) - min(c) > 30 and max(c) > 140:
                count[c] = count.get(c, 0) + 1
    title = max(count, key=count.get)
    return kc, border, title


def hexs(c):
    return "%02x%02x%02x" % tuple(c)


def write_layout(p):
    g = geometry(p)
    kc, border, title = colours(p)
    L = ["# Dragonfly %s -- MPC page. GENERATED by vst/df_skin.py from its PAGES spec: edit that, not this file." % p,
         "# Images are repainted by `df_skin.py paint` after gen_vst.py (see its header).",
         "theme_bg=%s" % hexs(BG), "theme_panel=%s" % hexs(PANEL), "theme_line=%s" % hexs(border),
         "theme_ink=%s" % hexs(WHITE), "theme_ink_dim=%s" % hexs(DIM), "theme_ink_faint=6e6e6e",
         "theme_accent=%s" % hexs(title), "theme_accent_hi=%s" % hexs(title), "theme_knob_face=%s" % hexs(kc),
         "theme_knob_ring=%s" % hexs(WHITE), "theme_knob_dot=%s" % hexs(WHITE), "theme_bar=%s" % hexs(PANEL),
         "theme_seg_active=%s" % hexs(PANEL), "theme_seg_inactive=%s" % hexs(PANEL),
         "theme_seg_active_tx=ffffff", "theme_btn_text=ffffff", "theme_tab_on=%s" % hexs(border),
         "theme_tab_on_tx=ffffff", "theme_lcd=%s" % hexs(PANEL), "theme_box=%s" % hexs(PANEL)]
    track = []
    for name, keys in PAGES[p]["qlinks"]:
        for k in keys.split(","):
            if k not in track:
                track.append(k)
    L += ["qlinks_track = " + ",".join(track[:16]), "", "[tab %s]" % p.upper()]
    for c in g["controls"]:
        y = c["cy"] + Y_OFF
        if c["kind"] == "knob":
            L.append('knob cx=%d cy=%d r=%d label="%s" key=%s' % (c["cx"], y, KNOB_R, c["label"], c["key"]))
        elif c["kind"] == "fader":
            L.append('slider_v cx=%d cy=%d w=%d h=%d label="%s" key=%s' % (c["cx"], y, FADER_W, c["s"], c["label"], c["key"]))
        elif c["kind"] == "popup":
            L.append('popup cx=%d cy=%d w=%d h=%d label="" key=%s cols=%d' % (c["cx"], y, c["w"], c["h"], c["key"], len(c["banks"])))
        elif c["kind"] == "list":
            L.append('enum_h cx=%d cy=%d label="" key=%s sw=%d rows=%d' % (c["cx"], y, c["key"], c["sw"], c["rows"]))
    for name, keys in PAGES[p]["qlinks"]:
        L.append('qlinks "%s" = %s' % (name, keys))
    open(os.path.join(HERE, p, "layout.conf"), "w").write("\n".join(L) + "\n")
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
