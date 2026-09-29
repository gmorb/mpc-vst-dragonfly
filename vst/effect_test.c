/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* effect_test.c -- offline test of a Dragonfly MPC plugin .so (mpc-vst-dragonfly).
 * dlopens the plugin like MPC's host does and checks, per plugin:
 *   two independent instances; magic, stereo in/out, effect category, chunk flag;
 *   every param has a name and a display string, and a set/get round trip holds;
 *   option params select on exact values and step one option on a nudge;
 *   the preset param loads the preset's values and reports them to the host;
 *   the preset popup opens and closes on a pick;
 *   an impulse gives a finite, bounded reverb tail (and silence in -> silence out);
 *   in-place processing (in == out) and the legacy accumulating process() work;
 *   chunk save -> restore into a fresh instance gives the same params AND the same audio;
 *   44.1 -> 48 kHz sample-rate change keeps working; every preset/program renders sanely.
 * Build it for the PC (with -fsanitize=address against a PC build of the plugin), or for armhf and run
 * it under qemu-arm against the real device .so.   effect_test <plugin.so>    exit 1 on any failure. */
#include <dlfcn.h>
#include <math.h>
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
enum { effOpen = 0, effClose = 1, effGetParamDisplay = 7, effGetParamName = 8, effSetSampleRate = 10,
       effMainsChanged = 12, effGetChunk = 23, effSetChunk = 24, effGetPlugCategory = 35, effGetEffectName = 45 };

#define MAXP 64
static int automated[MAXP], fails;
static float automated_val[MAXP];
static intptr_t host(AEffect *e, int32_t op, int32_t i, intptr_t v, void *p, float o) {
    (void)e; (void)v; (void)p;
    if (op == 0 && i >= 0 && i < MAXP) { automated[i]++; automated_val[i] = o; }
    if (op == 1) return 2400;   /* audioMasterVersion */
    return 0;
}
#define CHECK(c, ...) do { printf("%s ", (c) ? "ok  " : "FAIL"); printf(__VA_ARGS__); printf("\n"); if (!(c)) fails++; } while (0)
#define B 128

static char pname[MAXP][64];
static int find(AEffect *a, const char *name) {
    for (int i = 0; i < a->numParams; i++) if (!strcmp(pname[i], name)) return i;
    return -1;
}
/* Run n blocks; input = impulse at block 0 (if imp) else silence. Returns peak |out| after skip_blocks,
 * and sets *finite = 0 on any NaN/Inf. Optionally records the output into rec (n*B*2 floats). */
