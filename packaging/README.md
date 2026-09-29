# Dragonfly Reverb for MPC OS

An unofficial port; not affiliated with or endorsed by the Dragonfly Reverb authors or by Akai Professional.

Four reverbs from Dragonfly Reverb 3.2.10 (Michael Willis, Rob van den Berg) as native insert effects, each with a
touchscreen page modelled on the original plugin's (including its spectrogram), Q-Link mapping and its presets:

| Folder | Plugin (manufacturer "Dragonfly") | Presets |
|---|---|---|
| Dragonfly - VST - Hall | Hall | 25, in 5 banks |
| Dragonfly - VST - Room | Room | 25, in 5 banks |
| Dragonfly - VST - Plate | Plate | 8, plus 3 reverb types |
| Dragonfly - VST - Early Refl | Early Refl (Early Reflections) | 8 reflection types |

Version @VERSION@. Each folder is self-contained: the plugin (`.so`), its `plugin-meta.xml`, its page
(`Plugin Skins/`), `version.xml`, a parameter description (`<Name>.json`) and its licences.

## Requirements
- A Gen 1 Akai Force or MPC (Live, Live II, One, X, Key 61)
- SSH access to the device (modded firmware, e.g. MockbaMod); you should be comfortable running shell commands
- The `Synths` folder with `vstscanner.sh` from the Force VST plugins distribution

## Install
**Assumption: you use MockbaMod and its memory card is `/media/662522`** (for anything else see Other firmware).

1. Copy the four `Dragonfly - VST - ...` folders into the `Synths` folder on the card
   (`/media/662522/Synths`, next to `vstscanner.sh`). Copy the folders themselves, directly into `Synths`.
2. On the device, run the scanner: `ssh ip-of-Force 'sh /media/662522/Synths/vstscanner.sh'`
   (after its first run it is installed as the command `vstscanner`).
3. MPC restarts. The plugins are under the VST category, manufacturer "Dragonfly" (turn on the manufacturer tab to
   group them).

To remove a plugin, delete its folder and run the scanner again. `vstmanager` (in the same distribution) can
enable and disable them instead.

### Updating from 1.1.x
1.1 used two folders per plugin. Delete all of them from `Synths` first: the four `dragonfly.vst.*` folders and
the four `Dragonfly - VST - Dragonfly ...` page folders. Then install as above.

## Other firmware
The scanner registers every plugin folder in a `Synths` folder on any drive under `/media` (memory cards, and the
internal drive `/media/az01-internal`). It needs MPC's settings file; it looks at MockbaMod's
`/data/Settings/MPC/MPC.settings` unless given another as its first argument.

1. SSH into the device. `ls /media` lists the drives; pick one (a card, or `az01-internal`) and create
   `/media/<drive>/Synths` if it doesn't exist.
2. Copy `vstscanner.sh` and the four `Dragonfly - VST - ...` folders into it.
3. Find MPC's settings file: `find / -name MPC.settings 2>/dev/null` (usually
   `/media/az01-internal/Settings/MPC/MPC.settings`) and back it up: `cp <that path> <that path>.bak`
4. Run the scanner with it: `sh /media/<drive>/Synths/vstscanner.sh <that path>`
5. MPC restarts and the plugins appear under VST. If a plugin shows MPC's plain parameter list instead of its own
   page, MPC doesn't look for pages on that drive: check `grep SynthContentLocations <settings path>` and use a
   drive whose `Synths` folder is listed there.

To restore the old plugin list, stop MPC (`systemctl stop acvs`), copy the backup back, and start it
(`systemctl start acvs`).

## Notes
- Install either this way (vstscanner) or with the MPC OS Plugin Catalog's per-plugin zips, not both on one
  device: vstscanner rebuilds MPC's whole plugin list and would drop plugins installed with `install.sh`.
- The scanner rebuilds MPC's whole plugin list from what it finds, so keep every plugin you use in a `Synths` folder.
- Hall and Room have two Q-Link banks, MAIN and EQ (Hall) / TONE (Room), switched by the tab at the bottom of the
  screen. Presets: tap a bank tab, then a preset, as in the original plugins.
- The spectrogram (Hall, Room, Plate) shows the selected preset's reverb, computed as the original does. The
  original redraws it as you turn knobs; here it changes with the preset only.
- CPU: Hall is the heaviest of the four. Start with one instance and check it plays cleanly before stacking more.
- The C++ runtime is built in; the plugins need nothing from the device but libc.

## Licence and source
GPL-3.0-or-later (`LICENSE`), as Dragonfly Reverb (Copyright (c) 2018-2019 Michael Willis, Rob van den Berg)
and freeverb3 (Copyright (C) 2006-2018 Teru Kamogashira and others). `NOTICE.md` lists every component with its
authors and licence; `licenses/` holds the licence texts; each plugin folder carries `LICENSE` and `NOTICE.md`.
Source code: @SOURCE@
