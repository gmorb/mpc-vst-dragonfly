"""df_paint.py -- phase 2 of df_skin.py: repaint a kit-built skin in the Dragonfly look (mpc-vst-dragonfly).

Replaces, in vst/<p>/build/skin/<skin>/Plugin Skins/:
  sh_bg_*.png          page art: charcoal page, rounded panels with the plugin's border colour, upstream's
                       logo + title (cropped from its background.png), panel titles, knob min/max dots,
                       the preset field
  sh_knob_r*.png       128-frame knob filmstrip: upstream's knob (light rim, coloured face, white pointer),
                       redrawn at the MPC size, 270 degrees of travel; transparent edges
  sh_slider_v_*.png    128-frame level faders: black track, light border, coloured fill (upstream's sliders)
  sh_seg_*.png         option lists (Plate presets / reverb type, Early reflection type): upstream's plain
                       list look, grey names and the current one in white
  sh_pop*.png          the preset pop-out: panel with bank headings, one column per bank
and in TUI.json: every knob/fader cell laid out as upstream draws it (name above, value below), bigger white
live text, the preset field widened, the pop-out moved down under its headings. Only bounds, fonts, colours
and images change; the kit's components, actions and parameter bindings are left exactly as built.
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

import df_skin as S

SS = 4   # supersampling for everything drawn


def font(px):
    return ImageFont.truetype(os.path.join(S.ART, "NotoSans-Regular.ttf"), int(round(px)))


def argb(c, a=255):
    return "%02x%02x%02x%02x" % (a, c[0], c[1], c[2])


# ---------------------------------------------------------------------------------------------- drawing helpers
def knob_frame(size, t, face):
    """Upstream's knob.png, redrawn: light rim, face, white pointer; t in 0..1 over 270 degrees."""
    n = size * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2.0
    r = (S.KNOB_R) * SS                     # visible radius (the frame is 2r+10)
    d.ellipse((c - r, c - r, c + r, c + r), fill=S.WHITE + (255,))
    ri = r - 3.2 * SS
    d.ellipse((c - ri, c - ri, c + ri, c + ri), fill=tuple(face) + (255,))
    a = math.radians(-135 + 270 * t)       # 0 = up, clockwise
    sx, sy = math.sin(a), -math.cos(a)
    r0, r1 = ri * 0.52, ri * 0.97
    wdt = 3.4 * SS
    d.line((c + sx * r0, c + sy * r0, c + sx * r1, c + sy * r1), fill=S.WHITE + (255,), width=int(wdt))
    for rr in (r0, r1):                     # round caps
        d.ellipse((c + sx * rr - wdt / 2, c + sy * rr - wdt / 2, c + sx * rr + wdt / 2, c + sy * rr + wdt / 2),
                  fill=S.WHITE + (255,))
    return im.resize((size, size), Image.LANCZOS)


def fader_frame(size, t, fill, track_w):
    """Upstream's level sliders: a black track with a light border, filled from the bottom."""
    n = size * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = (n - track_w * SS) / 2.0
    x1 = x0 + track_w * SS
    y0, y1 = 2 * SS, n - 2 * SS
    b = 2 * SS
    d.rectangle((x0, y0, x1, y1), fill=S.WHITE + (255,))
    d.rectangle((x0 + b, y0 + b, x1 - b, y1 - b), fill=S.BLACK + (255,))
    h = (y1 - b) - (y0 + b)
    top = (y1 - b) - h * t
    if t > 0:
        d.rectangle((x0 + b, top, x1 - b, y1 - b), fill=tuple(fill) + (255,))
    return im.resize((size, size), Image.LANCZOS)


def strip(frames_fn, size):
    out = Image.new("RGBA", (size, size * S_FRAMES), (0, 0, 0, 0))
    for i in range(S_FRAMES):
        out.paste(frames_fn(i / float(S_FRAMES - 1)), (0, i * size))
    return out


S_FRAMES = 128