static float run(AEffect *a, int n, int imp, int skip_blocks, int *finite, float *rec) {
    float il[B], ir[B], ol[B], or_[B], *in[2] = {il, ir}, *out[2] = {ol, or_}, peak = 0;
    for (int k = 0; k < n; k++) {
        memset(il, 0, sizeof il); memset(ir, 0, sizeof ir);
        if (imp && k == 0) { il[0] = 1.0f; ir[0] = 1.0f; }
        a->pr(a, in, out, B);
        for (int j = 0; j < B; j++) {
            if (!isfinite(ol[j]) || !isfinite(or_[j])) *finite = 0;
            if (k >= skip_blocks) { float m = fabsf(ol[j]) > fabsf(or_[j]) ? fabsf(ol[j]) : fabsf(or_[j]); if (m > peak) peak = m; }
            if (rec) { rec[(k * B + j) * 2] = ol[j]; rec[(k * B + j) * 2 + 1] = or_[j]; }
        }
    }
    return peak;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: effect_test <plugin.so>\n"); return 2; }
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) { printf("FAIL dlopen: %s\n", dlerror()); return 1; }
    AEffect *(*entry)(hostcb) = (AEffect *(*)(hostcb))dlsym(h, "VSTPluginMain");
    CHECK(entry != NULL, "exports VSTPluginMain");
    if (!entry) return 1;
    AEffect *a = entry(host), *b = entry(host);
    CHECK(a && b && a != b, "two independent instances");
    if (!a || !b) return 1;
    char name[256] = {0};
    a->d(a, effGetEffectName, 0, 0, name, 0);
    printf("---- %s: %d params, uid %08x\n", name, a->numParams, a->uid);
    CHECK(a->magic == 0x56737450, "magic 'VstP'");
    CHECK(a->numInputs == 2 && a->numOutputs == 2, "stereo in -> stereo out");
    CHECK(a->d(a, effGetPlugCategory, 0, 0, 0, 0) == 1, "category: effect");
    CHECK((a->flags & (1 << 5)) && (a->flags & (1 << 4)), "program chunks + processReplacing flags");
    CHECK(a->pr && a->process, "processReplacing and process both set");
    CHECK(a->numParams > 0 && a->numParams <= MAXP, "param count sane");
    a->d(a, effOpen, 0, 0, 0, 0); b->d(b, effOpen, 0, 0, 0, 0);
    a->d(a, effSetSampleRate, 0, 0, 0, 44100.0f); a->d(a, effMainsChanged, 0, 1, 0, 0);

    /* names, displays */
    int named = 0, shown = 0;
    for (int i = 0; i < a->numParams; i++) {
        char d[256] = {0};
        a->d(a, effGetParamName, i, 0, pname[i], 0);
        a->d(a, effGetParamDisplay, i, 0, d, 0);
        named += pname[i][0] != 0; shown += d[0] != 0;
        printf("     [%2d] %-14s = %-22s (%.3f)\n", i, pname[i], d, a->getP(a, i));
    }
    CHECK(named == a->numParams && shown == a->numParams, "every param has a name and a display string");

    int preset = find(a, "Preset"), open = find(a, "Preset List");
    int n_dsp = preset >= 0 ? preset : a->numParams - (find(a, "Program List") >= 0 ? 1 : 0);

    /* continuous round trip (skip option params: they're detected by snapping) */
    int rt_ok = 1, opt_idx = -1;
    for (int i = 0; i < n_dsp; i++) {
        a->setP(a, i, 0.37f);
        float g = a->getP(a, i);
        if (fabsf(g - 0.37f) > 1e-3f) { if (opt_idx < 0) opt_idx = i; continue; }   /* snapped: an option param */
        a->setP(a, i, 0.0f); if (fabsf(a->getP(a, i)) > 1e-4f) rt_ok = 0;
        a->setP(a, i, 1.0f); if (fabsf(a->getP(a, i) - 1.0f) > 1e-4f) rt_ok = 0;
    }
    CHECK(rt_ok, "continuous params: set/get round trip at 0, 0.37, 1");

    /* option param (Plate algorithm / Early program): exact pick, then a nudge steps one option */
    if (opt_idx >= 0) {
        char d[256];
        a->setP(a, opt_idx, 0.0f);
        float step = -1;
        for (int k = 1; k < 32; k++) { a->setP(a, opt_idx, 1.0f / k); float g = a->getP(a, opt_idx); if (fabsf(g - 1.0f / k) < 1e-4f) step = 1.0f / k; }
        a->setP(a, opt_idx, 0.0f);
        a->setP(a, opt_idx, 0.01f);   /* a nudge up from option 0 */
        a->d(a, effGetParamDisplay, opt_idx, 0, d, 0);
        CHECK(step > 0 && fabsf(a->getP(a, opt_idx) - step) < 1e-4f, "option '%s': a nudge steps to the next option (%s)", pname[opt_idx], d);
        a->setP(a, opt_idx, 1.0f);
        a->setP(a, opt_idx, 0.99f);   /* a nudge down from the last */
        CHECK(fabsf(a->getP(a, opt_idx) - (1.0f - step)) < 1e-4f, "option '%s': a nudge down steps back one", pname[opt_idx]);
    }

    /* presets: pick each, check a param moved and the host heard about it */
    if (preset >= 0) {
        int n = 0;
        for (int k = 1; k < 64; k++) { a->setP(a, preset, 1.0f / k); if (fabsf(a->getP(a, preset) - 1.0f / k) < 1e-4f) n = k + 1; }
        CHECK(n > 1, "preset param has %d presets", n);
        int loaded = 1, reported = 1, sane = 1;
        for (int p = 0; p < n; p++) {
            memset(automated, 0, sizeof automated);
            a->setP(a, preset, (float)p / (n - 1));
            int f = 1;
            float pk = run(a, 4, 1, 0, &f, NULL);   /* notifications go out from the audio callback */
            for (int i = 0; i < n_dsp; i++) {
                if (!automated[i]) reported = 0;
                else if (fabsf(automated_val[i] - a->getP(a, i)) > 1e-4f) reported = 0;
            }
            if (!f || pk > 20.0f) sane = 0;
            char d[256]; a->d(a, effGetParamDisplay, preset, 0, d, 0);
            if (!d[0]) loaded = 0;
        }
        CHECK(loaded, "every preset has a display name");
        CHECK(reported, "a preset load reports every param's new value to the host (audioMasterAutomate)");
        CHECK(sane, "every preset renders finite, bounded audio");
        /* two different presets really give different settings */
        float v0[MAXP], v1[MAXP]; int differ = 0, back = 1;
        a->setP(a, preset, 0.0f); for (int i = 0; i < n_dsp; i++) v0[i] = a->getP(a, i);
        a->setP(a, preset, 1.0f); for (int i = 0; i < n_dsp; i++) { v1[i] = a->getP(a, i); differ += v1[i] != v0[i]; }
        a->setP(a, 0, 0.123f);   /* a user tweak... */
        a->setP(a, preset, 0.0f); for (int i = 0; i < n_dsp; i++) back &= a->getP(a, i) == v0[i];
        CHECK(differ > 0 && back, "first/last preset differ in %d params; re-picking a preset overrides tweaks", differ);
        int bank = find(a, "Bank");
        if (bank >= 0) {   /* the original UI: picking a bank loads that bank's current preset */
            int nb = 0;
            for (int k = 1; k < 16; k++) { a->setP(a, bank, 1.0f / k); if (fabsf(a->getP(a, bank) - 1.0f / k) < 1e-4f) nb = k + 1; }
            int per = n / nb;
            a->setP(a, preset, (float)(1 * per + 3) / (n - 1));          /* bank 1, its 4th preset */
            a->setP(a, preset, (float)(3 * per + 0) / (n - 1));          /* bank 3, its 1st */
            CHECK(fabsf(a->getP(a, bank) - 3.0f / (nb - 1)) < 1e-4f, "bank follows the loaded preset (%d banks of %d)", nb, per);
            a->setP(a, bank, 1.0f / (nb - 1));                            /* back to bank 1 */
            CHECK(fabsf(a->getP(a, preset) - (float)(1 * per + 3) / (n - 1)) < 1e-4f,
                  "picking a bank loads the preset last picked in it");
            char dsp_[64]; a->d(a, effGetParamDisplay, bank, 0, dsp_, 0);
            CHECK(dsp_[0] != 0, "bank shows its name (%s)", dsp_);
        }
        if (open >= 0) {
            memset(automated, 0, sizeof automated);
            a->setP(a, open, 1.0f);
            CHECK(a->getP(a, open) == 1.0f, "preset popup opens");
            a->setP(a, preset, 2.0f / (n - 1));
            int f = 1; run(a, 1, 0, 0, &f, NULL);
            CHECK(a->getP(a, open) == 0.0f && automated[open] > 0, "picking a preset closes the popup and tells the host");
            a->setP(a, open, 1.0f);
            a->setP(a, preset, 2.5f / (n - 1));   /* a Q-Link nudge */
            CHECK(a->getP(a, open) == 1.0f, "a Q-Link nudge on the preset leaves the popup open");
            a->setP(a, open, 0.0f);
        }
    }

    /* audio: impulse -> tail; silence -> silence */
    if (preset >= 0) a->setP(a, preset, a->getP(a, preset));   /* re-pick the current preset: known state */
    int f = 1;
    a->d(a, effMainsChanged, 0, 0, 0, 0); a->d(a, effMainsChanged, 0, 1, 0, 0);   /* resume: clears the tail */
    float silence = run(a, 50, 0, 0, &f, NULL);
    CHECK(f && silence < 1e-4f, "after a resume, silence in -> at most a -80 dB residue out (%.1e)", silence);
    {
        AEffect *c = entry(host); int fc = 1;
        float s0 = run(c, 50, 0, 0, &fc, NULL);
        CHECK(fc && s0 == 0.0f, "fresh instance: silence in -> exact silence out");
        float il[B] = {0}, ir[B] = {0}, ol[B], or_[B], *in[2] = {il, ir}, *out[2] = {ol, or_};
        for (int j = 0; j < B; j++) { ol[j] = 0.25f; or_[j] = 0.25f; }
        c->process(c, in, out, B);
        int acc = 1; for (int j = 0; j < B; j++) if (ol[j] != 0.25f || or_[j] != 0.25f) acc = 0;
        il[0] = ir[0] = 1.0f;
        c->process(c, in, out, B);
        CHECK(acc && ol[0] > 0.25f, "legacy process() adds to the outputs (%.3f after an impulse)", ol[0]);
        c->d(c, effClose, 0, 0, 0, 0);
    }
    float tail = run(a, 700, 1, 35, &f, NULL);          /* ~2 s; peak after the first 100 ms */
    CHECK(f, "impulse response is finite (no NaN/Inf)");
    CHECK(tail > 1e-5f && tail < 4.0f, "impulse gives a reverb tail after 100 ms (peak %.5f)", tail);
    float late = run(a, 3500, 0, 3400, &f, NULL);        /* +10 s of silence */
    CHECK(f && late < 1e-2f, "tail decays (peak %.2e after 12 s)", late);

    /* in-place: in == out */
    {
        float l[B], r[B], *io[2] = {l, r}, pk = 0;
        a->d(a, effMainsChanged, 0, 1, 0, 0);
        for (int k = 0; k < 100; k++) {
            for (int j = 0; j < B; j++) { l[j] = (k == 0 && j == 0) ? 1.0f : 0.0f; r[j] = l[j]; }
            a->pr(a, io, io, B);
            for (int j = 0; j < B; j++) { if (!isfinite(l[j]) || !isfinite(r[j])) f = 0; if (fabsf(l[j]) > pk) pk = fabsf(l[j]); }
        }
        CHECK(f && pk > 0 && pk < 4.0f, "in-place processing (in == out) works (peak %.4f)", pk);
    }
    /* odd block sizes */
    {
        float il[1000] = {0}, ir[1000] = {0}, ol[1000], or_[1000], *in[2] = {il, ir}, *out[2] = {ol, or_};
        il[0] = ir[0] = 1;
        a->pr(a, in, out, 1); a->pr(a, in, out, 1000); a->pr(a, in, out, 0); a->pr(a, in, out, 37);
        int ok = 1; for (int j = 0; j < 1000; j++) if (!isfinite(ol[j])) ok = 0;
        CHECK(ok, "block sizes 1, 1000, 0, 37");
    }

    /* chunk: tweak a, save, restore into b: same params. Then restore the same chunk into two FRESH
     * instances and require bit-identical audio (a itself has been running, so its modulation LFOs are
     * mid-cycle; a restore must be deterministic, not match a running instance's phase). */
    for (int i = 0; i < n_dsp; i++) if (i != opt_idx) a->setP(a, i, 0.2f + 0.6f * (float)((i * 7) % 11) / 10.0f);
    if (opt_idx >= 0) a->setP(a, opt_idx, 1.0f);
    void *chunk = NULL;
    intptr_t len = a->d(a, effGetChunk, 0, 0, &chunk, 0);
    CHECK(len > 0 && chunk, "chunk saved (%d bytes)", (int)len);
    if (len > 0 && chunk) {
        printf("     chunk: %.160s%s\n", (char *)chunk, len > 160 ? "..." : "");
        char *copy = malloc(len); memcpy(copy, chunk, len);
        CHECK(b->d(b, effSetChunk, 0, len, copy, 0) == 1, "chunk accepted by another instance");
        int same = 1;
        for (int i = 0; i < a->numParams; i++) if (i != open && fabsf(a->getP(a, i) - b->getP(b, i)) > 1e-5f) { same = 0; printf("     differs: [%d] %s\n", i, pname[i]); }
        CHECK(same, "restored instance has the same parameter values");
        AEffect *c1 = entry(host), *c2 = entry(host);
        c1->d(c1, effSetChunk, 0, len, copy, 0); c2->d(c2, effSetChunk, 0, len, copy, 0);
        float *ra = malloc(sizeof(float) * 400 * B * 2), *rb = malloc(sizeof(float) * 400 * B * 2);
        int fa = 1, fb = 1;
        run(c1, 400, 1, 0, &fa, ra); run(c2, 400, 1, 0, &fb, rb);
        double diff = 0, ea = 0, eb = 0;
        for (int j = 0; j < 400 * B * 2; j++) { double dd = fabs(ra[j] - rb[j]); if (dd > diff) diff = dd; ea += ra[j] * ra[j]; eb += rb[j] * rb[j]; }
        double ratio = eb > 0 ? sqrt(ea / eb) : 0;
        /* Room and Plate modulate with freeverb3's std::rand() noise (as the desktop plugins do), so two
         * restores can't be bit-identical; require the same level (RMS within 3%) instead. */
        CHECK(fa && fb && ea > 0 && fabs(ratio - 1.0) < 0.03, "two restored instances sound the same (%s; RMS ratio %.4f)",
              diff == 0.0 ? "bit-identical" : "rand()-modulated", ratio);
        free(ra); free(rb); free(copy);
        c1->d(c1, effClose, 0, 0, 0, 0); c2->d(c2, effClose, 0, 0, 0, 0);
        const char *bad = "garbage";
        CHECK(b->d(b, effSetChunk, 0, (intptr_t)strlen(bad) + 1, (void *)bad, 0) == 0, "a foreign chunk is refused");
    }

    /* sample-rate change */
    a->d(a, effSetSampleRate, 0, 0, 0, 48000.0f); a->d(a, effMainsChanged, 0, 1, 0, 0);
    f = 1; float p48 = run(a, 400, 1, 10, &f, NULL);
    CHECK(f && p48 > 0 && p48 < 4.0f, "48 kHz works (peak %.4f)", p48);

    /* parameter storm while running (Q-Link turns during playback) */
    a->d(a, effSetSampleRate, 0, 0, 0, 44100.0f);
    f = 1;
    for (int k = 0; k < 400; k++) {
        for (int i = 0; i < n_dsp; i++) a->setP(a, i, 0.5f + 0.5f * sinf(k * 0.05f + i));
        run(a, 1, k % 50 == 0, 0, &f, NULL);
    }
    CHECK(f, "parameter sweep during playback stays finite");

    a->d(a, effClose, 0, 0, 0, 0); b->d(b, effClose, 0, 0, 0, 0);
    printf("%s: %s (%d failure%s)\n", name, fails ? "FAILED" : "PASSED", fails, fails == 1 ? "" : "s");
    return fails ? 1 : 0;
}
