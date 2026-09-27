#!/usr/bin/env bash
# Build the Dragonfly Reverb plugins as MPC OS VST2 effects (armhf).
#   vst/build.sh [hall room plate early]        (default: all four)
# Per plugin, in vst/<plugin>/build/:
#   <so>                     -> /sdcard/vst/ on the device
#   skin/Dragonfly - VST - <name>/   -> /sdcard/Synths/
#   pluginlist-entry.xml     the <PLUGIN> line for MPC.settings' pluginList-arm
# Needs: a checkout of mpc-vst-plugins in $MPC_VST (default ../mpc-vst-plugins), python3 + Pillow, a host
# gcc/g++, and one armhf toolchain:
#   TOOLCHAIN=docker   arm32v7/gcc:12 under QEMU (mpc-vst-plugins' standard; glibc 2.36)
#   TOOLCHAIN=zig      zig c++ -target arm-linux-gnueabihf.2.36 (pip install ziglang; no Docker needed)
# Default: docker if it's installed, else zig.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
MPC_VST="${MPC_VST:-$ROOT/../mpc-vst-plugins}"
[ -f "$MPC_VST/tools/gen_vst.py" ] || { echo "MPC_VST=$MPC_VST is not an mpc-vst-plugins checkout" >&2; exit 1; }
if [ -z "${TOOLCHAIN:-}" ]; then command -v docker >/dev/null && TOOLCHAIN=docker || TOOLCHAIN=zig; fi
PLUGINS="${*:-hall room plate early}"

FV="allpass biquad comb delay delayline earlyref efilter nrev nrevb progenitor progenitor2 revbase slot strev utils zrev zrev2"
FV_SRC=""; for f in $FV; do FV_SRC="$FV_SRC src/dragonfly/common/freeverb/$f.cpp"; done
CXXFLAGS_COMMON="-O2 -std=gnu++11 -DLIBFV3_FLOAT -fPIC -fvisibility=hidden -Isrc/shim -Isrc/dragonfly/common -Ivst -I$MPC_VST/wrapper"
# armv7-a, VFPv3-D16, hard-float, Thumb-2: the same target as the other MPC OS ports (readelf -A)
ARM_FLAGS="-march=armv7-a -mfpu=vfpv3-d16 -mfloat-abi=hard -mthumb"

jget() { python3 -c "import json,sys; v=json.load(open(sys.argv[1]))[sys.argv[2]]; print(' '.join(v) if isinstance(v,list) else v)" "$1" "$2"; }

mkdir -p vst/.host
g++ -O2 -w -I"$MPC_VST/tools/vendor/force-shadow/tools" -x c -o vst/.host/shadow_art "$MPC_VST/tools/shadow_art.c" -lm

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

  # 2. the page layout (from vst/df_skin.py's spec), then params.h, skin and plugin-list entry
  #    (mpc-vst-plugins' generator), then the Dragonfly look painted over the kit's images, and the entry
  #    made an effect
  python3 vst/df_skin.py layout "$P"
  SHADOW_ART="$ROOT/vst/.host/shadow_art" python3 "$MPC_VST/tools/gen_vst.py" "$CFG"
  python3 vst/df_skin.py paint "$P"
  sed -i -e 's/category="Synth"/category="Effect"/' -e 's/isInstrument="1"/isInstrument="0"/' \
         -e 's/numInputs="0"/numInputs="2"/' "$B/pluginlist-entry.xml"

  # 3. the plugin
  SRCS="vst/dragonfly_vst.cpp vst/dsp_glue.cpp src/dragonfly/plugins/$UP/DSP.cpp $FV_SRC"
  FLAGS="$CXXFLAGS_COMMON $DEFS $INC -I$B -Wno-deprecated"
  case "$TOOLCHAIN" in
    zig)
      ZIG="${ZIG:-python3 -m ziglang}"
      # -ffp-contract=off: keep the same float results as gcc on this target (no FMA fusion)
      $ZIG c++ -target arm-linux-gnueabihf.2.36 -mcpu=generic+v7a+vfp3d16-d32-neon+thumb2 -ffp-contract=off \
          $FLAGS -w -shared -Wl,--no-undefined -Wl,--version-script=vst/exports.map -Wl,--gc-sections -ffunction-sections -fdata-sections \
          -Wl,-s $SRCS -o "$B/$SO" ;;
    docker)
      docker run --rm --platform linux/arm/v7 -u "$(id -u):$(id -g)" -v "$ROOT":/b -v "$MPC_VST":/mv:ro -w /b arm32v7/gcc:12 \
        bash -euc "g++ ${FLAGS//$MPC_VST//mv} $ARM_FLAGS -w -shared -Wl,--no-undefined -Wl,--version-script=vst/exports.map $SRCS \
                   -static-libstdc++ -static-libgcc -o '$B/$SO' && strip '$B/$SO'" ;;
    *) echo "TOOLCHAIN must be docker or zig" >&2; exit 1 ;;
  esac

  # 4. checks: one export, armhf, glibc <= 2.36 (the device has 2.39), no libstdc++ to find on the device
  EXP=$(readelf --dyn-syms -W "$B/$SO" | awk '$5=="GLOBAL" && $7!="UND" && $4!="NOTYPE"{print $8}' | tr '\n' ' ')
  GLIBC=$(readelf -V "$B/$SO" | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1)
  NEEDED=$(readelf -d "$B/$SO" | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p' | tr '\n' ' ')
  echo "   $(file -b "$B/$SO" | cut -d, -f1-3)"
  echo "   exported: $EXP"
  echo "   needed:   $NEEDED"
  echo "   highest glibc: $GLIBC (device has 2.39)"
  [ "$EXP" = "VSTPluginMain " ] || { echo "error: unexpected exports" >&2; exit 1; }
  case "$NEEDED" in *libstdc++*|*libc++*) echo "error: C++ runtime must be linked statically" >&2; exit 1 ;; esac
  [ "$(printf '%s\n%s\n' "$GLIBC" GLIBC_2.36 | sort -V | tail -1)" = GLIBC_2.36 ] || { echo "error: needs glibc > 2.36" >&2; exit 1; }
done
