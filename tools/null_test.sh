#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
# Sound check: do the device builds sound like the original Dragonfly Reverb? (run vst/build.sh first)
#   tools/null_test.sh [hall room plate early]
# Renders a fixed test signal through every preset (vst/render.c: noise burst, impulse, 6 s of tail, 48 kHz) of:
#   ref     the same sources built for this PC with upstream's own x86 flags (DPF's Makefile.base.mk:
#           -O3 -ffast-math -mtune=generic -msse -msse2 -mfpmath=sse), through the same VST wrapper;
#   armv7   the Gen1 device .so under qemu-arm      (apt: qemu-user libc6-armhf-cross)
#   aarch64 the Gen2 device .so under qemu-aarch64  (apt: qemu-user libc6-arm64-cross)
# and null-tests them (tools/null_compare.py). Limits:
#   device vs ref    -40 dB worst: catches a structurally different reverb (v1.2.0's strict-IEEE Hall built some
#                    diffusers one prime longer than upstream: -15.6 dB). What remains is float rounding and libm:
#                    upstream's own x86 binary differs from itself by up to -48 dB between a CPU with FMA and one
#                    without, because glibc picks other exp/sin routines (docs/SOUND.md).
#   armv7 vs aarch64 -80 dB worst: Gen1 and Gen2 sound the same (projects move between them).
# If Ubuntu/Debian's dragonfly-reverb-vst package (upstream's own build) can be downloaded with apt, or UPSTREAM_VST
# names a folder holding its Dragonfly*-vst.so, it also checks that ref is BIT-IDENTICAL to upstream's binary in
# upstream's default state (its VST has no preset parameter, so only the default preset can be compared).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
MPC_VST="${MPC_VST:-$ROOT/../mpc-vst-plugins}"
PLUGINS="${*:-hall room plate early}"
ZIG="${ZIG:-python3 -m ziglang}"
T=vst/.null; rm -rf $T; mkdir -p $T/bin
FV="allpass biquad comb delay delayline earlyref efilter nrev nrevb progenitor progenitor2 revbase slot strev utils zrev zrev2"
FV_SRC=""; for f in $FV; do FV_SRC="$FV_SRC src/dragonfly/common/freeverb/$f.cpp"; done
jget() { python3 -c "import json,sys; v=json.load(open(sys.argv[1]))[sys.argv[2]]; print(' '.join(v) if isinstance(v,list) else v)" "$1" "$2"; }

gcc -O1 vst/render.c -o $T/bin/render -ldl
ARM=0; A64=0
command -v qemu-arm >/dev/null && [ -d /usr/arm-linux-gnueabihf/lib ] && ARM=1 && \
  $ZIG cc -target arm-linux-gnueabihf.2.36 -O1 vst/render.c -o $T/bin/render_arm -ldl 2>/dev/null
command -v qemu-aarch64 >/dev/null && [ -d /usr/aarch64-linux-gnu/lib ] && A64=1 && \
  $ZIG cc -target aarch64-linux-gnu.2.36 -O1 vst/render.c -o $T/bin/render_a64 -ldl 2>/dev/null

UP="${UPSTREAM_VST:-}"
if [ -z "$UP" ] && command -v apt-get >/dev/null; then
  if (cd $T && apt-get download dragonfly-reverb-vst >/dev/null 2>&1); then
    dpkg-deb -x $T/dragonfly-reverb-vst_*.deb $T/upstream && UP=$T/upstream/usr/lib/lxvst
  fi
fi
[ -n "$UP" ] && echo "upstream's own build: $UP" || echo "upstream's own build: not available (apt package dragonfly-reverb-vst); skipping that check"
declare -A UPSO=([hall]=DragonflyHallReverb [room]=DragonflyRoomReverb [plate]=DragonflyPlateReverb [early]=DragonflyEarlyReflections)

rc=0
for P in $PLUGINS; do
  CFG="vst/$P/vst.json"; UPDIR=$(jget "$CFG" upstream); SO=$(jget "$CFG" so)
  DEFS=""; for d in $(jget "$CFG" glue_defines); do DEFS="$DEFS -D$d"; done
  echo "===== $P"
  g++ -O3 -ffast-math -mtune=generic -msse -msse2 -mfpmath=sse -std=gnu++11 -DLIBFV3_FLOAT -fPIC -w -shared $DEFS \
      -Isrc/dragonfly/plugins/$UPDIR -Isrc/shim -Isrc/dragonfly/common -Ivst -I"$MPC_VST/wrapper" -Ivst/$P/build \
      vst/dragonfly_vst.cpp vst/dsp_glue.cpp src/dragonfly/plugins/$UPDIR/DSP.cpp $FV_SRC -o $T/ref_$P.so -lm
  mkdir -p $T/ref/$P; $T/bin/render ./$T/ref_$P.so $T/ref/$P >/dev/null
  if [ $ARM = 1 ]; then
    mkdir -p $T/armv7/$P
    QEMU_LD_PREFIX=/usr/arm-linux-gnueabihf qemu-arm $T/bin/render_arm vst/$P/build/$SO $T/armv7/$P >/dev/null
    python3 tools/null_compare.py $T/armv7/$P $T/ref/$P -40 "$P Gen1 (armv7) vs upstream-flags reference" || rc=1
  fi
  if [ $A64 = 1 ] && [ -f vst/$P/build/aarch64/$SO ]; then
    mkdir -p $T/aarch64/$P
    QEMU_LD_PREFIX=/usr/aarch64-linux-gnu qemu-aarch64 $T/bin/render_a64 vst/$P/build/aarch64/$SO $T/aarch64/$P >/dev/null
    python3 tools/null_compare.py $T/aarch64/$P $T/ref/$P -40 "$P Gen2 (aarch64) vs upstream-flags reference" || rc=1
    [ $ARM = 1 ] && { python3 tools/null_compare.py $T/aarch64/$P $T/armv7/$P -80 "$P Gen2 vs Gen1" || rc=1; }
  fi
  if [ -n "$UP" ] && [ -f "$UP/${UPSO[$P]}-vst.so" ]; then
    k=$(printf '%02d' "$(python3 -c "import json;d=json.load(open('vst/$P/params.json'));print([p for p in d['params'] if p['key'] in ('preset','program')][0]['default'])")")
    mkdir -p $T/up/$P $T/refdef/$P
    $T/bin/render "$UP/${UPSO[$P]}-vst.so" $T/up/$P >/dev/null
    cp $T/ref/$P/$k.f32 $T/refdef/$P/00.f32
    python3 tools/null_compare.py $T/refdef/$P $T/up/$P -999 "$P reference vs upstream's own binary, default preset ($k)" || rc=1
  fi
done
exit $rc
