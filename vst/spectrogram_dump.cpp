/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 the mpc-vst-dragonfly contributors */
/* spectrogram_dump.cpp -- the reverb output behind upstream's spectrogram, per preset (mpc-vst-dragonfly).
 *
 * Does what common/Spectrogram.cpp does before its FFT: a DragonflyReverbDSP at SPECTROGRAM_SAMPLE_RATE with the
 * preset's values and the dry level at 0 ("don't show dry signal"), muted, then one SPECTROGRAM_WINDOW_SIZE burst
 * of white noise followed by silence, keeping the left channel. df_paint.py runs the same windowed FFT and pixel
 * mapping on it and draws the picture. The noise is seeded, so a build is reproducible (upstream seeds with the
 * time; one burst of noise looks like another).
 *   spectrogram_dump <out dir>      -> <out dir>/spec_<preset>.f32 (float32 mono, 8 s + two windows)
 * Built for the build host and linked with the same dsp_glue.cpp as the plugin.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "dsp_glue.h"

#define SPECTROGRAM_SAMPLE_RATE 40960
#define SPECTROGRAM_WINDOW_SIZE 8192
#define SPECTROGRAM_MAX_SECONDS 8.0f

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: spectrogram_dump <out dir>\n"); return 2; }
    static float noise[2][SPECTROGRAM_WINDOW_SIZE], silence[2][SPECTROGRAM_WINDOW_SIZE], out[2][SPECTROGRAM_WINDOW_SIZE];
    srand(1);
    for (int i = 0; i < SPECTROGRAM_WINDOW_SIZE; i++) {
        noise[0][i] = (float)((rand() % 4096) - 2048) / 2048.0f;
        noise[1][i] = (float)((rand() % 4096) - 2048) / 2048.0f;
    }
    const int total = (int)(SPECTROGRAM_MAX_SECONDS * SPECTROGRAM_SAMPLE_RATE) + 2 * SPECTROGRAM_WINDOW_SIZE;
    const int n = df_preset_count();
    for (int k = 0; k < n; k++) {
        void *d = df_create(SPECTROGRAM_SAMPLE_RATE);
        const float *v = df_preset_values(k);
        for (int i = 0; i < df_param_count(); i++) df_set(d, i, v[i]);
        df_set(d, 0, 0.0f);   /* param 0 is the dry level in every Dragonfly plugin */
        df_mute(d);
        char path[1024];
        snprintf(path, sizeof path, "%s/spec_%d.f32", argv[1], k);
        FILE *f = fopen(path, "wb");
        if (!f) { perror(path); return 1; }
        for (int done = 0; done < total; done += SPECTROGRAM_WINDOW_SIZE) {
            const float *in[2] = {done ? silence[0] : noise[0], done ? silence[1] : noise[1]};
            float *o[2] = {out[0], out[1]};
            df_run(d, in, o, SPECTROGRAM_WINDOW_SIZE);
            fwrite(out[0], sizeof(float), SPECTROGRAM_WINDOW_SIZE, f);
        }
        fclose(f);
        df_destroy(d);
    }
    printf("spectrogram: %d presets\n", n);
    return 0;
}
