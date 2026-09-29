# Vendored upstream source

`src/dragonfly/` is a partial copy of **Dragonfly Reverb** (Michael Willis, Rob van den Berg; GPL-3.0-or-later),
https://github.com/michaelwillis/dragonfly-reverb, tag `3.2.10`, commit `772cb2a7e6244aef7cd68188392ef6924a479dcc`.

Copied: `common/freeverb/` (freeverb3, GPL-2.0-or-later; its own AUTHORS/COPYING inside), `common/fv3_config.h`,
`common/AbstractDSP.hpp`, `common/Param.hpp`, `common/DragonflyVersion.h`, and for each of the four plugins
`DSP.cpp`, `DSP.hpp`, `DistrhoPluginInfo.h`. Nothing else: no DPF (the VST2 layer is `vst/dragonfly_vst.cpp`), no
desktop UI (the MPC page is a skin), no kiss_fft (only the UI's spectrogram used it).

Only the freeverb3 files upstream's own Makefile compiles are built (`vst/build.sh`'s `FV` list); the rest are
kept so a re-vendor is a plain copy.

`src/shim/` replaces the three DPF headers the DSP includes: `DistrhoPlugin.hpp` (`d_isNotEqual`),
`extra/ScopedDenormalDisable.hpp` (flush-to-zero; ARM FPSCR.FZ on the device), `Artwork.hpp` (UI size constants).

Also copied, as reference only (never compiled): each plugin's `UI.cpp`, as `UI.cpp.ref` -- the MPC pages take
their layout, value formats and behaviour from it (`vst/df_skin.py`, `vst/gen_formats.py`).

## Local changes
- `plugins/room-reverb/DSP.cpp` (2026-09-25; marked in the file), `DragonflyReverbDSP::mute()`: also mutes the four input filters
  (`input_lpf_0/1`, `input_hpf_0/1`). Upstream leaves their state, so after a host resume a -70 dB residue of
  the old signal could still come out. Found by `vst/effect_test.c`.

## Artwork (MPC pages)
`src/dragonfly/artwork/`: upstream's `NotoSans-Regular.ttf` (SIL OFL 1.1, `OFL.txt` beside it) and, per plugin,
`knob.png`, `background.png`, `tab_on.png` and `tab_off.png` from `plugins/<plugin>/artwork/` (GPL-3.0-or-later,
as the rest of Dragonfly Reverb). `vst/df_skin.py` / `vst/df_paint.py` sample the colours from them,
crop the logo + title from `background.png`, and redraw the knob, faders and panels in the same style at the MPC's
size; baked text uses NotoSans, as upstream's UI does.
