# Sound: how close is the port to the original?

Measured offline on 2026-10-28 (x86_64 host, the ARM builds under qemu-user). Re-run with `tools/null_test.sh`.

## Short answer
The DSP is upstream's code, unchanged except one documented fix (`src/VENDORED.md`; it only acts when the host
resumes the plugin), compiled with upstream's own flags. Against upstream, every preset of all four reverbs on both
Gen1 and Gen2 differs only by float rounding and libm, at -48 dB or lower (worst preset per plugin; median -61 dB or
lower), which is the same as upstream's own binary differs from itself between two PCs. Gen1 and Gen2 sound the same
(-98 dB or lower against each other).

## Method
`vst/render.c` loads a plugin as MPC does (VST2, 48 kHz, 256-frame blocks), picks each preset on a fresh instance and
renders a fixed signal: 0.5 s of white noise, 0.5 s of silence, an impulse, then silence to 6 s (the whole tail). Two
renders are subtracted; the result is the residual's RMS relative to the signal's (a "null test"): -20 dB is an
audibly different reverb, -60 dB is far below the reverb's own noise-like modulation, -100 dB is rounding.

Builds compared:

| Name | What |
|---|---|
| **upstream** | Ubuntu 24.04's `dragonfly-reverb-vst` 3.2.10-3build1: upstream's DPF VST2, built from upstream's tag with upstream's Makefiles (a build of upstream's 3.2.10 tag here gives the same output) |
| **reference** | this repo's sources built for x86_64 with DPF's flags (`-O3 -ffast-math -mtune=generic -msse -msse2 -mfpmath=sse`), through this repo's VST wrapper |
| **1.2.0** | the published 1.2.0 Gen1 `.so` (rebuilt here byte-identical): strict IEEE `-O2`, VFPv3-D16, no NEON |
| **1.3.0 Gen1 / Gen2** | this release: DSP `-O3 -ffast-math -ffp-contract=off`; Gen1 `-mcpu=cortex_a17` (NEON, VFPv4), Gen2 armv8-a |

Upstream's VST has no preset parameter (its presets are in its GUI), so it can only be compared in its default state:
there, **reference = upstream, bit for bit, for all four plugins.** The VST wrapper and the reference's flags are
therefore transparent, and the reference stands in for upstream on every preset.

## Results (worst preset / median, dB)

| | Hall (25) | Room (25) | Plate (8) | Early Refl (8) |
|---|---|---|---|---|
| 1.2.0 vs reference | **-15.6** / -59.0 | **-28.4** / -109.3 | -130.0 / -137.9 | -102.6 / -104.6 |
| 1.3.0 Gen1 vs reference | -48.3 / -61.4 | -108.0 / -109.3 | -129.4 / -138.0 | -101.3 / -103.6 |
| 1.3.0 Gen2 vs reference | -48.3 / -61.4 | -108.8 / -109.4 | -129.7 / -137.9 | -101.1 / -103.7 |
| 1.3.0 Gen1 vs reference on a CPU without FMA | -97.1 / -103.5 | -81.9 / -99.9 | -91.9 / -137.4 | -101.3 / -103.6 |
| reference: FMA CPU vs no FMA (upstream vs itself) | -48.3 / -61.4 | -81.9 / -99.9 | -91.9 / -136.8 | -147.7 / -149.2 |
| 1.3.0 Gen2 vs Gen1 | -97.8 / -103.8 | -109.8 / -110.4 | -139.4 / -143.7 | -100.5 / -103.1 |

"CPU without FMA": the reference run under `qemu-x86_64 -cpu Nehalem`. x86 glibc chooses its `exp`, `sincos`, `tan`
routines by CPU, so upstream's own Linux binary renders Hall differently (-48 dB) on a recent PC and an older one.
That, not the port, is where Hall's remaining -48 dB comes from: on the non-FMA PC the ARM builds match to -97 dB.

## Why 1.2.0 differed, and the fix
Fast-math is part of how upstream builds Dragonfly (DPF's `Makefile.base.mk`: `-O3 -ffast-math`, on every platform).
Two of the reverb engines turn a float into a delay length:

- Hall, `zrev2.cpp` (input diffusers): `totalFactor = getTotalFactorFs() / 34125`, then `p_(length, totalFactor)` =
  `(long)(length * totalFactor)`, rounded up to the next prime.
- Room, `progenitor2.cpp` (late reverb): the same pattern.

With `-ffast-math` (`-freciprocal-math`) the division becomes a multiply by `1/34125`, one ulp away. For some sizes
the product then lands on the other side of an integer, and the diffuser gets the next prime: 1.2.0's Hall built
right-channel diffusers of 131 and 193 samples where upstream builds 127 and 191 (5 of 25 Hall presets; 3 of 25 Room
presets). Same algorithm, slightly different room: audibly the same kind of reverb, but not the original. Found by
compiling one file at a time with `-freciprocal-math` (only `zrev2.cpp` changes Hall; only `progenitor2.cpp` changes
Room). 1.3.0 compiles the DSP with upstream's flags, so it computes upstream's lengths.

`-ffp-contract=off`: fast-math on ARM would also fuse `a*b+c` into one FMA instruction; upstream's x86 build has no
FMA (`-msse2`). Fused: Hall Gen1 vs the no-FMA reference -72.3 dB worst; unfused: -97.1 dB. Kept unfused.

The VST wrapper (`vst/dragonfly_vst.cpp`, ours) stays strict IEEE: it parses saved state, where fast-math's
"no NaN" assumption has no business. `vst/effect_test.c` checks that loading the plugin does not change the host's
FPU mode (gcc can link `crtfastmath.o`, which sets flush-to-zero for the whole MPC process; neither build does).

## Things that are not differences
- **Room and libc's `rand()`.** freeverb3's noise modulators (`efilter_t.hpp`) use `std::rand()`, one process-wide
  generator. Room's exact output therefore depends on everything else in the process that called `rand()` first, in
  upstream on a desktop as on MPC: no host plays Room's tail bit-identically twice. `vst/render.c` reseeds (`srand(1)`,
  a fresh process's state) before each instance so renders can be compared.
- **The Room `mute()` fix** only runs on a host resume; a fresh instance is unaffected (bit-identical above).

## CPU (Gen1 NEON + upstream flags)
Executed instructions per 256-frame block (qemu 8.2 `libinsn` plugin, average of presets 0, 2 and 5). A proxy: not
cycles, and not measured on a device yet (kit `tools/bench.sh`).

| | Hall | Room | Plate | Early Refl |
|---|---|---|---|---|
| 1.2.0 Gen1 | 1,248,530 | 1,239,461 | 203,159 | 178,002 |
| 1.3.0 Gen1 | 1,134,786 (-9%) | 1,116,833 (-10%) | 212,944 (+5%) | 165,206 (-7%) |
| 1.3.0 Gen2 | 786,762 | 856,646 | 178,616 | 146,153 |

Gen2 also runs on faster cores (Cortex-A76 at 2.4 GHz on a Live III vs Cortex-A17 at 1.8 GHz), and its denormals are
flushed like Gen1's: the DSP's `ScopedDenormalDisable` sets FPCR.FZ on aarch64 (`src/shim/extra/`).
