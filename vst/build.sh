#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
# Build the Dragonfly Reverb plugins as MPC OS VST2 effects, for Gen1 (armv7) and Gen2 (aarch64) devices.
#   vst/build.sh [hall room plate early]        (default: all four)
#   ARCHS="armv7 aarch64" (default) | ARCHS=armv7 | ARCHS=aarch64
# Per plugin, in vst/<plugin>/build/:
#   <so>                     Gen1 (armv7: Force, Live, Live II, One, X, Key 61; RK3288 Cortex-A17)
#   aarch64/<so>             Gen2 (aarch64: Live III, One G2, Key G2)
#   skin/Dragonfly - VST - <name>/   the page (the same for both)
#   pluginlist-entry.xml     the <PLUGIN> line for MPC.settings' plugin list
# Needs: a checkout of mpc-vst-plugins in $MPC_VST (default ../mpc-vst-plugins), python3 + Pillow + numpy, a host
# gcc/g++, and one cross toolchain:
#   TOOLCHAIN=zig      zig c++ (pip install ziglang; no Docker needed). glibc 2.36 symbols at most.
#   TOOLCHAIN=docker   arm32v7/gcc:12 and arm64v8/gcc:12-bookworm under QEMU (mpc-vst-plugins' standard; glibc 2.36)
# Default: docker if it's installed, else zig.
#
# Compiler flags (docs/SOUND.md has the measurements behind them):
#   Upstream's DSP (DSP.cpp, freeverb3) and the glue get upstream's own optimisation flags, -O3 -ffast-math (DPF's
#   Makefile.base.mk), so the reverbs are built exactly as upstream builds them: fast-math decides, for example, some
#   of Hall's diffuser lengths (zrev2.cpp: a division done as a multiply by the reciprocal, then rounded to an
#   integer and the next prime). -ffp-contract=off keeps a*b+c as two roundings, as upstream's x86 build does (no FMA),
#   so ARM output stays next to the desktop original. The VST wrapper (ours) stays strict IEEE (-O2).
#   Gen1: NEON + VFPv4 (-mcpu=cortex_a17): every Gen1 MPC/Force is an RK3288 (4x Cortex-A17), whose MPC OS userland is
#   itself built for NEON/VFPv4. Gen2: generic armv8-a (NEON is part of the base ISA).
#   Neither build links crtfastmath (it would change MPC's FPU mode when the plugin loads); vst/effect_test.c checks.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
MPC_VST="${MPC_VST:-$ROOT/../mpc-vst-plugins}"
[ -f "$MPC_VST/tools/gen_vst.py" ] || { echo "MPC_VST=$MPC_VST is not an mpc-vst-plugins checkout" >&2; exit 1; }
if [ -z "${TOOLCHAIN:-}" ]; then command -v docker >/dev/null && TOOLCHAIN=docker || TOOLCHAIN=zig; fi
PLUGINS="${*:-hall room plate early}"
ARCHS="${ARCHS:-armv7 aarch64}"

FV="allpass biquad comb delay delayline earlyref efilter nrev nrevb progenitor progenitor2 revbase slot strev utils zrev zrev2"
FV_SRC=""; for f in $FV; do FV_SRC="$FV_SRC src/dragonfly/common/freeverb/$f.cpp"; done
CXXFLAGS_COMMON="-std=gnu++11 -DLIBFV3_FLOAT -fPIC -fvisibility=hidden -ffunction-sections -fdata-sections -w -Wno-deprecated -Isrc/shim -Isrc/dragonfly/common -Ivst -I$MPC_VST/wrapper"
OPT_WRAP="-O2 -ffp-contract=off"                     # vst/dragonfly_vst.cpp (ours): strict IEEE
OPT_DSP="-O3 -ffast-math -ffp-contract=off"          # upstream's DSP: upstream's -O3 -ffast-math (see above)
LDFLAGS_SO="-shared -Wl,--no-undefined -Wl,--version-script=vst/exports.map -Wl,--gc-sections"
# zig targets (clang CPU names) and the gcc equivalents for the Docker images
ZIG_armv7="-target arm-linux-gnueabihf.2.36 -mcpu=cortex_a17 -mthumb"
ZIG_aarch64="-target aarch64-linux-gnu.2.36 -mcpu=generic"
GCC_armv7="-march=armv7-a -mtune=cortex-a17 -mfpu=neon-vfpv4 -mfloat-abi=hard -mthumb"
GCC_aarch64="-march=armv8-a"
IMG_armv7="arm32v7/gcc:12";              PLAT_armv7="linux/arm/v7"
IMG_aarch64="arm64v8/gcc:12-bookworm";   PLAT_aarch64="linux/arm64"
GLIBC_MAX=GLIBC_2.36                    # Gen1 MPC OS 3.x has 2.39 (2.34 already means "3.x only"); Gen2 has 2.39

