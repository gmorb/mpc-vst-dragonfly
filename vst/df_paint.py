# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
"""df_paint.py -- phase 2 of df_skin.py: turn the kit-built skin into the original Dragonfly UI (mpc-vst-dragonfly).

The kit (mpc-vst-plugins' gen_vst.py) builds every component from layout.conf: a knob component per knob and per
level fader, one button per option of each list, all bound to their parameters, plus the Q-Link maps. This pass
keeps those components (their actions and bindings are the kit's, proven on MPC) and changes only where they sit,
their fonts and their pictures, to match upstream's UI (UI.cpp.ref, artwork/):
  - knobs: upstream's knob redrawn at MPC size, 300 degrees of travel (ImageKnob::setRotationAngle(300)), min/max
    dots, the name above in NotoSans (baked), the value below (live, MPC's font; the original UI's printf format)
  - level faders: upstream's tall thin sliders -- a light-bordered black track filled from the bottom. MPC
    filmstrip frames are square and images can't pass 16384 px, so a fader is FADER_SEGS small square segments
    stacked, each a knob component on the same parameter showing its slice of the fill; the kit's component is
    the bottom segment and carries the value label and the Q-Link focus for the whole fader
  - lists (the original's Selection widget): names in NotoSans, the current one white, the others grey; Hall and
    Room's banks use upstream's tab images, and their preset column shows the current bank's five presets
    (MPC's IndexedEnabling on the bank parameter), as the original does
  - page art: panels, logo + title (cropped from upstream's background.png), panel titles, fader tracks
Each Q-Link bank (sub-page) keeps its region set to its own controls.
"""
import copy
import json
import numpy as np
import math
import os

from PIL import Image, ImageDraw, ImageFont

import df_skin as S

SS = 4                 # supersampling for everything drawn
S_FRAMES = 128
MAX_IMAGE_H = 16384    # MPC draws taller images wrongly (seen on a Force: 25088 px strips showed half-frames)
KNOB_TRAVEL = 300.0    # degrees, as upstream's LabelledKnob


def font(px):
    return ImageFont.truetype(os.path.join(S.ART, "NotoSans-Regular.ttf"), int(round(px)))


def argb(c, a=255):
    return "%02x%02x%02x%02x" % (a, c[0], c[1], c[2])


