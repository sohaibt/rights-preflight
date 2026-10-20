# rights-preflight

A rights gate for creative projects. It lists every font, image, audio, video and 3D file in a folder,
finds files with missing or conflicting licenses, and writes a ready-to-ship `CREDITS.md`.
It runs locally or in CI. Python standard library only, no dependencies.

## Install

```bash
pip install rights-preflight
```

## Usage

```bash
rights-preflight scan assets/               # list media files, write assets/rights-manifest.json
rights-preflight check assets/              # exit 1 on any rights problem
rights-preflight check assets/ --commercial # also fail on non-commercial (NC) assets
rights-preflight check assets/ --json       # machine-readable output for CI
rights-preflight credits assets/            # write assets/CREDITS.md grouped by license
```

Example `check` output:

```
images/hero.png: missing-source: CC-BY requires attribution: add source
music/loop.mp3: unknown-license: unknown license: WTFPL
images/bg.png: non-commercial: CC-BY-NC does not allow commercial use
3 problems in 3 of 42 files
```

### Where rights come from

For each field (`license`, `author`, `source`) the first source that has a value wins:

1. **Sidecar**: `<file>.rights.json` next to the file, for example `hero.png.rights.json`:

   ```json
   {"license": "CC-BY-4.0", "author": "Jane Photo", "source": "https://example.com/hero"}
   ```

2. **Project rules**: `rights.json` in the scanned folder. The first rule whose glob matches the
   file's relative path wins. A glob with no `/` also matches the file name alone.

   ```json
   {"rules": [
     {"glob": "fonts/*", "license": "OFL"},
     {"glob": "sfx/**", "license": "CC0", "author": "Freesound", "source": "https://freesound.org"}
   ]}
   ```

3. **Embedded metadata**: the font `name` table (license URL, license text, designer, vendor URL)
   for TTF/OTF/TTC/WOFF, and XMP (`cc:license`, `xmpRights:WebStatement`, `dc:rights`,
   `dc:creator`, `cc:attributionURL`) in images.

`scan` records where each field came from (`rights_from`) in the manifest.

### Built-in licenses

| ID | Attribution required | Commercial use |
|---|---|---|
| CC0 | no | yes |
| CC-BY | yes | yes |
| CC-BY-SA | yes | yes |
| CC-BY-NC | yes | **no** |
| OFL | no | yes |
| Apache-2.0 | yes | yes |
| MIT | yes | yes |
| public-domain | no | yes |
| licensed-proprietary | no | yes |
| ai-generated | no | yes |

IDs are matched case-insensitively, version suffixes are ignored (`CC BY 4.0`, `OFL-1.1`, `Apache 2.0`),
and license URLs and common license names are recognised. "Attribution required" means `check` fails
unless both `author` and `source` are set. Anything else, like CC-BY-ND, is reported as `unknown-license`.

### Checks

| Code | Meaning |
|---|---|
| `missing-license` | no license from any source |
| `unknown-license` | license text is not in the table |
| `missing-author` / `missing-source` | the license requires attribution |
| `non-commercial` | NC license with `--commercial` |
| `bad-sidecar` | a `.rights.json` file is not a valid JSON object |

Exit codes: `0` clean, `1` problems found, `2` bad input (missing folder, invalid `rights.json`).

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: sohaibt/rights-preflight@main
  with:
    path: assets          # default "."
    commercial: "true"    # fail on NC assets
    credits: "false"      # "true" also writes CREDITS.md
```

The action runs the CLI straight from the action folder with the runner's `python3`. Nothing is installed.

## How it is different

- **ScanCode / REUSE** detect source-code licenses and SPDX headers. They are weak on fonts and media
  and have no attribution rules.
- **License Keeper / AssetTrail** are desktop trackers with manual entry and no CI.
- **C2PA** records where media came from. It does not enforce a rights policy.

rights-preflight is one cross-platform CLI. It reads rights from sidecars, project rules and embedded
metadata, enforces a policy that fails CI, and writes `CREDITS.md` plus a machine-readable manifest.

## Development

```bash
python3 -m unittest            # run the tests
python3 tests/make_fixtures.py # regenerate the tiny binary fixtures
```

## License

MIT
