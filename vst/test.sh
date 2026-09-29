#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
# Offline tests for the Dragonfly MPC plugins (run vst/build.sh first; it makes each plugin's params.h).
#   vst/test.sh [hall room plate early]
# 1. PC: builds each plugin for this machine under AddressSanitizer + UBSan and runs vst/effect_test.c on it.
# 2. ARM: if qemu-arm and an armhf glibc are installed (apt: qemu-user libc6-armhf-cross), builds
#    effect_test for armhf and runs it on the REAL device .so from vst/<p>/build/ under emulation.
set -euo pipefail
cd "$(dirname "$0")/.."
MPC_VST="${MPC_VST:-$PWD/../mpc-vst-plugins}"
PLUGINS="${*:-hall room plate early}"
FV="allpass biquad comb delay delayline earlyref efilter nrev nrevb progenitor progenitor2 revbase slot strev utils zrev zrev2"
FV_SRC=""; for f in $FV; do FV_SRC="$FV_SRC src/dragonfly/common/freeverb/$f.cpp"; done
jget() { python3 -c "import json,sys; v=json.load(open(sys.argv[1]))[sys.argv[2]]; print(' '.join(v) if isinstance(v,list) else v)" "$1" "$2"; }
T=vst/.test; mkdir -p $T
SAN="-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=undefined"
gcc -O1 -g $SAN vst/effect_test.c -o $T/effect_test -ldl -lm
ARM=0
if command -v qemu-arm >/dev/null && [ -d /usr/arm-linux-gnueabihf/lib ]; then
  ARM=1
  ${ZIG:-python3 -m ziglang} cc -target arm-linux-gnueabihf.2.36 -mcpu=generic+v7a+vfp3d16-d32-neon -O1 \
      vst/effect_test.c -o $T/effect_test_arm -ldl -lm 2>/dev/null
fi
rc=0
for P in $PLUGINS; do
  CFG="vst/$P/vst.json"; UP=$(jget "$CFG" upstream); SO=$(jget "$CFG" so)
  DEFS=""; for d in $(jget "$CFG" glue_defines); do DEFS="$DEFS -D$d"; done
  g++ -O1 -g $SAN -w -shared -fPIC -std=gnu++11 -DLIBFV3_FLOAT $DEFS -Isrc/dragonfly/plugins/$UP -Isrc/shim \
      -Isrc/dragonfly/common -Ivst -I"$MPC_VST/wrapper" -Ivst/$P/build \
      vst/dragonfly_vst.cpp vst/dsp_glue.cpp src/dragonfly/plugins/$UP/DSP.cpp $FV_SRC -o $T/$P.so -lm
  echo "===== $P: PC build, AddressSanitizer + UBSan"
  ASAN_OPTIONS=detect_leaks=1 $T/effect_test $T/$P.so > $T/$P.pc.log 2>&1 || rc=1
  grep -E "^(FAIL|----)|PASSED|FAILED|ERROR|runtime error" $T/$P.pc.log || true
  if [ $ARM = 1 ]; then
    echo "===== $P: device .so (armhf) under qemu-arm"
    QEMU_LD_PREFIX=/usr/arm-linux-gnueabihf qemu-arm $T/effect_test_arm vst/$P/build/$SO > $T/$P.arm.log 2>&1 || rc=1
    grep -E "^(FAIL|----)|PASSED|FAILED" $T/$P.arm.log || tail -5 $T/$P.arm.log
  fi
done
exit $rc
