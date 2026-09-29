/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* =============================================================================
 * dragonfly_vst.cpp -- a Dragonfly Reverb plugin as a Linux VST2 *effect* for the built-in JUCE
 * plugin host of MPC OS standalone devices (mpc-vst-dragonfly).
 *
 * Same ABI and parameter conventions as mpc-vst-plugins' wrapper/vst2_wrap.c (hand-written VST2,
 * no Steinberg SDK; option params step one option per Q-Link nudge; popups via wrapper/popup.h;
 * host notifications deferred to the audio callback; state saved as a chunk), but:
 *   - stereo in -> stereo out (vst2_wrap.c's engine interface is output-only, for instruments);
 *   - float audio straight through at the host's block size (Dragonfly's DSP takes any size);
 *   - the parameter list is upstream's, in upstream's order, then one "preset" option param when
 *     the plugin has presets, then the layout's hidden popup flags (params.h, from gen_vst.py).
 * The DSP itself is only reached through dsp_glue.h (see dsp_glue.cpp for why).
 * ========================================================================== */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <strings.h>
#include "params.h"
#include "popup.h"
#include "dsp_glue.h"
#include "formats.h"      /* DF_FORMATS[]: the original UI's value formats (vst/gen_formats.py) */

/* ---- VST2 ABI (hand-written; no Steinberg SDK) -------------------------- */
struct AEffect;
typedef intptr_t (*audioMasterCallback)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
struct AEffect {
    int32_t magic;
    intptr_t (*dispatcher)(AEffect *, int32_t, int32_t, intptr_t, void *, float);
    void (*process)(AEffect *, float **, float **, int32_t);
    void (*setParameter)(AEffect *, int32_t, float);
    float (*getParameter)(AEffect *, int32_t);
    int32_t numPrograms, numParams, numInputs, numOutputs, flags;
    intptr_t resvd1, resvd2;
    int32_t initialDelay, realQualities, offQualities;
    float ioRatio;
    void *object, *user;
    int32_t uniqueID, version;
    void (*processReplacing)(AEffect *, float **, float **, int32_t);
    void (*processDoubleReplacing)(AEffect *, double **, double **, int32_t);
    char future[56];
};
enum {
    effOpen = 0, effClose = 1, effGetParamLabel = 6, effGetParamDisplay = 7, effGetParamName = 8,
    effSetSampleRate = 10, effSetBlockSize = 11, effMainsChanged = 12, effGetChunk = 23,
    effSetChunk = 24, effCanBeAutomated = 26, effGetPlugCategory = 35,
    effGetEffectName = 45, effGetVendorString = 47, effGetProductString = 48,
    effGetVendorVersion = 49, effCanDo = 51, effGetVstVersion = 58,
};
enum { audioMasterAutomate = 0, audioMasterUpdateDisplay = 42 };
enum { effFlagsCanReplacing = 1 << 4, effFlagsProgramChunks = 1 << 5 };
enum { kPlugCategEffect = 1 };

#define MAX_DSP_PARAMS 32
#define ACC_BLOCK 256          /* legacy accumulate process(): rendered through this scratch size */

/* ---- per-instance state ------------------------------------------------- */
struct wrap_t {
    AEffect fx;
    audioMasterCallback master;
    void *dsp;
    double sr;
    int preset;                          /* last picked preset, -1 if none */
    int bank_pick[16];                   /* per bank, its current preset (the original UI's currentProgram[]) */
    float open[NPARAMS];                 /* popup "open" flags (popup.h): never sent to the DSP or saved */
    volatile char release[NPARAMS];      /* popup flags to report back to 0 */
    volatile char changed[NPARAMS];      /* params a preset load changed: report their new value */
    volatile char need_update_display;
    float acc[2][ACC_BLOCK];
    char chunk[4096];
};

static int n_dsp;          /* upstream's paramCount: VST indices 0..n_dsp-1 */
static int preset_idx;     /* VST index of the "preset" param, or -1 */
static int bank_idx;       /* VST index of the "bank" param (Hall/Room), or -1 */