jget() { python3 -c "import json,sys; v=json.load(open(sys.argv[1]))[sys.argv[2]]; print(' '.join(v) if isinstance(v,list) else v)" "$1" "$2"; }

mkdir -p vst/.host
g++ -O2 -w -I"$MPC_VST/tools/vendor/force-shadow/tools" -x c -o vst/.host/shadow_art "$MPC_VST/tools/shadow_art.c" -lm

# compile_so <arch> <out .so> <defines+includes> <sources...>: the wrapper with OPT_WRAP, everything else with OPT_DSP
compile_so() {
  local A="$1" OUT="$2" INCS="$3"; shift 3
  local OBJ="$(dirname "$OUT")/obj"; rm -rf "$OBJ"; mkdir -p "$OBJ"
  local cmds="" objs="" s o opt
  for s in "$@"; do
    o="$OBJ/$(basename "$s" .cpp).o"; objs="$objs $o"
    [ "$s" = vst/dragonfly_vst.cpp ] && opt="$OPT_WRAP" || opt="$OPT_DSP"
    case "$TOOLCHAIN" in
      zig) local zt="ZIG_$A"; ${ZIG:-python3 -m ziglang} c++ ${!zt} $opt $CXXFLAGS_COMMON $INCS -c "$s" -o "$o" & ;;
      docker) local gt="GCC_$A"; cmds="$cmds g++ ${!gt} $opt ${CXXFLAGS_COMMON//$MPC_VST//mv} $INCS -c '$s' -o '$o';" ;;
    esac
  done
  case "$TOOLCHAIN" in
    zig)
      wait
      local zt="ZIG_$A"
      ${ZIG:-python3 -m ziglang} c++ ${!zt} $LDFLAGS_SO -Wl,-s $objs -o "$OUT" ;;
    docker)
      local img="IMG_$A" plat="PLAT_$A"
      docker run --rm --platform "${!plat}" -u "$(id -u):$(id -g)" -v "$ROOT":/b -v "$MPC_VST":/mv:ro -w /b "${!img}" \
        bash -euc "$cmds g++ $LDFLAGS_SO $objs -static-libstdc++ -static-libgcc -o '$OUT' && strip '$OUT'" ;;
    *) echo "TOOLCHAIN must be docker or zig" >&2; exit 1 ;;
  esac
  rm -rf "$OBJ"
}

# check_so <arch> <.so>: one export, the right machine and FPU, glibc <= GLIBC_MAX, no C++ runtime to find on the device
check_so() {
  local A="$1" SO="$2"
  local EXP GLIBC NEEDED MACH
  EXP=$(readelf --dyn-syms -W "$SO" | awk '$5=="GLOBAL" && $7!="UND" && $4!="NOTYPE"{print $8}' | tr '\n' ' ')
  GLIBC=$(readelf -V "$SO" | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1)
  NEEDED=$(readelf -d "$SO" | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p' | tr '\n' ' ')
  MACH=$(readelf -h "$SO" | sed -n 's/^ *Machine: *//p')
  echo "   [$A] $(file -b "$SO" | cut -d, -f1-3)"
  echo "   exported: $EXP"
  echo "   needed:   $NEEDED"
  echo "   highest glibc: $GLIBC (device has 2.39)"
  [ "$EXP" = "VSTPluginMain " ] || { echo "error: unexpected exports" >&2; exit 1; }
  case "$NEEDED" in *libstdc++*|*libc++*) echo "error: C++ runtime must be linked statically" >&2; exit 1 ;; esac
  [ "$(printf '%s\n%s\n' "$GLIBC" $GLIBC_MAX | sort -V | tail -1)" = $GLIBC_MAX ] || { echo "error: needs glibc > ${GLIBC_MAX#GLIBC_}" >&2; exit 1; }
  case "$A" in
    armv7)
      [ "$MACH" = ARM ] || { echo "error: $SO is $MACH, not ARM" >&2; exit 1; }
      readelf -A "$SO" | grep -q 'Tag_ABI_VFP_args: VFP registers' || { echo "error: not hard-float" >&2; exit 1; }
      readelf -A "$SO" | grep -q 'Tag_Advanced_SIMD_arch: NEON' || { echo "error: built without NEON" >&2; exit 1; }
      echo "   fpu:      $(readelf -A "$SO" | sed -n 's/ *Tag_FP_arch: //p') + $(readelf -A "$SO" | sed -n 's/ *Tag_Advanced_SIMD_arch: //p')" ;;
    aarch64)
      [ "$MACH" = AArch64 ] || { echo "error: $SO is $MACH, not AArch64" >&2; exit 1; } ;;
  esac
}

