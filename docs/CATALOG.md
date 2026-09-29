# The MPC OS Plugin Catalog

The [MPC OS Plugin Catalog](https://sd88me.github.io/mpc-vst-plugins/) lists plugins from their GitHub releases.
Each Dragonfly plugin is its own catalog entry with its own zip:

| Catalog id | Zip in each release | Installs |
|---|---|---|
| `dragonfly-hall` | `Hall-X.Y.Z-mpc-armv7.zip` | `/sdcard/vst/dragonfly_hall.so` + page in `/sdcard/Synths` |
| `dragonfly-room` | `Room-X.Y.Z-mpc-armv7.zip` | `/sdcard/vst/dragonfly_room.so` + page |
| `dragonfly-plate` | `Plate-X.Y.Z-mpc-armv7.zip` | `/sdcard/vst/dragonfly_plate.so` + page |
| `dragonfly-early-reflections` | `Early-Refl-X.Y.Z-mpc-armv7.zip` | `/sdcard/vst/dragonfly_early.so` + page |

`tools/package.sh` builds them with the kit's `tools/release.py` (installer, manifest, checksums) and checks each
with its `tools/catalog_check.py --catalog`; CI does this for every tag (the repo name comes from GitHub). The same
release also carries the Force VST distribution zip (`Dragonfly-Reverb-for-MPC-OS-X.Y.Z.zip`, docs/DISTRIBUTION.md);
the catalog only picks up `*-mpc-armv7.zip` files.

**Never change** the ids, the plugins' uids or the `.so` names (`dragonfly_*.so`): projects and the catalog find
the plugins by them. Versions are `X.Y.Z`; bump X only if parameter positions change.

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
   measure CPU with the kit's `tools/bench.sh <.so> <device-ip> -j`.
4. Record it in `tested.json` at the repo root (the catalog shows it), commit, push:
   `[ { "version": "X.Y.Z", "device": "Force", "firmware": "<version>", "date": "YYYY-MM-DD" } ]`
5. Publish the draft. The catalog lists it on its next run.

## One install method per device
The catalog zips' `install.sh` adds the plugin to MPC's plugin list directly. `vstscanner.sh` (Force VST
distribution) rebuilds that whole list from the plugin folders in `Synths` folders, so it removes plugins that
were installed with `install.sh`. On a device that uses `vstscanner`, use the distribution zip; otherwise the
catalog zips.