static float clamp01(float v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

static float real_to_norm(int i, float v) {
    const param_t *p = &PARAMS[i];
    if (p->nopts > 1) return clamp01(v / (p->nopts - 1));
    return p->max > p->min ? clamp01((v - p->min) / (p->max - p->min)) : 0;
}
static float norm_to_real(int i, float n) {
    const param_t *p = &PARAMS[i];
    if (p->nopts > 1) return (float)lroundf(clamp01(n) * (p->nopts - 1));
    return p->min + (p->max - p->min) * clamp01(n);
}

static float get_real(wrap_t *w, int i) {
    if (i < n_dsp) return df_get(w->dsp, i);
    if (i == preset_idx) return (float)(w->preset < 0 ? 0 : w->preset);
    if (i == bank_idx) return (float)((w->preset < 0 ? df_default_preset() : w->preset) / df_presets_per_bank());
    return 0;
}
static float get_norm(wrap_t *w, int i) {
    if (i < 0 || i >= NPARAMS) return 0;
    if (popup_is(i)) return w->open[i];
    return real_to_norm(i, get_real(w, i));
}

static void load_preset(wrap_t *w, int k) {
    if (k < 0 || k >= df_preset_count()) return;
    const float *v = df_preset_values(k);
    w->preset = k;
    if (bank_idx >= 0) {
        w->bank_pick[k / df_presets_per_bank()] = k % df_presets_per_bank();
        w->changed[bank_idx] = 1;
    }
    if (preset_idx >= 0) w->changed[preset_idx] = 1;
    for (int j = 0; j < n_dsp; j++) {
        df_set(w->dsp, j, v[j]);
        w->changed[j] = 1;   /* tell the host (and so the MPC page) in processReplacing */
    }
}

static void setParameter(AEffect *e, int32_t i, float n) {
    wrap_t *w = (wrap_t *)e->object;
    if (i < 0 || i >= NPARAMS) return;
    const param_t *p = &PARAMS[i];
    int nudge = 0;
    if (popup_set(w->open, i, n)) return;
    if (p->nopts > 1) {
        /* As vst2_wrap.c: a value on an option selects it; one between options is a Q-Link/encoder
         * nudge from the current option, which steps one option that way. */
        float pos = clamp01(n) * (p->nopts - 1);
        if (fabsf(pos - roundf(pos)) > 0.001f) {
            nudge = 1;
            float cur = get_norm(w, i) * (p->nopts - 1);
            int idx = (int)lroundf(cur) + (pos > cur ? 1 : -1);
            if (idx < 0) idx = 0;
            if (idx > p->nopts - 1) idx = p->nopts - 1;
            n = (float)idx / (p->nopts - 1);
        }
    }
    float v = norm_to_real(i, n);
    if (i < n_dsp) df_set(w->dsp, i, v);
    else if (i == preset_idx) {
        int k = (int)v;
        if (!nudge || k != w->preset) load_preset(w, k);   /* a pick (even the same one) reloads it */
    } else if (i == bank_idx) {
        /* As the original UI: picking a bank loads that bank's current preset. */
        int b = (int)v;
        if (!nudge || b != (int)get_real(w, bank_idx)) load_preset(w, b * df_presets_per_bank() + w->bank_pick[b]);
    }
    if (!nudge) popup_picked(w->open, w->release, i);      /* a list pick closes it; a nudge doesn't */
    w->need_update_display = 1;
}

static float getParameter(AEffect *e, int32_t i) { return get_norm((wrap_t *)e->object, i); }

/* Host notifications, from the audio callback so the host is never re-entered from its own call. */
static void notify(wrap_t *w) {
    for (int i = 0; i < NPARAMS; i++) {
        if (w->changed[i]) { w->changed[i] = 0; w->master(&w->fx, audioMasterAutomate, i, 0, 0, get_norm(w, i)); }
        if (w->release[i]) { w->release[i] = 0; w->master(&w->fx, audioMasterAutomate, i, 0, 0, 0.0f); }
    }
    if (w->need_update_display) {
        w->need_update_display = 0;
        w->master(&w->fx, audioMasterUpdateDisplay, 0, 0, 0, 0.0f);
    }
}

static void processReplacing(AEffect *e, float **in, float **out, int32_t n) {
    wrap_t *w = (wrap_t *)e->object;
    if (w->master) notify(w);
    if (n <= 0) return;
    df_run(w->dsp, (const float **)in, out, (uint32_t)n);
}

/* VST2's legacy process() must ADD to the outputs. MPC calls processReplacing, but a NULL
 * e->process would crash any host that tried the old call. */
static void process(AEffect *e, float **in, float **out, int32_t n) {
    wrap_t *w = (wrap_t *)e->object;
    if (w->master) notify(w);
    for (int32_t off = 0; off < n; off += ACC_BLOCK) {
        int32_t k = n - off < ACC_BLOCK ? n - off : ACC_BLOCK;
        const float *ci[2] = {in[0] + off, in[1] + off};
        float *co[2] = {w->acc[0], w->acc[1]};
        df_run(w->dsp, ci, co, (uint32_t)k);
        for (int32_t j = 0; j < k; j++) { out[0][off + j] += w->acc[0][j]; out[1][off + j] += w->acc[1][j]; }
    }
}

static void copy_str(void *dst, const char *src, size_t max) {
    strncpy((char *)dst, src, max - 1);
    ((char *)dst)[max - 1] = 0;
}

/* Value text with its unit (MPC shows the display string; the label is left empty so a host that
 * shows both doesn't print the unit twice). */
static void format_value(wrap_t *w, int i, char *out, size_t len) {
    const param_t *p = &PARAMS[i];
    if (p->nopts) {
        int k = (int)lroundf(get_norm(w, i) * (p->nopts - 1));
        snprintf(out, len, "%s", p->opts[k]);
        return;
    }
    float v = get_real(w, i), range = fabsf(p->max - p->min);
    if (i < n_dsp && DF_FORMATS[i]) {       /* exactly as the original UI prints it */
        char tmp[48];
        if (!strcmp(DF_FORMATS[i], "%i%%")) snprintf(tmp, sizeof tmp, "%i%%", (int)v);
        else snprintf(tmp, sizeof tmp, DF_FORMATS[i], v);
        const char *t = tmp;
        while (*t == ' ') t++;
        snprintf(out, len, "%s", t);
        return;
    }
    int dec = range <= 3 ? 2 : range <= 20 ? 1 : 0;
    if (!strcmp(p->unit, "Hz") && v >= 1000) snprintf(out, len, "%.1f kHz", v / 1000.0f);
    else if (!strcmp(p->unit, "%")) snprintf(out, len, "%.0f%%", v);
    else if (!strcmp(p->unit, "X")) snprintf(out, len, "%.2fx", v);
    else if (p->unit[0]) snprintf(out, len, "%.*f %s", dec, v, p->unit);
    else snprintf(out, len, "%.*f", dec, v);
}

/* State: "dragonfly=1;<key>=<value>;..." in real units, preset first (it only records which one;
 * the values that follow are what's restored). Popup flags are never saved. */
static int get_chunk(wrap_t *w) {
    size_t o = (size_t)snprintf(w->chunk, sizeof w->chunk, "dragonfly=1;");
    for (int i = 0; i < NPARAMS && o < sizeof w->chunk; i++) {
        if (popup_is(i)) continue;
        if (i == preset_idx) o += (size_t)snprintf(w->chunk + o, sizeof w->chunk - o, "%s=%d;", PARAMS[i].key, w->preset);
    }
    for (int i = 0; i < n_dsp && o < sizeof w->chunk; i++)
        o += (size_t)snprintf(w->chunk + o, sizeof w->chunk - o, "%s=%.9g;", PARAMS[i].key, df_get(w->dsp, i));
    return o < sizeof w->chunk ? (int)o + 1 : 0;
}

static void set_chunk(wrap_t *w, const char *s) {
    while (*s) {
        const char *eq = strchr(s, '='), *end = strchr(s, ';');
        if (!end) end = s + strlen(s);
        if (eq && eq < end) {
            size_t kl = (size_t)(eq - s);
            float v = (float)atof(eq + 1);
            for (int i = 0; i < NPARAMS; i++) {
                if (popup_is(i) || strlen(PARAMS[i].key) != kl || strncmp(PARAMS[i].key, s, kl)) continue;
                if (i < n_dsp) {
                    const param_t *p = &PARAMS[i];
                    float lo = p->nopts > 1 ? 0 : p->min, hi = p->nopts > 1 ? (float)(p->nopts - 1) : p->max;
                    if (v < lo) v = lo;
                    if (v > hi) v = hi;
                    df_set(w->dsp, i, p->nopts > 1 ? (float)lroundf(v) : v);
                } else if (i == preset_idx) {
                    int k = (int)v;
                    w->preset = (k >= 0 && k < df_preset_count()) ? k : -1;
                    if (w->preset >= 0 && bank_idx >= 0)
                        w->bank_pick[w->preset / df_presets_per_bank()] = w->preset % df_presets_per_bank();
                } else if (i == bank_idx) {
                    continue;
                }
                w->changed[i] = 1;
            }
        }
        s = *end ? end + 1 : end;
    }
    w->need_update_display = 1;
}

static intptr_t dispatcher(AEffect *e, int32_t op, int32_t idx, intptr_t v, void *p, float o) {
    wrap_t *w = (wrap_t *)e->object;
    switch (op) {
    case effOpen: return 1;
    case effClose:
        df_destroy(w->dsp);
        free(w);
        return 1;
    case effGetPlugCategory: return kPlugCategEffect;
    case effGetEffectName:
    case effGetProductString: copy_str(p, PLUG_NAME, 32); return 1;
    case effGetVendorString: copy_str(p, PLUG_VENDOR, 32); return 1;
    case effGetVendorVersion: return PLUG_VERSION;
    case effGetVstVersion: return 2400;
    case effCanBeAutomated: return idx >= 0 && idx < NPARAMS;
    case effGetParamName:
        if (idx >= 0 && idx < NPARAMS) copy_str(p, PARAMS[idx].name, 32);
        return 1;
    case effGetParamLabel:
        if (p) ((char *)p)[0] = 0;
        return 1;
    case effGetParamDisplay:
        if (idx < 0 || idx >= NPARAMS) return 0;
        format_value(w, idx, (char *)p, 24);
        return 1;
    case effSetSampleRate:
        if (o > 1000 && fabs(o - w->sr) > 0.5) { w->sr = o; df_set_sample_rate(w->dsp, o); }
        return 1;
    case effSetBlockSize: return 1;
    case effMainsChanged:
        if (v) df_mute(w->dsp);   /* resume: start from silence, no stale tail */
        return 1;
    case effCanDo: return -1;
    case effGetChunk: {
        int len = get_chunk(w);
        if (len <= 0) return 0;
        *(void **)p = w->chunk;
        return len;
    }
    case effSetChunk: {
        if (v <= 0 || (size_t)v > sizeof w->chunk || !p) return 0;
        memcpy(w->chunk, p, (size_t)v);
        w->chunk[v - 1] = 0;
        if (strncmp(w->chunk, "dragonfly=", 10)) return 0;
        set_chunk(w, w->chunk);
        return 1;
    }
    default: return 0;
    }
}

/* The generated params.h must describe this build's DSP (same keys, same order). */
static int params_match(void) {
    n_dsp = df_param_count();
    if (n_dsp > MAX_DSP_PARAMS || n_dsp > NPARAMS) return 0;
    for (int i = 0; i < n_dsp; i++)
        if (strcmp(PARAMS[i].key, df_param_symbol(i))) return 0;
    preset_idx = -1;
    if (df_preset_count() > 0) {
        if (NPARAMS <= n_dsp || strcmp(PARAMS[n_dsp].key, "preset") || PARAMS[n_dsp].nopts != df_preset_count()) return 0;
        preset_idx = n_dsp;
    }
    bank_idx = -1;
    if (df_bank_count() > 0) {
        if (df_bank_count() > 16 || NPARAMS <= n_dsp + 1 || strcmp(PARAMS[n_dsp + 1].key, "bank") ||
            PARAMS[n_dsp + 1].nopts != df_bank_count())
            return 0;
        bank_idx = n_dsp + 1;
    }
    return 1;
}

extern "C" __attribute__((visibility("default"))) AEffect *VSTPluginMain(audioMasterCallback master) {
    if (!params_match()) return NULL;
    wrap_t *w = (wrap_t *)calloc(1, sizeof *w);
    if (!w) return NULL;
    w->sr = 44100.0;   /* MPC OS: 44.1 kHz; effSetSampleRate corrects it if a host says otherwise */
    w->dsp = df_create(w->sr);
    if (!w->dsp) { free(w); return NULL; }
    w->master = master;
    w->preset = df_default_preset();
    for (int b = 0; b < 16; b++) w->bank_pick[b] = df_bank_count() ? df_default_preset() % df_presets_per_bank() : 0;
    AEffect *e = &w->fx;
    e->magic = 0x56737450; /* 'VstP' */
    e->dispatcher = dispatcher;
    e->process = process;
    e->setParameter = setParameter;
    e->getParameter = getParameter;
    e->processReplacing = processReplacing;
    e->numParams = NPARAMS;
    e->numInputs = 2;
    e->numOutputs = 2;
    e->flags = effFlagsCanReplacing | effFlagsProgramChunks;
    e->uniqueID = PLUG_UID;
    e->version = PLUG_VERSION;
    e->object = w;
    return e;
}
