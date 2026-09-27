#!/usr/bin/env python3
"""screenshot.py -- render a built MPC page the way MPC lays it out, for docs (mpc-vst-dragonfly).

  tools/screenshot.py <hall|room|plate|early> <out.png>      (after vst/build.sh)

Uses the skin's own TUI.json: the background, every knob/fader filmstrip at the parameter's default, option lists
with the default option selected, and live text (names, values, preset field) in Titillium Web at JUCE's sizing
(font height = ascent + descent), from mpc-vst-plugins' tools/html_art/fonts. Value text follows
vst/dragonfly_vst.cpp's format_value(). The preset list is drawn closed.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MPC_VST = os.environ.get("MPC_VST", os.path.join(ROOT, "..", "mpc-vst-plugins"))
FONTS = os.path.join(MPC_VST, "tools", "html_art", "fonts")


def jfont(style, height):
    path = os.path.join(FONTS, "TitilliumWeb-%s.ttf" % style)
    probe = ImageFont.truetype(path, 100)
    a, d = probe.getmetrics()
    return ImageFont.truetype(path, max(1, round(height * 100.0 / (a + d))))


def display(p, v):
    if p.get("options"):
        return p["options"][int(v)]
    unit, rng = p.get("unit", ""), abs(p["max"] - p["min"])
    dec = 2 if rng <= 3 else 1 if rng <= 20 else 0
    if unit == "Hz" and v >= 1000:
        return "%.1f kHz" % (v / 1000.0)
    if unit == "%":
        return "%.0f%%" % v
    if unit == "X":
        return "%.2fx" % v
    return ("%.*f %s" % (dec, v, unit)).strip()


def norm(p, v):
    if p.get("options"):
        return v / float(max(1, len(p["options"]) - 1))
    return (v - p["min"]) / float(p["max"] - p["min"])


def main(plugin, out):
    vd = os.path.join(ROOT, "vst", plugin)
    params = json.load(open(os.path.join(vd, "params.json")))["params"]
    skin_root = os.path.join(vd, "build", "skin")
    skin = os.path.join(skin_root, os.listdir(skin_root)[0], "Plugin Skins")
    tui = json.load(open(os.path.join(skin, "TUI.json")))
    L = tui["pageData"]["componentDefinitions"]["localComponentDefinitions"]
    defs = {x["key"]: x["value"] for x in L}
    tab = defs[tui["pageData"]["tabs"][0]["componentName"]]
    page = None

    def param_of(ch, handle="Data"):
        for m in ch.get("handle remapping", {}).get("map", []):
            if m["key"] == handle and m["value"].startswith("Parameter "):
                i = int(m["value"].split()[1])
                return params[i] if i < len(params) else None
        return None

    def label(d, sub, x0, y0, s):
        ts = sub["componentData"]["data"]["textStyle"]
        f = jfont(ts["font"]["style"], ts["font"]["height"])
        x, y, w, h = map(int, sub["bounds"]["bounds"].split())
        c = ts["colour"]
        col = tuple(int(c[i:i + 2], 16) for i in (2, 4, 6))
        left = "Left" in ts["justification"]
        d.text((x0 + x + (0 if left else w / 2.0), y0 + y + h / 2.0), s, font=f, fill=col, anchor="lm" if left else "mm")

    for ch in tab["componentsData"]:
        cd = ch["componentData"]
        t = cd["type"]
        x0, y0, w0, h0 = map(int, ch["bounds"]["bounds"].split())
        if t == "Image" and cd["name"] == "Background":
            page = Image.open(os.path.join(skin, cd["data"]["image"])).convert("RGBA")
            continue
        if page is None or t.startswith(("shPopPanel_", "shPopOpt_")):
            continue
        d = ImageDraw.Draw(page)
        p = param_of(ch)
        for sub in defs.get(t, {}).get("componentsData", []):
            scd = sub["componentData"]
            x, y, w, h = map(int, sub["bounds"]["bounds"].split())
            if scd["type"] == "Knob" and p:
                strip = Image.open(os.path.join(skin, scd["data"]["filmStrip"])).convert("RGBA")
                n = scd["data"]["numFrames"]
                fh = strip.height // (n + 1)
                k = int(round(norm(p, p["default"]) * n))
                fr = strip.crop((0, k * fh, strip.width, (k + 1) * fh)).resize((w, h))
                page.alpha_composite(fr, (x0 + x, y0 + y))
            elif scd["type"] == "Button" and p:
                on = int(p["default"]) == scd["data"]["buttonId"]
                im = Image.open(os.path.join(skin, scd["data"]["onImage" if on else "offImage"])).convert("RGBA")
                page.alpha_composite(im.resize((w, h)), (x0 + x, y0 + y))
            elif scd["type"] == "Label" and scd["name"] == "Name" and p:
                label(d, sub, x0, y0, cd["name"])
            elif scd["type"] == "Label" and scd["name"] == "Value":
                q = p if not t.startswith("shPopField") else param_of(ch, "Text")
                if q:
                    label(d, sub, x0, y0, display(q, q["default"]))
    page.convert("RGB").save(out)
    print("wrote", out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
