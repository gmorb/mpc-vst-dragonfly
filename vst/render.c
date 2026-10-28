/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* render.c -- renders a fixed test signal through every preset (or, for Early Reflections, every program)
 * of a Dragonfly MPC plugin .so, for tools/null_test.sh (mpc-vst-dragonfly).
 *   render <plugin.so> <outdir> [sample_rate]
 * Per setting k it writes <outdir>/<k>.f32: interleaved stereo float32. The plugin is loaded as MPC's host
 * loads it (VST2 ABI, a fresh instance per setting, the setting picked through its parameter).
 * Signal (deterministic, the same on every machine): 0.5 s of white noise at -6 dBFS (L and R uncorrelated),
 * 0.5 s of silence, a unit impulse on both channels, then silence to 6 s: the reverb's full tail.
 * Presets are picked through the plugin's Preset/Program parameter, or as VST programs when it has none. */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct AEffect AEffect;
typedef intptr_t (*hostcb)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
struct AEffect {
    int32_t magic;
    intptr_t (*d)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
    void (*process)(AEffect *, float **, float **, int32_t);
    void (*setP)(AEffect *, int32_t, float);
    float (*getP)(AEffect *, int32_t);
    int32_t numPrograms, numParams, numInputs, numOutputs, flags;
    intptr_t r1, r2;
    int32_t a, b, c;
    float io;
    void *obj, *user;
    int32_t uid, ver;
    void (*pr)(AEffect *, float **, float **, int32_t);
    void *pdr;
    char f[56];
};
#define B 256
enum { effOpen = 0, effClose = 1, effSetProgram = 2, effGetParamName = 8, effSetSampleRate = 10, effSetBlockSize = 11, effMainsChanged = 12 };
static float host_sr = 48000.0f;
static intptr_t host(AEffect *e, int32_t op, int32_t i, intptr_t v, void *p, float o) {
    (void)e; (void)i; (void)v; (void)p; (void)o;
    if (op == 1) return 2400;                    /* audioMasterVersion */
    if (op == 16) return (intptr_t)host_sr;      /* audioMasterGetSampleRate: answered as a real host does */
    if (op == 17) return B;                      /* audioMasterGetBlockSize */
    return 0;
}

static uint32_t rng = 0x12345678u;
static float noise(void) {               /* xorshift32 -> [-0.5, 0.5): exact on every target */
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
    return (float)(int32_t)(rng >> 8) / 16777216.0f - 0.5f;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: render <plugin.so> <outdir> [sample_rate]\n"); return 2; }
    float sr = argc > 3 ? (float)atof(argv[3]) : 48000.0f;
    host_sr = sr;
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    AEffect *(*m)(hostcb) = (AEffect *(*)(hostcb))dlsym(h, "VSTPluginMain");
    if (!m) m = (AEffect *(*)(hostcb))dlsym(h, "main");   /* older VST2 builds (upstream's DPF build) */
    if (!m) { fprintf(stderr, "no VSTPluginMain\n"); return 1; }

    AEffect *a = m(host);
    int sel = -1, nsel = 1;
    for (int i = 0; i < a->numParams; i++) {
        char n[64] = {0};
        a->d(a, effGetParamName, i, 0, n, 0);
        if (!strcmp(n, "Preset") || !strcmp(n, "Program")) { sel = i; break; }
    }
    if (sel >= 0)   /* count the options: the param holds k/(n-1) exactly for the right n */
        for (int k = 1; k < 64; k++) { a->setP(a, sel, 1.0f / k); if (a->getP(a, sel) == 1.0f / k) nsel = k + 1; }
    int programs = sel < 0 && a->numPrograms > 1;   /* upstream's own (DPF) VST2 build: presets are programs */
    if (programs) nsel = a->numPrograms;
    a->d(a, effClose, 0, 0, 0, 0);

    const int frames = (int)(6 * sr), burst = (int)(0.5f * sr), imp = (int)(1.0f * sr);
    float *rec = (float *)malloc(sizeof(float) * 2 * (frames + B));
    for (int s = 0; s < nsel; s++) {
        /* freeverb3's noise modulators (efilter_t.hpp) draw from libc's one process-wide rand(), so a reverb's
         * exact output depends on who called rand() before it -- as in any host. Reseed as a fresh process
         * is, so every setting renders the same whatever ran before it. */
        srand(1);
        a = m(host);
        a->d(a, effOpen, 0, 0, 0, 0);
        a->d(a, effSetSampleRate, 0, 0, 0, sr);
        a->d(a, effSetBlockSize, 0, B, 0, 0);
        a->d(a, effMainsChanged, 0, 1, 0, 0);
        if (sel >= 0 && nsel > 1) a->setP(a, sel, (float)s / (nsel - 1));
        if (programs) a->d(a, effSetProgram, 0, s, 0, 0);
        rng = 0x12345678u;
        float il[B], ir[B], ol[B], or_[B], *in[2] = {il, ir}, *out[2] = {ol, or_};
        for (int f0 = 0; f0 < frames; f0 += B) {
            for (int j = 0; j < B; j++) {
                int t = f0 + j;
                il[j] = t < burst ? noise() : t == imp ? 1.0f : 0.0f;
                ir[j] = t < burst ? noise() : t == imp ? 1.0f : 0.0f;
            }
            a->pr(a, in, out, B);
            for (int j = 0; j < B; j++) { rec[(f0 + j) * 2] = ol[j]; rec[(f0 + j) * 2 + 1] = or_[j]; }
        }
        a->d(a, effMainsChanged, 0, 0, 0, 0);
        a->d(a, effClose, 0, 0, 0, 0);
        char path[1024];
        snprintf(path, sizeof path, "%s/%02d.f32", argv[2], s);
        FILE *fo = fopen(path, "wb");
        if (!fo) { perror(path); return 1; }
        fwrite(rec, sizeof(float), (size_t)frames * 2, fo);
        fclose(fo);
    }
    printf("%d settings rendered\n", nsel);
    return 0;
}
