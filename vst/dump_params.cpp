/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* dump_params.cpp -- print one Dragonfly plugin's parameter list as mpc-vst-plugins params.json
 * (tools/params.py format), straight from upstream's DistrhoPluginInfo.h via dsp_glue.
 * Built for the build host, linked with the same dsp_glue.cpp as the plugin:
 *   dump_params "<plugin display name>" > params.json
 * VST index order = upstream's order, then "preset" when the plugin has presets. Never reorder. */
#include <stdio.h>
#include <string.h>
#include "dsp_glue.h"

static void js(const char *s) {
    putchar('"');
    for (; *s; s++) {
        if (*s == '"' || *s == '\\') putchar('\\');
        putchar(*s);
    }
    putchar('"');
}

int main(int argc, char **argv) {
    printf("{\n  \"name\": ");
    js(argc > 1 ? argv[1] : "Dragonfly");
    printf(",\n  \"params\": [\n");
    int n = df_param_count();
    for (int i = 0; i < n; i++) {
        printf("    {\"key\": "); js(df_param_symbol(i));
        printf(", \"name\": "); js(df_param_name(i));
        int no = df_option_count(i);
        if (no) {
            printf(", \"options\": [");
            for (int k = 0; k < no; k++) { if (k) printf(", "); js(df_option_name(i, k)); }
            printf("], \"default\": %d", (int)df_default(i));
        } else {
            printf(", \"min\": %.9g, \"max\": %.9g, \"unit\": ", df_param_min(i), df_param_max(i));
            js(df_param_unit(i));
            printf(", \"default\": %.9g", df_default(i));
        }
        printf("}%s\n", (i < n - 1 || df_preset_count()) ? "," : "");
    }
    if (df_preset_count()) {
        printf("    {\"key\": \"preset\", \"name\": \"Preset\", \"options\": [");
        for (int k = 0; k < df_preset_count(); k++) { if (k) printf(", "); js(df_preset_name(k)); }
        printf("], \"default\": %d}%s\n", df_default_preset(), df_bank_count() ? "," : "");
    }
    if (df_bank_count()) {   /* the original UI's bank tabs: picking one loads that bank's current preset */
        printf("    {\"key\": \"bank\", \"name\": \"Bank\", \"options\": [");
        for (int b = 0; b < df_bank_count(); b++) { if (b) printf(", "); js(df_bank_name(b)); }
        printf("], \"default\": %d}\n", df_default_preset() / df_presets_per_bank());
    }
    printf("  ]\n}\n");
    return 0;
}
