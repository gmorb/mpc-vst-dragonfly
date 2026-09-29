# Distribution layout

Releases follow the **Force VST plugins distribution** layout (the one its DISTRHO and AirWindows collections
use), so they drop into the same `Synths` folder and are registered by its `vstscanner.sh` / `vstmanager.sh`.
This is the layout for every port going forward.

```
<Collection name>/                          the release zip's single top folder
  <Vendor> - VST - <Name>/                  one self-contained folder per plugin
    <Name>.so                               the plugin (no spaces in the file name)
    plugin-meta.xml                         one <PLUGIN .../> line: MPC's plugin-list entry
    version.xml                             <identifier>vendor.vst.name</identifier>, <version>a.b.c.d</version>
    <Name>.json                             parameter description (index, name, range, unit, type, options, format)
    Plugin Skins/                           the page: TUI.json, Q-Links*.json, images
    LICENSE, NOTICE.md                      the plugin's licence(s) and component notices
  README.md, LICENSE, NOTICE.md, licenses/  install instructions and licence texts for the collection
```

## Rules
- **The folder name is MPC's page-folder name**: `<manufacturer> - VST - <name>`, with `manufacturer=` and
  `name=` exactly as in `plugin-meta.xml`. MPC finds the page (`Plugin Skins/`) by it, so plugin and page share
  one folder.
- **`file=` in plugin-meta.xml** is `%payload-path%/<folder>/<Name>.so`. The scanner replaces `%payload-path%`
  with the `Synths` folder the plugin folder sits in.
- **Plugin folders go directly into a `Synths` folder** on a drive under `/media` (the scanner reads
  `/media/*/Synths/*/plugin-meta.xml`, one level deep), e.g. `/media/662522/Synths` on MockbaMod.
- **Names fit MPC's insert slot** (about 11 characters): the manufacturer line already shows the vendor, so the
  name is just the plugin (`Hall`, not `Dragonfly Hall`).
- The scanner takes MPC's settings file as its first argument (default: MockbaMod's
  `/data/Settings/MPC/MPC.settings`).

## In this repository
`tools/package.sh` builds the layout from `vst/build.sh`'s output: the page folder the kit generates is already
named `<Vendor> - VST - <Name>` and holds `Plugin Skins/` and `version.xml`; the packager adds the `.so` (renamed
`<Name>.so`), `plugin-meta.xml` (its `file=` rewritten), `version.xml` (release version), `<Name>.json`
(`tools/param_json.py`) and the licences. Checked against the real `vstscanner.sh`: every registered plugin loads
from its path and has its page beside it.
