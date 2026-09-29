/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* dsp_glue.cpp -- the only translation unit that sees Dragonfly's own headers (mpc-vst-dragonfly).
 *
 * Built once per plugin with -I src/dragonfly/plugins/<plugin> first on the include path, so
 * "DistrhoPluginInfo.h" / "DSP.hpp" are that plugin's. It hides upstream's PARAMS[] (which would
 * clash with the generated params.h's PARAMS[]) behind a small C API used by dragonfly_vst.cpp and
 * by tools/dump_params.cpp. Which preset table the plugin has is picked with one define:
 *   DF_PRESETS_BANKS   banks[NUM_BANKS].presets[PRESETS_PER_BANK]   (Hall, Room)
 *   DF_PRESETS_FLAT    presets[NUM_PRESETS]                         (Plate)
 *   (neither)          no presets; DEFAULTS[] holds the defaults    (Early Reflections)
 */
#include <new>
#include "DistrhoPluginInfo.h"
#include "DSP.hpp"
#include "dsp_glue.h"

extern "C" {

int df_param_count(void) { return paramCount; }
const char *df_param_name(int i) { return (i >= 0 && i < paramCount) ? PARAMS[i].name : ""; }
const char *df_param_symbol(int i) { return (i >= 0 && i < paramCount) ? PARAMS[i].symbol : ""; }
const char *df_param_unit(int i) { return (i >= 0 && i < paramCount) ? PARAMS[i].unit : ""; }
float df_param_min(int i) { return (i >= 0 && i < paramCount) ? PARAMS[i].range_min : 0.0f; }
float df_param_max(int i) { return (i >= 0 && i < paramCount) ? PARAMS[i].range_max : 1.0f; }

#if defined(DF_PRESETS_BANKS)
int df_preset_count(void) { return NUM_BANKS * PRESETS_PER_BANK; }
int df_default_preset(void) { return DEFAULT_BANK * PRESETS_PER_BANK + DEFAULT_PRESET; }
const char *df_preset_bank(int p) { return banks[p / PRESETS_PER_BANK].name; }
const char *df_preset_name(int p) { return banks[p / PRESETS_PER_BANK].presets[p % PRESETS_PER_BANK].name; }
const float *df_preset_values(int p) { return banks[p / PRESETS_PER_BANK].presets[p % PRESETS_PER_BANK].params; }
int df_bank_count(void) { return NUM_BANKS; }
int df_presets_per_bank(void) { return PRESETS_PER_BANK; }
const char *df_bank_name(int b) { return (b >= 0 && b < NUM_BANKS) ? banks[b].name : ""; }
#elif defined(DF_PRESETS_FLAT)
int df_preset_count(void) { return NUM_PRESETS; }
int df_default_preset(void) { return DEFAULT_PRESET; }
const char *df_preset_bank(int) { return ""; }
const char *df_preset_name(int p) { return presets[p].name; }
const float *df_preset_values(int p) { return presets[p].params; }
int df_bank_count(void) { return 0; }
int df_presets_per_bank(void) { return 0; }
const char *df_bank_name(int) { return ""; }
#else
int df_preset_count(void) { return 0; }
int df_default_preset(void) { return -1; }
const char *df_preset_bank(int) { return ""; }
const char *df_preset_name(int) { return ""; }
const float *df_preset_values(int) { return DEFAULTS; }
int df_bank_count(void) { return 0; }
int df_presets_per_bank(void) { return 0; }
const char *df_bank_name(int) { return ""; }
#endif

float df_default(int i) {
    if (i < 0 || i >= paramCount) return 0.0f;
    int p = df_default_preset();
    return df_preset_values(p < 0 ? 0 : p)[i];
}

/* Enum-like upstream params (shown as option lists, not knobs). */
int df_option_count(int i) {
#if defined(DF_HAS_ALGORITHM)
    if (i == paramAlgorithm) return ALGORITHM_COUNT;
#endif
#if defined(DF_HAS_PROGRAM)
    if (i == paramProgram) return PROGRAM_COUNT;
#endif
    (void)i;
    return 0;
}
const char *df_option_name(int i, int k) {
#if defined(DF_HAS_ALGORITHM)
    if (i == paramAlgorithm && k >= 0 && k < ALGORITHM_COUNT) return algorithmNames[k];
#endif
#if defined(DF_HAS_PROGRAM)
    if (i == paramProgram && k >= 0 && k < PROGRAM_COUNT) return programs[k].name;
#endif
    (void)i; (void)k;
    return "";
}

void *df_create(double sample_rate) {
    return new (std::nothrow) DragonflyReverbDSP(sample_rate);
}
void df_destroy(void *d) { delete static_cast<DragonflyReverbDSP *>(d); }
void df_set(void *d, int i, float v) { static_cast<DragonflyReverbDSP *>(d)->setParameterValue(i, v); }
float df_get(void *d, int i) { return static_cast<DragonflyReverbDSP *>(d)->getParameterValue(i); }
void df_set_sample_rate(void *d, double sr) { static_cast<DragonflyReverbDSP *>(d)->sampleRateChanged(sr); }
void df_mute(void *d) { static_cast<DragonflyReverbDSP *>(d)->mute(); }
void df_run(void *d, const float **in, float **out, uint32_t frames) {
    static_cast<DragonflyReverbDSP *>(d)->run(in, out, frames);
}

}  // extern "C"