for P in $PLUGINS; do
  CFG="vst/$P/vst.json"
  UP=$(jget "$CFG" upstream); SO=$(jget "$CFG" so); NAME=$(jget "$CFG" name)
  DEFS=""; for d in $(jget "$CFG" glue_defines); do DEFS="$DEFS -D$d"; done
  INC="-Isrc/dragonfly/plugins/$UP"    # first: this plugin's DSP.hpp / DistrhoPluginInfo.h
  B="vst/$P/build"; mkdir -p "$B"
  echo "== $NAME ($UP)"

  # 1. params.json, straight from upstream's DistrhoPluginInfo.h (host build of the same glue)
  g++ -O1 -w -std=gnu++11 -DLIBFV3_FLOAT $DEFS $INC -Isrc/shim -Isrc/dragonfly/common -Ivst \
      vst/dump_params.cpp vst/dsp_glue.cpp "src/dragonfly/plugins/$UP/DSP.cpp" $FV_SRC -lm -o "vst/.host/dump_$P"
  "vst/.host/dump_$P" "$NAME" > "vst/$P/params.json"
  python3 vst/gen_formats.py "src/dragonfly/plugins/$UP" "$B/formats.h"
  if python3 -c "import json,sys; sys.path.insert(0,'vst'); import df_skin; sys.exit(0 if df_skin.DESIGNS['$P'].get('spectrogram') is not None else 1)"; then
    # the original's spectrogram, rendered per preset (df_paint.py turns these into pictures)
    g++ -O2 -w -std=gnu++11 -DLIBFV3_FLOAT $DEFS $INC -Isrc/shim -Isrc/dragonfly/common -Ivst \
        vst/spectrogram_dump.cpp vst/dsp_glue.cpp "src/dragonfly/plugins/$UP/DSP.cpp" $FV_SRC -lm -o "vst/.host/spectro_$P"
    rm -rf "$B/spectro"; mkdir -p "$B/spectro"; "vst/.host/spectro_$P" "$B/spectro"
  fi

  # 2. the page layout (from vst/df_skin.py's spec), then params.h, skin and plugin-list entry
  #    (mpc-vst-plugins' generator), then the Dragonfly look painted over the kit's images, and the entry
  #    made an effect. One page for both architectures.
  rm -rf "$B/skin"      # the page folder is named after the plugin: never keep one from an older name
  python3 vst/df_skin.py layout "$P"
  SHADOW_ART="$ROOT/vst/.host/shadow_art" python3 "$MPC_VST/tools/gen_vst.py" "$CFG"
  python3 vst/df_skin.py paint "$P"
  sed -i -e 's/category="Synth"/category="Effect"/' -e 's/isInstrument="1"/isInstrument="0"/' \
         -e 's/numInputs="0"/numInputs="2"/' "$B/pluginlist-entry.xml"

  # 3. the plugin, once per architecture
  SRCS="vst/dragonfly_vst.cpp vst/dsp_glue.cpp src/dragonfly/plugins/$UP/DSP.cpp $FV_SRC"
  for A in $ARCHS; do
    case "$A" in
      armv7) OUT="$B/$SO" ;;
      aarch64) mkdir -p "$B/aarch64"; OUT="$B/aarch64/$SO" ;;
      *) echo "unknown arch $A (armv7, aarch64)" >&2; exit 1 ;;
    esac
    compile_so "$A" "$OUT" "$DEFS $INC -I$B" $SRCS
    # 4. checks
    check_so "$A" "$OUT"
  done
done
