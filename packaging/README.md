# Dragonfly Reverb for MPC OS

An unofficial port; not affiliated with or endorsed by the Dragonfly Reverb authors or by Akai Professional.

Four reverbs from Dragonfly Reverb 3.2.10 (Michael Willis, Rob van den Berg), ported as native insert effects,
each with a touchscreen page modelled on the original plugin's, Q-Link mapping and its presets:

| Folder | Plugin (manufacturer "Dragonfly") | Presets |
|---|---|---|
| dragonfly.vst.Hall | Hall | 25, in 5 banks |
| dragonfly.vst.Room | Room | 25, in 5 banks |
| dragonfly.vst.Plate | Plate | 8, plus 3 reverb types |
| dragonfly.vst.EarlyReflections | Early Refl | 8 reflection types |

Version @VERSION@.

## Install
The plugins work on **Gen 1 Akai MPC and Akai Force** units (Force, MPC Live, Live II, One, X, Key 61) with SSH
access through custom firmware. They are registered with `vstscanner.sh` from the Force VST distribution; copy it
along with the plugins.

The steps below are written for the **Akai Force with MockbaMod**, which mounts its memory card at
`/media/662522`. On other custom firmware (for example Hakai), or without that `662522` card, use
"Other firmware" below instead.

### Akai Force with MockbaMod (card at /media/662522)
1. Copy the eight folders from this `Dragonfly Reverb for MPC OS` folder into the `Synths` folder on the memory
   card, next to `vstscanner.sh`: the four `dragonfly.vst.*` folders (the plugins) and the four
   `Dragonfly - VST - ...` folders (their pages). The page folders must sit directly in `Synths`, not inside
   another folder.
2. Run the scanner: `ssh ip-of-force 'sh /media/662522/Synths/vstscanner.sh'`
3. MPC restarts. The plugins are under the VST category, manufacturer "Dragonfly".

### Other firmware, or no 662522 card
The scanner needs two paths: the folder holding the plugins, and MPC's settings file. Find yours first.

1. SSH into the device and find where to put the plugins:
   - a memory card: `ls /media` lists the mounted cards (the internal drive is `az01-internal`); or
   - the internal storage: `/sdcard` (the plugins can run from there).
   Below, `<dir>` means that location plus `/Synths`, e.g. `/media/MYCARD/Synths` or `/sdcard/Synths`.
2. Find the settings file: `find / -name MPC.settings 2>/dev/null`. It is usually
   `/media/az01-internal/Settings/MPC/MPC.settings`. Below, `<settings>` means that path. Back it up:
   `cp "<settings>" "<settings>.bak"`
3. Create `<dir>` and copy `vstscanner.sh` and the eight folders into it (as in step 1 above).
4. Run the scanner with both paths: `sh <dir>/vstscanner.sh <dir> <settings>`
   (Without them it assumes MockbaMod's `/data/Settings/MPC/MPC.settings` and stops if that isn't there.)
5. MPC restarts and the plugins appear under VST. If a plugin shows MPC's plain parameter list instead of its own
   page, MPC doesn't look for pages in `<dir>`: check `grep SynthContentLocations "<settings>"` and copy the four
   `Dragonfly - VST - ...` folders into one of the folders it lists (usually `/sdcard/Synths`).

To restore the old plugin list, stop MPC (`systemctl stop acvs`), copy the backup back, and start it
(`systemctl start acvs`).

To update, replace both kinds of folder and run the scanner again; projects keep their settings.
**From 1.1.x:** the page folders were renamed (e.g. `Dragonfly - VST - Dragonfly Hall` is now
`Dragonfly - VST - Hall`), so delete the four old `Dragonfly - VST - Dragonfly ...` folders from `Synths`. To remove a
plugin, delete its `dragonfly.vst.*` folder and its page folder, then run the scanner.

MockbaMod: if a plugin shows MPC's plain parameter list instead of its own page, the card's `Synths` folder isn't one
of MPC's content locations: check `grep SynthContentLocations /data/Settings/MPC/MPC.settings`, or copy the
`Dragonfly - VST - ...` folders into the internal Synths folder instead (other firmware: step 5 above).

## Notes
- Hall and Room have two Q-Link banks, MAIN and EQ (Hall) / TONE (Room), switched by the tab at the bottom of the
  screen. Presets: tap a bank tab, then a preset, as in the original plugins.
- The spectrogram (Hall, Room, Plate) shows the selected preset's reverb, computed as the original does. The
  original redraws it as you turn knobs; here it changes with the preset only.
- The scanner rebuilds MPC's whole plugin list from what it finds under `Synths`, so keep every plugin you use there.
- CPU: Hall is the heaviest of the four. Start with one instance and check it plays cleanly before stacking more.
- The C++ runtime is built in; the plugins need nothing from the device but libc.

## Licence and source
GPL-3.0-or-later (`LICENSE`), as Dragonfly Reverb (Copyright (c) 2018-2019 Michael Willis, Rob van den Berg)
and freeverb3 (Copyright (C) 2006-2018 Teru Kamogashira and others). `NOTICE.md` lists every component with its
authors and licence; `licenses/` holds the licence texts. Source code: @SOURCE@
Upstream: https://github.com/michaelwillis/dragonfly-reverb