def rounded_panel(d, x, y, w, h, border, fill=S.PANEL, radius=12):
    d.rounded_rectangle((x * SS, y * SS, (x + w) * SS, (y + h) * SS), radius=radius * SS, fill=fill,
                        outline=border, width=int(1.6 * SS))


def text(d, xy, s, px, colour, anchor="la"):
    d.text((xy[0] * SS, xy[1] * SS), s, font=font(px * SS), fill=colour, anchor=anchor)


def label_image(w, h, s, px, colour, bg, x_pad=12, bar=None):
    im = Image.new("RGB", (w * SS, h * SS), bg)
    d = ImageDraw.Draw(im)
    if bar:
        d.rectangle((0, 0, 4 * SS, h * SS), fill=bar)
    f = font(px * SS)
    txt = s
    while f.getlength(txt) > (w - x_pad - 6) * SS and len(txt) > 3:   # never spill: ellipsize
        txt = txt[:-2].rstrip() + "\u2026"
    d.text((x_pad * SS, h * SS / 2.0), txt, font=f, fill=colour, anchor="lm")
    return im.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------- the pass
def paint(p, g, cols):
    face, border, title = cols
    skin_root = os.path.join(S.HERE, p, "build", "skin")
    skin = os.path.join(skin_root, os.listdir(skin_root)[0], "Plugin Skins")
    tui_path = os.path.join(skin, "TUI.json")
    tui = json.load(open(tui_path))
    L = tui["pageData"]["componentDefinitions"]["localComponentDefinitions"]
    defs = {x["key"]: x["value"] for x in L}
    tabs = [k for k in defs if "|" in k]
    ctl = {c["label"]: c for c in g["controls"] if "label" in c}
    popups = [c for c in g["controls"] if c["kind"] == "popup"]
    spec = S.PAGES[p]

    # ---- filmstrips
    for f in os.listdir(skin):
        path = os.path.join(skin, f)
        if f.startswith("sh_knob_r") and f.endswith(".png"):
            size = Image.open(path).width
            strip(lambda t: knob_frame(size, t, face), size).save(path, optimize=True)
        elif f.startswith("sh_slider_v_") and f.endswith(".png"):
            size = Image.open(path).width
            tw = 30 if size < 150 else 42
            strip(lambda t: fader_frame(size, t, face, tw), size).save(path, optimize=True)

    # ---- option lists (enum segments): plain names, the current one white
    for f in os.listdir(skin):
        if f.startswith("sh_seg_") and f.endswith(".png"):
            path = os.path.join(skin, f)
            w, h = Image.open(path).size
            base = f[len("sh_seg_"):-4]                 # <key>_<i>_<on|off>
            key, i, state = base.rsplit("_", 2)
            name = S.options(p, key)[int(i)]
            on = state == "on"
            label_image(w, h, name, S.LIST_PX, S.WHITE if on else S.DIM, (96, 96, 96) if on else S.PANEL,
                        bar=tuple(title) if on else None).save(path)

    # ---- preset pop-out: headings row, one column per bank
    head = 36
    for c in popups:
        banks = c["banks"]
        for k in tabs:
            for ch in defs[k]["componentsData"]:
                t = ch["componentData"]["type"]
                if t.startswith("shPopPanel_") or t.startswith("shPopOpt_"):
                    x, y, w, h = map(int, ch["bounds"]["bounds"].split())
                    if t.startswith("shPopPanel_"):
                        pan = (x, y, w, h + head)
                        ch["bounds"]["bounds"] = "%d %d %d %d" % pan
                    else:
                        ch["bounds"]["bounds"] = "%d %d %d %d" % (x, y + head, w, h)
        for key, v in defs.items():
            if key.startswith("shPopPanel_"):
                for sub in v["componentsData"]:
                    if sub["componentData"]["type"] == "Image":
                        x, y, w, h = map(int, sub["bounds"]["bounds"].split())
                        sub["bounds"]["bounds"] = "%d %d %d %d" % (x, y, w, h + head)
                        img = sub["componentData"]["data"]["image"]
                        pw, ph = w, h + head
                        im = Image.new("RGB", (pw * SS, ph * SS), S.BG)
                        d = ImageDraw.Draw(im)
                        rounded_panel(d, 0, 0, pw - 1, ph - 1, tuple(border), radius=10)
                        colw = c["w"]
                        for bi, b in enumerate(banks):
                            bx = 6 + bi * (colw + 2)
                            text(d, (bx + 12, 22), b, S.HEAD_PX, tuple(title), anchor="lm")
                            d.line(((bx + 8) * SS, (head + 2) * SS, (bx + colw - 8) * SS, (head + 2) * SS),
                                   fill=tuple(border), width=SS)
                        im.resize((pw, ph), Image.LANCZOS).save(os.path.join(skin, img))
        for f in os.listdir(skin):
            if f.startswith("sh_popopt_") and f.endswith(".png"):
                path = os.path.join(skin, f)
                w, h = Image.open(path).size
                base = f[len("sh_popopt_"):-4]           # <tab>_<key>_<i>_<on|off>
                parts = base.split("_")
                state, i = parts[-1], int(parts[-2])
                key = "_".join(parts[1:-2])
                on = state == "on"
                label_image(w, h, S.options(p, key)[i], S.POPOPT_PX, S.WHITE if on else S.DIM,
                            (100, 100, 100) if on else S.PANEL, x_pad=10, bar=tuple(title) if on else None).save(path)

    # ---- TUI.json: cells laid out like upstream (name above, control, value below), bigger white text
    def restyle_label(sub, px, style, colour):
        ts = sub["componentData"]["data"]["textStyle"]
        ts["font"]["height"] = float(px)
        ts["font"]["style"] = style
        ts["colour"] = argb(colour)

    cell_w = {}
    for key, v in defs.items():
        is_knob, is_fader = key.startswith("shKnob"), key.startswith("shSlider_v_")
        if not (is_knob or is_fader):
            continue
        s = next(int(sub["bounds"]["bounds"].split()[2]) for sub in v["componentsData"]
                 if sub["componentData"]["type"] == "Knob")
        cw = max(116, s)
        ch = S.NAME_H + s + S.VALUE_H
        cell_w[key] = (cw, ch, s)
        for sub in v["componentsData"]:
            cd = sub["componentData"]
            b = sub["bounds"]
            if cd["type"] == "Focus":
                b["bounds"] = "0 0 %d %d" % (cw, ch)
                cd["data"]["outlineColour"] = argb(title)
            elif cd["type"] == "Knob":
                b["bounds"] = "%d %d %d %d" % ((cw - s) // 2, S.NAME_H, s, s)
            elif cd["name"] == "Name":
                b["bounds"] = "0 0 %d %d" % (cw, S.NAME_H)
                restyle_label(sub, S.NAME_PX, "SemiBold", S.WHITE)
            elif cd["name"] == "Value":
                b["bounds"] = "0 %d %d %d" % (S.NAME_H + s, cw, S.VALUE_H)
                restyle_label(sub, S.VALUE_PX, "Regular", S.WHITE)
    field = {}
    for key, v in defs.items():
        if key.startswith("shPopField_"):
            c = popups[0]
            fw = c["field_w"]
            field[key] = fw
            for sub in v["componentsData"]:
                cd = sub["componentData"]
                if cd["type"] == "Focus":
                    sub["bounds"]["bounds"] = "0 0 %d %d" % (fw, c["h"])
                    cd["data"]["outlineColour"] = argb(title)
                elif cd["name"] == "Value":
                    sub["bounds"]["bounds"] = "18 0 %d %d" % (fw - 70, c["h"])
                    restyle_label(sub, S.FIELD_PX, "SemiBold", S.WHITE)
                    sub["componentData"]["data"]["textStyle"]["justification"] = "centredLeft"
        elif key.startswith("shSeg") or key.startswith("shEnum"):
            for sub in v["componentsData"]:
                if sub["componentData"]["type"] == "Focus":
                    sub["componentData"]["data"]["outlineColour"] = argb(title)
    field_rects = []
    for k in tabs:
        for ch in defs[k]["componentsData"]:
            t = ch["componentData"]["type"]
            if t in cell_w:
                c = ctl.get(ch["componentData"]["name"])
                if not c:
                    raise SystemExit("paint: no geometry for control %r" % ch["componentData"]["name"])
                cw, chh, s = cell_w[t]
                ch["bounds"]["bounds"] = "%d %d %d %d" % (c["cx"] - cw // 2, c["cy"] - S.NAME_H - s // 2, cw, chh)
            elif t in field:
                c = popups[0]
                pan = next(q for q in g["panels"] if q["title"] == "Preset")
                fx = pan["x"] + S.PAD + 150
                fy = c["cy"] - c["h"] // 2
                ch["bounds"]["bounds"] = "%d %d %d %d" % (fx, fy, field[t], c["h"])
                if (fx, fy) not in [r[:2] for r in field_rects]:
                    field_rects.append((fx, fy, field[t], c["h"]))
            elif t.startswith("sh") and ch["componentData"]["type"] not in ("Image",):
                for sub in defs.get(t, {}).get("componentsData", []):
                    if sub["componentData"]["type"] == "Focus":
                        sub["componentData"]["data"]["outlineColour"] = argb(title)
    json.dump(tui, open(tui_path, "w"), indent=1)

    # ---- page background
    bg_files = sorted({ch["componentData"]["data"]["image"] for k in tabs for ch in defs[k]["componentsData"]
                       if ch["componentData"]["type"] == "Image" and ch["componentData"]["name"] == "Background"})
    im = Image.new("RGB", (S.W * SS, S.H * SS), S.BG)
    d = ImageDraw.Draw(im)
    for q in g["panels"]:
        rounded_panel(d, q["x"], q["y"], q["w"], q["h"], tuple(border))
        if q["title"] == "Preset":
            text(d, (q["x"] + 26, q["y"] + q["h"] / 2.0 + 14), "Preset", S.HEAD_PX + 2, S.WHITE, anchor="lm")
        elif q["title"]:
            text(d, (q["x"] + q["w"] / 2.0, q["y"] + 22), q["title"], S.HEAD_PX, S.WHITE, anchor="mm")
    for fx, fy, fw, fh in field_rects:
        d.rounded_rectangle((fx * SS, fy * SS, (fx + fw) * SS, (fy + fh) * SS), radius=8 * SS, fill=(52, 52, 52),
                            outline=tuple(border), width=int(1.6 * SS))
        ax, ay = fx + fw - 30, fy + fh / 2.0
        d.polygon([((ax - 10) * SS, (ay - 5) * SS), ((ax + 10) * SS, (ay - 5) * SS), (ax * SS, (ay + 7) * SS)],
                  fill=tuple(title))
    for c in g["controls"]:
        if c["kind"] == "knob":   # upstream's min/max dots under each knob
            for a in (-135, 135):
                rr = S.KNOB_R + 7
                x = c["cx"] + math.sin(math.radians(a)) * rr
                y = c["cy"] - math.cos(math.radians(a)) * rr
                d.ellipse(((x - 2.6) * SS, (y - 2.6) * SS, (x + 2.6) * SS, (y + 2.6) * SS), fill=S.WHITE)
    im = im.resize((S.W, S.H), Image.LANCZOS)
    # logo + title, cropped from upstream's own background art
    up = Image.open(os.path.join(S.ART, spec["upstream"], "background.png")).convert("RGB")
    logo = up.crop(spec["logo_box"])
    lx, ly, lw, lh = g["logo"]
    logo = logo.resize((lw, lh), Image.LANCZOS)
    im.paste(logo, (lx, ly))
    for f in bg_files:
        im.save(os.path.join(skin, f))
    print("painted:", skin)
