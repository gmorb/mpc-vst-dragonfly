# Vendored upstream source

`src/dragonfly/` is a partial copy of **Dragonfly Reverb** (Michael Willis, Rob van den Berg; GPL-3.0-or-later),
https://github.com/michaelwillis/dragonfly-reverb, tag `3.2.10`, commit `772cb2a7e6244aef7cd68188392ef6924a479dcc`.

Copied: `common/freeverb/` (freeverb3, GPL; its own AUTHORS/COPYING inside), `common/fv3_config.h`,
`common/AbstractDSP.hpp`, `common/Param.hpp`, `common/DragonflyVersion.h`, and for each of the four plugins
`DSP.cpp`, `DSP.hpp`, `DistrhoPluginInfo.h`. Nothing else: no DPF (the VST2 layer is `vst/dragonfly_vst.cpp`), no
desktop UI (the MPC page is a skin), no kiss_fft (only the UI's spectrogram used it).

Only the freeverb3 files upstream's own Makefile compiles are built (`vst/build.sh`'s `FV` list); the rest are
kept so a re-vendor is a plain copy.

`src/shim/` replaces the three DPF headers the DSP includes: `DistrhoPlugin.hpp` (`d_isNotEqual`),
`extra/ScopedDenormalDisable.hpp` (flush-to-zero; ARM FPSCR.FZ on the device), `Artwork.hpp` (UI size constants).

## Local changes
- `plugins/room-reverb/DSP.cpp`, `DragonflyReverbDSP::mute()`: also mutes the four input filters
  (`input_lpf_0/1`, `input_hpf_0/1`). Upstream leaves their state, so after a host resume a -70 dB residue of
  the old signal could still come out. Found by `vst/effect_test.c`.

## Artwork (MPC pages)
`src/dragonfly/artwork/`: upstream's `NotoSans-Regular.ttf` (SIL OFL) and, per plugin, `knob.png` and
`background.png` from `plugins/<plugin>/artwork/`. `vst/df_skin.py` / `vst/df_paint.py` sample the colours from them,
crop the logo + title from `background.png`, and redraw the knob, faders and panels in the same style at the MPC's
size; baked text uses NotoSans, as upstream's UI does.
