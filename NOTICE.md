# Notices

**Dragonfly Reverb for MPC OS** is an unofficial port of Dragonfly Reverb to Akai MPC OS devices. It is not
affiliated with or endorsed by the Dragonfly Reverb authors or by Akai Professional / inMusic.

The port as a whole is licensed under the **GNU General Public License, version 3 or later** (`LICENSE`), as
Dragonfly Reverb is. Source code: this repository; every release is built from the tag of the same version.

## Components

### Dragonfly Reverb 3.2.10
- Copyright (c) 2018-2019 Michael Willis, Rob van den Berg
- https://github.com/michaelwillis/dragonfly-reverb (commit `772cb2a7e6244aef7cd68188392ef6924a479dcc`)
- Licence: GPL-3.0-or-later (`LICENSE`)
- Used: the reverb DSP of all four plugins (`src/dragonfly/plugins/*/DSP.*`, `DistrhoPluginInfo.h`, `common/`),
  compiled into the plugins; the UI source as layout reference (`UI.cpp.ref`, not compiled); the artwork
  (`src/dragonfly/artwork/`: logo and title, knob, tab and background images), which the MPC pages are drawn from.
- Modified: `src/dragonfly/plugins/room-reverb/DSP.cpp` (2026-09-25, `mute()` also clears the input filters).
  See `src/VENDORED.md`.

### Freeverb3
- Copyright (C) 2006-2018 Teru Kamogashira; parts by others, listed in `src/dragonfly/common/freeverb/AUTHORS`
  (including libgdither, Copyright (C) 2002 Steve Harris; algorithms after Jezar at Dreampoint's Freeverb and
  Fons Adriaensen's work)
- Licence: GPL-2.0-or-later (`src/dragonfly/common/freeverb/COPYING`), distributed here under GPL-3.0 as part of
  the whole
- Used: the reverb algorithms inside Dragonfly Reverb (`src/dragonfly/common/freeverb/`), compiled into the plugins.

### Noto Sans
- Copyright 2012 Google Inc. All Rights Reserved.
- Licence: SIL Open Font License 1.1 (`src/dragonfly/artwork/OFL.txt`)
- Used: at build time only, to draw the pages' text into their images. The font file itself is not in the
  release; the release's images contain text drawn with it.

### mpc-vst-plugins
- https://github.com/sd88me/mpc-vst-plugins (sd88me), commit `c0394f0352d77072f345bd929d26c6fc09bc34a0`
- Used: its `wrapper/popup.h` is compiled into the plugins; its tools generate the page skins (TUI.json, Q-Links)
  and are run from a separate checkout at build time. Its bundled force-shadow tools are MIT-licensed
  (Copyright (c) 2026 sd88me). At that commit the repository itself states no licence.

### This port
- Copyright (c) 2026 the mpc-vst-dragonfly contributors
- Licence: GPL-3.0-or-later
- The VST2 wrapper, DSP glue, DPF stand-in headers (`src/shim/`), page design and painting tools, tests and
  build scripts (files marked `SPDX-License-Identifier: GPL-3.0-or-later`).

## Trademarks
"Akai", "MPC" and "Force" are trademarks of inMusic Brands; they are used only to say which devices this runs on.
