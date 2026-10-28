# Changelog

## 1.3.0
**Gen2 builds**, and the reverbs now built as upstream builds them.

- **Gen2 (64-bit) MPCs**: every release now also has `<Name>-1.3.0-mpc-aarch64.zip` per plugin for the MPC Live III,
  One G2 and Key G2, next to the Gen1 `-mpc-armv7.zip`. Same plugin ids, uids, parameters and pages, so projects
  move between generations. The catalog lists both from the same entry.
- **Sound: matched to upstream's own builds.** Upstream compiles the DSP with `-O3 -ffast-math`; 1.2.0 used strict
  IEEE floats, which turned out to build a slightly different Hall and Room on some presets: Hall's input diffusers
  (`zrev2.cpp`) and Room's late reverb (`progenitor2.cpp`) compute delay lengths with a division that fast-math does
  as a multiply by the reciprocal, then round to an integer (and the next prime), so a one-ulp difference picks a
  different length (Hall 5 of 25 presets, Room 3 of 25; null test against upstream -15.6 and -28.4 dB). The DSP is
  now compiled with upstream's flags (the VST wrapper stays strict). Against a reference built from the same
  sources with upstream's x86 flags -- itself bit-identical to Ubuntu's `dragonfly-reverb-vst` 3.2.10 in each
  plugin's default state -- every preset of all four now nulls to between -48 and -129 dB (worst preset per plugin),
  the remainder being float rounding and libm (upstream's own binary differs from itself by up to -48 dB between an
  x86 CPU with FMA and one without). Gen1 and Gen2 null to -98 dB or better against each other. docs/SOUND.md.
- **Gen1: NEON + VFPv4** (`-mcpu=cortex_a17`; 1.2.0 was VFPv3-D16 without NEON). Every Gen1 device is an RK3288
  (Cortex-A17) whose MPC OS is itself built for NEON/VFPv4. Instructions per audio block under emulation, against
  1.2.0: Hall -9%, Room -10%, Early -7%, Plate +5% (the lightest of the four).
- New `tools/null_test.sh` (CI): null-tests both device builds, under qemu, against the upstream-flags reference
  and each other, and checks that reference against upstream's own binary when apt can fetch it. `vst/render.c`
  renders every preset; `vst/effect_test.c` also checks that loading and running a plugin leaves the host's FPU
  mode alone (no `crtfastmath`).
- Pages, presets and parameters unchanged (the pages are byte-identical to 1.2.0's, still generated with
  mpc-vst-plugins `c0394f0`). The catalog zips are packaged with mpc-vst-plugins `67413a5` (Gen2 packaging,
  current installer templates) and carry the correct licence, GPL-3.0-or-later.
- Catalog: each plugin is listed from its own repo (`gmorb/mpc-vst-dragonfly-hall`, `-room`, `-plate`,
  `-early-reflections`); the zips are built with that repo as `source_repo` (`CATALOG_OWNER`), and the same files go on
  this repo's release and on each per-plugin repo's. This repo is not listed itself. docs/CATALOG.md.
- Removed the 1.2 zips committed to the repo root (releases are the place for binaries).
- Tested: Akai Force (Gen1) and MPC Live III (Gen2), MPC OS 3.9.1 (`tested.json`).

## 1.2.0
The package is now called **Dragonfly Reverb for MPC OS**.

Also released for the [MPC OS Plugin Catalog](https://sd88me.github.io/mpc-vst-plugins/): one
`<Name>-1.2.0-mpc-armv7.zip` per plugin (installer, manifest, checksums), built with mpc-vst-plugins'
`release.py` and passing its `catalog_check.py`. Built with mpc-vst-plugins `c0394f0`.

The distribution zip is packaged in the Force VST plugins distribution layout: one self-contained folder per plugin
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
