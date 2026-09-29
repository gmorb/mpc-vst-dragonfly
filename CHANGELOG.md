# Changelog

## 1.2
The package is now called **Dragonfly Reverb for MPC OS**.

Packaged in the Force VST plugins distribution layout: one self-contained folder per plugin
(`Dragonfly - VST - Hall/` with `Hall.so`, `plugin-meta.xml`, `version.xml`, `Hall.json`, `Plugin Skins/` and its
licences), registered by the distribution's `vstscanner.sh`. From 1.1.x, delete the old `dragonfly.vst.*` and
`Dragonfly - VST - Dragonfly ...` folders before installing. Projects saved with 1.1.x reference the old plugin file
paths; check that they reopen with the plugins.

Every page rebuilt to match the original plugin's UI (upstream's UI.cpp positions and artwork):
- Layouts as the originals: Hall and Room with the bank tabs and preset list at the top, the modulation knobs top
  right, the level faders on the left, Size/Width over Predelay/Decay, the spectrogram in the middle, the EQ/tone
  panels on the right; Plate and Early Reflections as theirs.
- The spectrogram (Hall, Room, Plate), computed exactly as upstream's (a burst of white noise through the reverb,
  dry level off, a windowed FFT on log time and frequency axes) at build time, once per preset, with the plugin's
  own DSP; the page shows the current preset's. The original redraws it on every knob change; on MPC it follows
  the preset.
- Hall and Room presets work as in the original: pick a bank tab, then one of its five presets. Picking a bank
  loads the preset last picked in it (a new "Bank" parameter; projects keep their settings).
- Values read exactly as in the original ("6250 Hz", "0.3 X", "2.10 Hz", "17.0 ms", levels in whole %).
- Knobs turn 300 degrees, as upstream's; names above them in the original's NotoSans.
- The level faders are the original's tall sliders (each a stack of small square segments, since MPC needs
  square filmstrip frames).
- The 1.1.2 Q-Link panel highlights are gone. The Q-Link banks are unchanged (Hall MAIN/EQ, Room MAIN/TONE), and
  each keeps its region set to its own controls.
- Licensing: `NOTICE.md` lists every component (Dragonfly Reverb, freeverb3, Noto Sans, mpc-vst-plugins) with
  its authors and licence, and ships in the release with the licence texts (`licenses/`); Noto Sans' OFL beside
  the font; the port's own files carry SPDX licence headers; the modified upstream file is dated. The READMEs
  say this is an unofficial port.
- Short plugin names, so they fit MPC's insert slots: Hall, Room, Plate, Early Refl (the manufacturer line
  already says Dragonfly). The page folders are renamed with them (`Dragonfly - VST - Hall`, ...): delete the old
  `Dragonfly - VST - Dragonfly ...` folders when updating. Projects should still find the plugins: MPC matches
  them by file and ID, which are unchanged.

## 1.1.2
- Hall and Room: tapping the second page at the bottom of the screen (EQ / TONE) seemed to do nothing. Those
  are Q-Link banks on the same page, not separate screens. Each bank now highlights the panels its Q-Links
  control (brighter panel, accent border, a "Q-LINKS" tag), so switching visibly changes the page.
- The banks no longer overlap: Hall MAIN = levels, space and modulation; Hall EQ = the six EQ controls. Room
  MAIN = levels, space and modulation; Room TONE = the six tone controls. The preset is on every bank.
- Each bank's Q-Link region now matches the page layout (it still had the 1.0 layout's coordinates).

## 1.1.1
- Plate and Early Reflections: the Dry Level and Wet Level faders drew two misaligned half-images instead of
  one clean fader. Their filmstrips were taller than MPC can display (25088 px); they are now under its
  16384 px limit (83 frames), and the build refuses any image over that limit.

## 1.1.0
- Every page redesigned after the original plugin's UI: its logo and title, colours, knobs (light rim, coloured
  face, white pointer, min/max dots), black level faders with a coloured fill, and rounded panels.
- Much larger text: control names and values are about twice their previous on-screen size, and the lists and
  headings use Dragonfly's own NotoSans font.
- Hall and Room: the preset list opens grouped by bank, one column per bank, as in the original.
- Plate and Early Reflections: presets, reverb types and reflection types are lists right on the page.
- Distributed as a collection for `vstscanner.sh` (the Force VST distribution layout).
- Plate and Early Reflections have one parameter fewer (their list pop-up flag). Update the plugin together with
  its page; saved projects keep their settings.

## 1.0.0
- First release: Dragonfly Hall, Room, Plate and Early Reflections 3.2.10 as MPC OS VST2 insert effects.
- Room: fixed upstream's `mute()` leaving the input filters' state (a faint residue after a host resume).
