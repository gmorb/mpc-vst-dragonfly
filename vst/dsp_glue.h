/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* C API of dsp_glue.cpp (one Dragonfly plugin's DSP, parameters and presets). Values are in the
 * plugin's own units (%, m, ms, Hz, s, or an option index), exactly as upstream's DSP takes them. */
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

int df_param_count(void);
const char *df_param_name(int i);
const char *df_param_symbol(int i);
const char *df_param_unit(int i);
float df_param_min(int i);
float df_param_max(int i);
float df_default(int i);
int df_option_count(int i);                 /* 0: a continuous param */
const char *df_option_name(int i, int k);

int df_preset_count(void);                  /* 0: no presets (Early Reflections) */
int df_default_preset(void);
const char *df_preset_bank(int p);
const char *df_preset_name(int p);
const float *df_preset_values(int p);       /* df_param_count() values */
int df_bank_count(void);                    /* Hall/Room: presets come in banks (0: no banks) */
int df_presets_per_bank(void);
const char *df_bank_name(int b);

void *df_create(double sample_rate);
void df_destroy(void *d);
void df_set(void *d, int i, float v);
float df_get(void *d, int i);
void df_set_sample_rate(void *d, double sr);
void df_mute(void *d);
void df_run(void *d, const float **in, float **out, uint32_t frames);

#ifdef __cplusplus
}
#endif
