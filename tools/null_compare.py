#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 the mpc-vst-dragonfly contributors
"""Null test of two sets of vst/render.c renders (tools/null_test.sh).

  null_compare.py <dir A> <dir B> <limit dB> [label]

For every setting rendered in B (NN.f32: interleaved stereo float32), subtracts A from B and prints the residual's
level relative to B (RMS, dB) for the worst and the median setting. Exit 1 if the worst is above <limit dB> (a less
negative number), or if a setting is missing, of a different length or not finite.
"""
import glob
import os
import sys

import numpy as np


def main():
    a_dir, b_dir, limit = sys.argv[1], sys.argv[2], float(sys.argv[3])
    label = sys.argv[4] if len(sys.argv) > 4 else f"{a_dir} vs {b_dir}"
    files = sorted(glob.glob(os.path.join(b_dir, "*.f32")))
    if not files:
        print(f"FAIL {label}: no renders in {b_dir}")
        return 1
    nulls, ident, bad = [], 0, []
    for fb in files:
        fa = os.path.join(a_dir, os.path.basename(fb))
        if not os.path.exists(fa):
            bad.append(f"{os.path.basename(fb)} missing")
            continue
        a = np.fromfile(fa, np.float32).astype(np.float64)
        b = np.fromfile(fb, np.float32).astype(np.float64)
        if a.shape != b.shape or not (np.isfinite(a).all() and np.isfinite(b).all()):
            bad.append(f"{os.path.basename(fb)} length or non-finite")
            continue
        r = a - b
        if not r.any():
            ident += 1
            continue
        ref = np.sqrt(np.mean(b ** 2)) or 1e-30
        nulls.append(20 * np.log10(np.sqrt(np.mean(r ** 2)) / ref))
    n = len(files)
    worst = max(nulls) if nulls else float("-inf")
    text = f"{ident}/{n} bit-identical"
    if nulls:
        text += f", worst {worst:.1f} dB, median {np.median(nulls):.1f} dB"
    ok = not bad and worst <= limit
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {text} (limit {limit:.0f} dB)" + (f"; {', '.join(bad)}" if bad else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