def strip_frames(size):
    return min(S_FRAMES, MAX_IMAGE_H // size)


# ------------------------------------------------------------------------------------------------ pictures
def knob_frame(size, t, face):
    n = size * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2.0
    r = S.KNOB_R * SS
    d.ellipse((c - r, c - r, c + r, c + r), fill=S.WHITE + (255,))
    ri = r - 3.4 * SS
    d.ellipse((c - ri, c - ri, c + ri, c + ri), fill=tuple(face) + (255,))
    a = math.radians(-KNOB_TRAVEL / 2 + KNOB_TRAVEL * t)
    sx, sy = math.sin(a), -math.cos(a)
    r0, r1, wdt = ri * 0.52, ri * 0.97, 3.6 * SS
    d.line((c + sx * r0, c + sy * r0, c + sx * r1, c + sy * r1), fill=S.WHITE + (255,), width=int(wdt))
    for rr in (r0, r1):
        d.ellipse((c + sx * rr - wdt / 2, c + sy * rr - wdt / 2, c + sx * rr + wdt / 2, c + sy * rr + wdt / 2),
                  fill=S.WHITE + (255,))
    return im.resize((size, size), Image.LANCZOS)


def fader_segment_frame(size, t, j, fill, K, track_w):
    """Segment j (0 = bottom) of a FADER_SEGS-segment fader at value t: its slice of the fill, drawn exactly on
    pixel rows so the stacked segments join without seams."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    part = min(1.0, max(0.0, t * K - j))
    h = int(round(part * size))
    if h > 0:
        x0 = (size - track_w) // 2
        ImageDraw.Draw(im).rectangle((x0, size - h, x0 + track_w - 1, size - 1), fill=tuple(fill) + (255,))
    return im


def strip(frame_fn, size):
    n = strip_frames(size)
    out = Image.new("RGBA", (size, size * n), (0, 0, 0, 0))
    for i in range(n):
        out.paste(frame_fn(i / float(n - 1)), (0, i * size))
    return out


def fit_px(names, w):
    for px in range(int(S.LIST_PX), 14, -1):
        f = font(px)
        if all(f.getlength(n) <= w - 18 for n in names):
            return px
    return 15


def list_item(w, h, s, on, tab=None, px=None):
    """An option of the original's Selection widget. tab: (tab_on, tab_off) images for the bank tabs."""
    if tab:
        im = tab[0 if on else 1].convert("RGB").resize((w * SS, h * SS), Image.LANCZOS)
    else:
        im = Image.new("RGB", (w * SS, h * SS), S.PANEL)
    d = ImageDraw.Draw(im)
    f = font((px or S.LIST_PX) * SS)
    txt = s
    while f.getlength(txt) > (w - 16) * SS and len(txt) > 3:
        txt = txt[:-2].rstrip() + "\u2026"
    colour = S.WHITE if on else S.DIM
    if tab:   # the original right-aligns the bank names on their tabs
        d.text(((w - 8) * SS, h * SS / 2.0), txt, font=f, fill=colour, anchor="rm")
    else:
        d.text((10 * SS, h * SS / 2.0), txt, font=f, fill=colour, anchor="lm")
    return im.resize((w, h), Image.LANCZOS)


# ------------------------------------------------------------------------------------------------ spectrogram
# upstream common/Spectrogram.hpp
SPEC_RATE, SPEC_WIN = 40960, 8192
SPEC_MIN_S, SPEC_MAX_S, SPEC_MIN_F, SPEC_MAX_F = 0.2, 8.0, 100.0, 16000.0
SPEC_RECT = (305, 207)                     # its widget size; margins below are in the same units
SPEC_MARGIN = (50, 10, 15, 20)             # left, top, right, bottom


def spec_area(q):
    """The picture's place inside the spectrogram panel, upstream's margins scaled to the panel."""
    sx, sy = q["w"] / float(SPEC_RECT[0]), q["h"] / float(SPEC_RECT[1])
    l, t, r, b = SPEC_MARGIN
    x0, y0 = q["x"] + int(l * sx), q["y"] + int(t * sy)
    return x0, y0, int(q["w"] - (l + r) * sx), int(q["h"] - (t + b) * sy), sx, sy


def spectrogram_picture(samples, w, h):
    """Upstream's Spectrogram::uiIdle, column by column: a sin^2-windowed FFT at log-spaced times, the real part
    of the bin at each log-spaced frequency, |.| clamped to 8, alpha = 30 x that; white over the panel colour."""
    window = np.sin(np.pi * np.arange(SPEC_WIN) / (SPEC_WIN - 1)) ** 2
    ys = np.arange(h)
    freqs = np.exp(ys * np.log(SPEC_MAX_F / SPEC_MIN_F) / h) * SPEC_MIN_F
    idx = (freqs / (SPEC_RATE / float(SPEC_WIN)) + 1).astype(int)
    alpha = np.zeros((h, w), dtype=np.float32)
    for x in range(w):
        t = np.exp(x * np.log(SPEC_MAX_S / SPEC_MIN_S) / w) * SPEC_MIN_S
        off = int(t * SPEC_RATE)
        seg = samples[off:off + SPEC_WIN]
        if len(seg) < SPEC_WIN:
            seg = np.pad(seg, (0, SPEC_WIN - len(seg)))
        val = np.minimum(np.abs(np.fft.rfft(seg * window).real[idx]), 8.0)
        alpha[::-1, x] = val * 30.0                      # low frequencies at the bottom
    a = alpha[:, :, None] / 255.0
    rgb = np.array(S.PANEL, dtype=np.float32) * (1 - a) + 255.0 * a
    return Image.fromarray(rgb.astype(np.uint8), "RGB")


# ------------------------------------------------------------------------------------------------ the pass
def paint(p, g, cols):
    face, border, title = cols
    spec = S.DESIGNS[p]
    skin_root = os.path.join(S.HERE, p, "build", "skin")
    skin = os.path.join(skin_root, os.listdir(skin_root)[0], "Plugin Skins")
    tui_path = os.path.join(skin, "TUI.json")
    tui = json.load(open(tui_path))
    L = tui["pageData"]["componentDefinitions"]["localComponentDefinitions"]
    defs = {x["key"]: x["value"] for x in L}
    tabs = tui["pageData"]["tabs"]
    plist = json.load(open(os.path.join(S.HERE, p, "params.json")))["params"]
    pindex = {q["key"]: i for i, q in enumerate(plist)}
    ctl = {c["key"]: c for c in g["controls"]}
    fader_r, K = spec["fader"]
    knob_def, fader_def = "shKnob%d" % S.KNOB_R, "shKnob%d" % fader_r
    knob_s, fader_s = 2 * S.KNOB_R + 10, 2 * fader_r + 10
    track_w = fader_s - 6                 # px inside the track's border
    fader_cw = next(c["cw"] for c in g["controls"] if c["kind"] == "fader")
    art = os.path.join(S.ART, spec["upstream"])
    tab_imgs = (Image.open(os.path.join(art, "tab_on.png")), Image.open(os.path.join(art, "tab_off.png")))
    bank_n = len(S.options(p, "bank")) if "bank" in pindex else 0

    def key_of(inst):
        for m in inst.get("handle remapping", {}).get("map", []):
            if m["key"] == "Data" and m["value"].startswith("Parameter "):
                i = int(m["value"].split()[1])
                return plist[i]["key"] if i < len(plist) else None
        return None

    def restyle_label(sub, px, style, colour, just=None):
        ts = sub["componentData"]["data"]["textStyle"]
        ts["font"]["height"] = float(px)
        ts["font"]["style"] = style
        ts["colour"] = argb(colour)
        if just:
            ts["justification"] = just

    def set_bounds(o, x, y, w, h):
        o["bounds"]["bounds"] = "%d %d %d %d" % (x, y, w, h)

    # ---- pictures: knobs, fader segments, lists
    strip(lambda t: knob_frame(knob_s, t, face), knob_s).save(os.path.join(skin, "sh_knob_r%d.png" % S.KNOB_R), optimize=True)
    for j in range(K):
        name = "sh_knob_r%d.png" % fader_r if j == 0 else "df_fader_seg%d.png" % j
        strip(lambda t, j=j: fader_segment_frame(fader_s, t, j, face, K, track_w), fader_s).save(os.path.join(skin, name), optimize=True)
    for f in os.listdir(skin):
        if f.startswith("sh_seg_") and f.endswith(".png"):
            key, i, state = f[len("sh_seg_"):-4].rsplit("_", 2)
            w, h = Image.open(os.path.join(skin, f)).size
            list_item(w, h, S.options(p, key)[int(i)], state == "on", tab_imgs if key == "bank" else None,
                      fit_px(S.options(p, key), w)).save(os.path.join(skin, f))

    # ---- component definitions
    for sub in defs[knob_def]["componentsData"]:
        cd = sub["componentData"]
        if cd["type"] == "Focus":
            set_bounds(sub, 0, 0, S.KNOB_CW, S.NAME_H + knob_s + S.VALUE_H)
            cd["data"]["outlineColour"] = argb(title)
        elif cd["type"] == "Knob":
            set_bounds(sub, (S.KNOB_CW - knob_s) // 2, S.NAME_H, knob_s, knob_s)
            cd["data"]["numFrames"] = strip_frames(knob_s) - 1
        elif cd["name"] == "Name":
            set_bounds(sub, 0, 0, 0, 0)            # the name is baked in NotoSans, as the original draws it
        elif cd["name"] == "Value":
            set_bounds(sub, 0, S.NAME_H + knob_s, S.KNOB_CW, S.VALUE_H)
            restyle_label(sub, S.VALUE_PX, "Regular", S.WHITE)
    fc = g["controls"]
    f0 = next(c for c in fc if c["kind"] == "fader")
    head = f0["track_y"] - f0["top"]                        # names above the track
    col_h = head + K * fader_s + 4 + S.VALUE_H
    for sub in defs[fader_def]["componentsData"]:
        cd = sub["componentData"]
        if cd["type"] == "Focus":
            set_bounds(sub, 0, 0, fader_cw, col_h)
            cd["data"]["outlineColour"] = argb(title)
        elif cd["type"] == "Knob":                          # the bottom segment
            set_bounds(sub, (fader_cw - fader_s) // 2, head + (K - 1) * fader_s, fader_s, fader_s)
            cd["data"]["numFrames"] = strip_frames(fader_s) - 1
        elif cd["name"] == "Name":
            set_bounds(sub, 0, 0, 0, 0)
        elif cd["name"] == "Value":
            set_bounds(sub, 0, head + K * fader_s + 4, fader_cw, S.VALUE_H)
            restyle_label(sub, S.VALUE_PX, "Regular", S.WHITE)
    for j in range(1, K):                                   # the upper segments: just the knob, same actions
        seg = copy.deepcopy(defs[fader_def])
        seg["componentsData"] = [copy.deepcopy(s_) for s_ in seg["componentsData"] if s_["componentData"]["type"] == "Knob"]
        seg["componentsData"][0]["componentData"]["data"]["filmStrip"] = "df_fader_seg%d.png" % j
        set_bounds(seg["componentsData"][0], 0, 0, fader_s, fader_s)
        L.append({"key": "dfFaderSeg%d" % j, "value": seg})
    for k, v in defs.items():
        if k.startswith("shSeg_"):
            for sub in v["componentsData"]:
                if sub["componentData"]["type"] == "Focus":
                    sub["componentData"]["data"]["outlineColour"] = argb(title)

    # ---- component placement, per sub-page
    lists = {c["key"]: c for c in fc if c["kind"] == "list"}
    for tab in tabs:
        kids = defs[tab["componentName"]]["componentsData"]
        out = []
        for inst in kids:
            t = inst["componentData"]["type"]
            key = key_of(inst)
            if t == knob_def:
                c = ctl[key]
                set_bounds(inst, c["cx"] - S.KNOB_CW // 2, c["top"], S.KNOB_CW, S.NAME_H + knob_s + S.VALUE_H)
                out.append(inst)
            elif t == fader_def:
                c = ctl[key]
                set_bounds(inst, c["cx"] - fader_cw // 2, c["top"], fader_cw, col_h)
                out.append(inst)
                for j in range(1, K):
                    seg = copy.deepcopy(inst)
                    seg["componentData"]["type"] = "dfFaderSeg%d" % j
                    seg["componentData"]["name"] = "%s %d" % (inst["componentData"]["name"], j)
                    seg["bounds"]["acceptsHWFocus"] = "No"
                    set_bounds(seg, c["cx"] - fader_s // 2, c["track_y"] + (K - 1 - j) * fader_s, fader_s, fader_s)
                    out.append(seg)
            elif t.startswith("shSeg_"):
                i = int(t.rsplit("_", 1)[1])
                c = lists[key]
                w = c["w"]
                if c["by_bank"]:          # this bank's five presets, visible only while that bank is current
                    per = c["rows"]
                    b, row = i // per, i % per
                    set_bounds(inst, c["x"], c["y"] + row * S.LIST_ROW, w, 33)
                    inst["bounds"]["showWhenDataModelInvalid"] = "Show"
                    inst["bounds"]["additionalInvalidatingHandles"] = [
                        "IndexedEnabling/%d/%d/Parameter %d" % (b, bank_n, pindex["bank"])]
                else:                     # column by column, as the original's Selection widgets
                    col, row = i // c["rows"], i % c["rows"]
                    set_bounds(inst, c["x"] + col * (w + 8), c["y"] + row * S.LIST_ROW, w, 33)
                out.append(inst)
            else:
                out.append(inst)
        kids[:] = out

    # ---- Q-Link region per sub-page: its own controls
    def rect(key):
        c = ctl.get(key)
        if not c:
            return None
        if c["kind"] == "knob":
            return (c["cx"] - S.KNOB_CW // 2, c["top"], S.KNOB_CW, S.NAME_H + knob_s + S.VALUE_H)
        if c["kind"] == "fader":
            return (c["cx"] - fader_cw // 2, c["top"], fader_cw, col_h)
        cols_ = 1 if c["by_bank"] else -(-c["n"] // c["rows"])
        return (c["x"], c["y"], cols_ * (c["w"] + 8) - 8, c["rows"] * S.LIST_ROW)
    banks = dict(spec["qlinks"])
    for tab in tabs:
        rs = [r for r in (rect(k) for k in banks.get(tab["tabName"], "").split(",")) if r]
        if rs:
            x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs)
            x1 = max(r[0] + r[2] for r in rs); y1 = max(r[1] + r[3] for r in rs)
            tab["qlinkBoundsData"] = ["%d %d %d %d" % (x0, y0, x1 - x0, y1 - y0)]

    # ---- the original's spectrogram: one picture per preset, shown while that preset is the current one
    spec_q = g["panels"][spec["spectrogram"]] if spec.get("spectrogram") is not None else None
    if spec_q:
        sx0, sy0, sw, sh, _, _ = spec_area(spec_q)
        n_pre = len(S.options(p, "preset"))
        src = os.path.join(S.HERE, p, "build", "spectro")
        for k in range(n_pre):
            samples = np.fromfile(os.path.join(src, "spec_%d.f32" % k), dtype=np.float32)
            spectrogram_picture(samples, sw, sh).save(os.path.join(skin, "df_spec_%d.png" % k), optimize=True)
        for tab in tabs:
            kids = defs[tab["componentName"]]["componentsData"]
            bgi = next(i for i, ch in enumerate(kids)
                       if ch["componentData"]["type"] == "Image" and ch["componentData"]["name"] == "Background")
            pics = []
            for k in range(n_pre):
                pic = copy.deepcopy(kids[bgi])
                pic["componentData"]["name"] = "Spectrogram %d" % k
                pic["componentData"]["data"]["image"] = "df_spec_%d.png" % k
                set_bounds(pic, sx0, sy0, sw, sh)
                pic["bounds"]["showWhenDataModelInvalid"] = "Show"
                pic["bounds"]["additionalInvalidatingHandles"] = [
                    "IndexedEnabling/%d/%d/Parameter %d" % (k, n_pre, pindex["preset"])]
                pics.append(pic)
            kids[bgi + 1:bgi + 1] = pics

    # ---- page art (one picture for every sub-page)
    im = Image.new("RGB", (S.W * SS, S.H * SS), S.BG)
    d = ImageDraw.Draw(im)

    def txt(x, y, s, px, colour, anchor):
        d.text((x * SS, y * SS), s, font=font(px * SS), fill=colour, anchor=anchor)

    for q in g["panels"]:
        d.rounded_rectangle((q["x"] * SS, q["y"] * SS, (q["x"] + q["w"]) * SS, (q["y"] + q["h"]) * SS),
                            radius=12 * SS, fill=S.PANEL, outline=tuple(border), width=int(1.8 * SS))
        if q["title"].startswith("<"):      # left-aligned title, as Early's "Reflection Type"
            txt(q["x"] + 20, q["y"] + 24, q["title"][1:], S.TITLE_PX, S.WHITE, "lm")
        elif q["title"]:
            txt(q["x"] + q["w"] / 2.0, q["y"] + 22, q["title"], S.TITLE_PX, S.WHITE, "mm")
    if spec_q:   # upstream's axis labels: frequencies right-aligned in the left margin, decay times below
        sx0, sy0, sw, sh, fx, fy = spec_area(spec_q)
        lab_px = min(19.0, 13 * min(fx, fy) * 1.05)
        for f_, name in zip((125, 250, 500, 1000, 2000, 4000, 8000, 16000),
                            ("125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz")):
            y = sy0 + sh - sh * math.log(f_ / SPEC_MIN_F) / math.log(SPEC_MAX_F / SPEC_MIN_F)
            txt(sx0 - 8 * fx, y, name, lab_px, S.WHITE, "rm")
        for t_, name in zip((0.5, 1.0, 2.0, 4.0, 8.0), (u"\u00bds", "1s", "2s", "4s", "8s")):
            x = sw * math.log(t_ / SPEC_MIN_S) / math.log(SPEC_MAX_S / SPEC_MIN_S)
            txt(spec_q["x"] + x + 40 * fx, spec_q["y"] + spec_q["h"] - 5 * fy - 6, name, lab_px, S.WHITE, "rm")
    for c in fc:
        if c["kind"] == "knob":
            txt(c["cx"], c["top"] + S.NAME_H / 2.0, c["name"], S.NAME_PX, S.WHITE, "mm")
            for a in (-KNOB_TRAVEL / 2, KNOB_TRAVEL / 2):      # the original's min/max dots
                rr = S.KNOB_R + 8
                x = c["cx"] + math.sin(math.radians(a)) * rr
                y = c["cy"] - math.cos(math.radians(a)) * rr
                d.ellipse(((x - 2.8) * SS, (y - 2.8) * SS, (x + 2.8) * SS, (y + 2.8) * SS), fill=S.WHITE)
        elif c["kind"] == "fader":
            words = c["name"].split(" ", 1)                     # "Dry / Level", as the original prints them
            for li, wd in enumerate(words):
                txt(c["cx"], c["top"] + 13 + 26 * li, wd, S.NAME_PX, S.WHITE, "mm")
            x0 = c["cx"] - (fader_s // 2) + (fader_s - track_w) // 2 - 2
            y0 = c["track_y"] - 2
            d.rectangle((x0 * SS, y0 * SS, (x0 + track_w + 4) * SS, (y0 + K * fader_s + 4) * SS), fill=S.WHITE)
            d.rectangle(((x0 + 2) * SS, (y0 + 2) * SS, (x0 + 2 + track_w) * SS, (y0 + 2 + K * fader_s) * SS),
                        fill=S.BLACK)
    im = im.resize((S.W, S.H), Image.LANCZOS)
    up = Image.open(os.path.join(art, "background.png")).convert("RGB")
    (lx0, ly0, lx1, ly1), (bx0, by0, bx1, by1) = g["logo"]
    logo = up.crop((lx0, ly0, lx1, ly1))
    sc = min((bx1 - bx0) / float(logo.width), (by1 - by0) / float(logo.height))
    logo = logo.resize((int(logo.width * sc), int(logo.height * sc)), Image.LANCZOS)
    im.paste(logo, (bx0, by0 + ((by1 - by0) - logo.height) // 2))
    bg_files = {ch["componentData"]["data"]["image"] for tab in tabs for ch in defs[tab["componentName"]]["componentsData"]
                if ch["componentData"]["type"] == "Image" and ch["componentData"]["name"] == "Background"}
    for f in bg_files:
        im.save(os.path.join(skin, f))

    json.dump(tui, open(tui_path, "w"), indent=1)
    for f in os.listdir(skin):
        if f.endswith(".png") and Image.open(os.path.join(skin, f)).height > MAX_IMAGE_H:
            raise SystemExit("paint: %s is taller than MPC can show (%d px)" % (f, MAX_IMAGE_H))
    print("painted:", skin)
