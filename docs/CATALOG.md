# The MPC OS Plugin Catalog

The [MPC OS Plugin Catalog](https://sd88me.github.io/mpc-vst-plugins/) lists plugins from their GitHub releases.
Each Dragonfly plugin is its own catalog entry, with one zip per device generation in each release:

| Catalog id | Gen1 zip (armv7) | Gen2 zip (aarch64) | Installs (both) |
|---|---|---|---|
| `dragonfly-hall` | `Hall-X.Y.Z-mpc-armv7.zip` | `Hall-X.Y.Z-mpc-aarch64.zip` | `<Synths>/Dragonfly - VST - Hall/dragonfly_hall.so` + its page |
| `dragonfly-room` | `Room-X.Y.Z-mpc-armv7.zip` | `Room-X.Y.Z-mpc-aarch64.zip` | `<Synths>/Dragonfly - VST - Room/dragonfly_room.so` + page |
| `dragonfly-plate` | `Plate-X.Y.Z-mpc-armv7.zip` | `Plate-X.Y.Z-mpc-aarch64.zip` | `<Synths>/Dragonfly - VST - Plate/dragonfly_plate.so` + page |
| `dragonfly-early-reflections` | `Early-Refl-X.Y.Z-mpc-armv7.zip` | `Early-Refl-X.Y.Z-mpc-aarch64.zip` | `<Synths>/Dragonfly - VST - Early Refl/dragonfly_early.so` + page |

(The kit's portable layout: one self-contained folder in a Synths folder, `/sdcard/Synths` by default on Gen1; on
Gen2 the Synths folder MPC lists in `SynthContentLocations`, e.g. `/nvme/Synths` on a Live III. The collection zip
(docs/DISTRIBUTION.md) names the `.so` files `Hall.so` etc. instead.)

`tools/package.sh` builds them with the kit's `tools/release.py` (installer, manifest, checksums; the zip is named from
the `.so`'s ELF machine) and checks each with its `tools/catalog_check.py --catalog`; CI does this for every tag (the
repo name comes from GitHub). The registry entry stays one per plugin with the armv7 `asset_pattern`: the catalog
finds the Gen2 zip by swapping `armv7` for `aarch64` and lists both (kit docs/GEN2.md). **The Gen2 zip must be on
the same release as the Gen1 zip of the repo the entry points at.** The same release also carries the Force VST
distribution zip (`Dragonfly-Reverb-for-MPC-OS-X.Y.Z.zip`, Gen1 only, docs/DISTRIBUTION.md), which the catalog ignores.

**Never change** the ids, the plugins' uids or the `.so` names: projects and the catalog find the plugins by them.
Gen1 and Gen2 zips share id, uid, version and parameters, so projects move between generations. Versions are `X.Y.Z`;
bump X only if parameter positions change.

## Listing the plugins (once)
1. Publish a release (see Releasing below).
2. Generate the four registry entries with your GitHub repo and the name to show:
   `python3 tools/catalog_entries.py --repo <you>/mpc-vst-dragonfly --author "<your name>" -o catalog-entries`
3. Fork https://github.com/sd88me/mpc-vst-plugins, copy the four files into its `catalog/plugins/`, and open one
   pull request. Its check runs on the entries; a maintainer merges it. After that, new releases appear by
   themselves (nightly).

## Releasing
1. Bump `VERSION` (X.Y.Z) and add its `## X.Y.Z` section to `CHANGELOG.md`; commit and push.
2. `git tag vX.Y.Z && git push --tags`. CI builds, tests, packages and makes a **draft** release with all zips.
3. On a device, smoke-test the draft's zips: install with a catalog zip's `install.sh`, load the plugin on a
   track, play it, turn every page and Q-Link, save and reload a project, then run `uninstall.sh`. Optionally
   measure CPU with the kit's `tools/bench.sh <.so> <device-ip> -j` (it picks the build for the device). Do the same
   with the `-mpc-aarch64.zip` files on a Gen2 device when one is available.
4. Record it in `tested.json` at the repo root (the catalog shows it), commit, push. A Gen2 test needs "Gen2" in
   `device` (it gives the "Verified Gen2" badge):
   `[ { "version": "X.Y.Z", "device": "Force", "firmware": "<version>", "date": "YYYY-MM-DD" },
      { "version": "X.Y.Z", "device": "MPC Live III (Gen2)", "firmware": "<version>", "date": "YYYY-MM-DD" } ]`
5. Publish the draft. The catalog lists it on its next run.

## One install method per device
The catalog zips' `install.sh` adds the plugin to MPC's plugin list directly. `vstscanner.sh` (Force VST
distribution) rebuilds that whole list from the plugin folders in `Synths` folders, so it removes plugins that
were installed with `install.sh`. On a device that uses `vstscanner`, use the distribution zip; otherwise the
catalog zips.
