# Changelog

## 1.1.0
- Every page redesigned after the original plugin's UI: its logo and title, colours, knobs (light rim, coloured
  face, white pointer, min/max dots), black level faders with a coloured fill, and rounded panels.
- Much larger text: control names and values are about twice their previous on-screen size, and the lists and
  headings use Dragonfly's own NotoSans font.
- Hall and Room: the preset list opens grouped by bank, one column per bank, as in the original.
- Plate and Early Reflections: presets, reverb types and reflection types are lists right on the page.
- Distributed as a collection for `vstscanner.sh` (the Force VST distribution layout).
- Plate and Early Reflections have one parameter fewer (their list pop-up flag). Update the plugin together with
  its page; saved projects keep their settings.

## 1.0.0
- First release: Dragonfly Hall, Room, Plate and Early Reflections 3.2.10 as MPC OS VST2 insert effects.
- Room: fixed upstream's `mute()` leaving the input filters' state (a faint residue after a host resume).
