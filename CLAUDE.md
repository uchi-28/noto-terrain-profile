# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A tool to visualize terrain change from the 2024 Noto Peninsula earthquake and the Aug. 2024 Oku-Noto flooding: it extracts elevation profiles along a user-defined transect from multiple DEMs (before/after) and plots them as a cross-section for comparison. The task spec (in Japanese) is `task01.md`; `task01_results.md` documents what was built and verified. Per `task01.md`, this started as a local Python app (`src/dem_profile/`) and now also has a static web port (`docs/`) deployable to GitHub Pages — both implement the same sampling algorithm independently (Python vs. JS), not one wrapping the other.

## Commands

There is no system Python installed — this project is managed entirely with `uv` (it fetches its own Python 3.14 interpreter). Always prefix commands with `uv run`.

```
uv sync                 # install/refresh the environment from pyproject.toml
uv run pytest -q        # run the full test suite
uv run pytest tests/test_sampling.py::test_sample_dem_along_line_returns_expected_z  # single test
uv add <package>        # add a runtime dependency
uv add --dev <package>  # add a dev-only dependency
```

Running the CLI (all DEM/point coordinates must be in EPSG:6675):

```
uv run python -m dem_profile.cli \
  --dem dem/bfeq_pref_07ed694_67ee703.tif \
  --dem dem/afeq_mliti_07ed694_67ee703.tif \
  --dem dem/afst_07ed694_67ee703.tif \
  --start -1500 158000 --end 1500 158500 --interval 5 \
  --out-csv out/profile.csv --out-png out/profile.png
```

Picking the transect interactively by clicking on a hillshade instead of typing coordinates — this opens a real GUI window and blocks on mouse clicks, so it must be run in a local interactive terminal (not headless/CI), and its result can't be verified by an agent without a human clicking:

```
uv run python -m dem_profile.pick_transect \
  --hillshade-dem dem/afeq_mliti_07ed694_67ee703.tif \
  --dem dem/bfeq_pref_07ed694_67ee703.tif --dem dem/afeq_mliti_07ed694_67ee703.tif --dem dem/afst_07ed694_67ee703.tif \
  --interval 5 --out-csv out/profile.csv --out-png out/profile.png
```

The hillshade and the profile chart share one window (profile panel below the hillshade, always visible) — clicking 2 points fills it in without switching screens; a 3rd click (or Esc) clears the selection to pick again. `--out-csv`/`--out-png` are only written when the "保存" button in that same window is clicked (it can be clicked again after re-picking, each time overwriting the same output paths); closing the window without ever clicking it discards the run.

Same flow, but with the DEM paths entered in a GUI form instead of CLI args (see `pick_transect_gui.py` below) — also GUI, also blocks on clicks, same local-terminal-only caveat:

```
uv run python -m dem_profile.pick_transect_gui
```

Generating/refreshing the downsampled DEMs the web app serves (`docs/data/*.tif`, 2m resolution — see "Web app" below for why):

```
uv run python -m dem_profile.prepare_web_data \
  --dem dem/bfeq_pref_07ed694_67ee703.tif --dem dem/afeq_mliti_07ed694_67ee703.tif --dem dem/afst_07ed694_67ee703.tif \
  --target-resolution 2.0 --out-dir docs/data
```

Serving/testing the web app locally (it uses `fetch`, so it needs real HTTP, not `file://`):

```
uv run python -m http.server 8000 --directory docs   # then open http://localhost:8000/
node --test tests-js/*.test.mjs                       # unit tests for docs/js/sampling.js, hillshade.js (no browser needed)
cd tools/e2e && npm install && npx playwright install chromium   # first time only
cd tools/e2e && node check.mjs                        # headless-browser click-through E2E check
```

There is no configured linter/formatter in this project yet.

## Architecture

`src/dem_profile/` is deliberately split so the extraction logic can later be reused by a web port without dragging in matplotlib/CLI/GUI concerns:

- **`sampling.py`** — all raster I/O and geometry, no plotting. `validate_crs()` checks every input DEM against EPSG:6675 (note: uses `to_epsg(confidence_threshold=20)`, not the pyproj default of 70 — these DEMs' WKT doesn't bit-match pyproj's canonical EPSG:6675 definition at the default confidence, even though the CRS is unambiguous). `sample_dem_along_line()` walks a single DEM at fixed intervals along a transect, converting out-of-bounds/nodata points to `NaN` rather than erroring, so a transect only partially covered by one DEM still plots (the line just breaks where data is missing). `build_profile_dataframe()` runs this across multiple DEMs and stacks them into one long-format DataFrame (`dem, distance, x, y, z`) — long format because `plotting.py` groups by the `dem` column to draw one line per DEM. `dem` defaults to each path's filename, but an optional `names` list (same length/order as `dem_paths`) overrides it — this is what lets `transect_session.py`/`docs/app.js` show a user-chosen legend label instead of the raw filename.
- **`fonts.py`** — one shared `configure_japanese_font()` used by both `plotting.py` and `transect_session.py`, since both render Japanese text (titles/labels/legend) and matplotlib's default font can't. Probes `matplotlib.font_manager` for an installed Japanese-capable font (Yu Gothic/Meiryo/MS Gothic/etc.); warns instead of failing if none is found. Keep this shared rather than duplicated — that was a real bug once (the picker window silently didn't call it and showed missing-glyph boxes for its Japanese title/labels).
- **`hillshade.py`** — `compute_hillshade()` reads a DEM (downsampled via `out_shape`/`Resampling.average` to `max_pixels`, using the `.tif.ovr` overviews already shipped alongside `dem/*.tif` for speed) and returns a `(hillshade, extent)` pair via `matplotlib.colors.LightSource`. `extent` is always the DEM's real `bounds`, independent of the display resolution — this is what keeps click coordinates from a downsampled preview accurate to the underlying CRS.
- **`plotting.py`** — turns a sampling DataFrame into the cross-section PNG. `draw_profile(ax, df)` draws onto an existing (already-cleared) axes — colors per DEM, legend outside the axes via `bbox_to_anchor` so it never overlaps the plotted lines, labeled with the DEM filename per the spec. `build_profile_figure(df)` wraps that in its own standalone `(fig, ax)`; `plot_profiles(df, output_path)` wraps *that*, `savefig`s, and closes. The `draw_profile`/`build_profile_figure` split exists so `transect_session.py` can draw the exact same chart onto a panel embedded in its own multi-axes window instead of only ever getting a whole new standalone figure.
- **`transect_session.py`** — one matplotlib window with the hillshade on top and a profile panel permanently reserved below it (no second window, no screen-switching): clicking 2 points on the hillshade draws the transect and immediately renders the profile in the panel below in place; a 3rd click (or Esc) clears the selection so a new transect can be picked without restarting anything; a "保存" `Button` writes the current profile to `out_csv`/`out_png` (re-clickable after re-picking — each click overwrites the same paths). `run_transect_session(...)` computes the hillshade and blocks on `plt.show()` until the window is closed, returning whether the save button was ever clicked. As with `picker.py` (now folded into this module) the wiring is split out into `_build_session(...)` (no `plt.show()`) so `tests/test_transect_session.py` can drive it with synthetic `MouseEvent`/`KeyEvent`/button press+release events and verify the click→profile update, 3rd-click/Esc reset, and save-writes-files behavior headlessly. A `Button` only fires its `"clicked"` callback on release, after press has grabbed the mouse (see `Button._click`/`_release`) — press alone does nothing, so tests must send both events. What the tests can't cover is the real window actually opening/rendering on a given machine — that still needs a human running `dem-profile-pick` locally once. (This module replaces an earlier two-window design — a `picker.py` that blocked until 2 clicks then closed, followed by a separate `profile_viewer.py` preview-then-save window — collapsed into one window because switching screens for every transect was the exact complaint that prompted this design.)
- **`cli.py`** — argument parsing and wiring for the coordinate-driven entry point (`dem-profile`); owns nothing reusable elsewhere. Unlike `pick_transect.py`, it saves immediately — there's no interactive step to preview before, since the transect is already fully specified via `--start`/`--end`.
- **`pick_transect.py`** — argument parsing and wiring for the hillshade-click entry point (`dem-profile-pick`); `main()` just forwards the parsed args straight into `transect_session.run_transect_session()`.
- **`pick_transect_gui.py`** (`dem-profile-pick-gui`) — upgrade over `pick_transect.py` requiring DEM paths as CLI args: opens a Tkinter form first (dynamic "+ DEMを追加"/削除 rows, each with a path field, a "陰影図"-selection radio, and a "凡例名" field that falls back to the filename when left blank, plus interval/output-path fields), then on submit destroys the form and calls `transect_session.run_transect_session(..., dem_names=...)` — so the combined hillshade+profile window is the unmodified one described above, just now reached via a path-entry form instead of argv. Input validation (`_collect_dem_entries`/`_parse_interval`/`_select_hillshade_dem`) is factored out as plain functions specifically so `tests/test_pick_transect_gui.py` can cover it without opening a Tk window — same split as `transect_session.py`/`_build_session`. `run_transect_session()`'s return value picks which final `messagebox` to show ("断面図を保存しました" vs. "保存しませんでした"). The Tkinter window itself still needs a human to verify, for the same reason the matplotlib window does.
- **`web_export.py`** / **`prepare_web_data.py`** — `resample_dem()` reuses the same `out_shape`/`Resampling.average` decimation pattern as `hillshade.py` to shrink a DEM to a target resolution (default 2m) and writes it as DEFLATE-compressed GeoTIFF, preserving CRS/nodata/bounds. Exists solely because GitHub Pages can't serve the ~600MB originals (see below).

### Web app (`docs/`)

Deployable as-is to GitHub Pages ("Deploy from a branch" → `/docs`, no build step, no bundler). It's a from-scratch reimplementation, not a Pyodide wrapper around the Python code — GDAL/rasterio aren't available in-browser, so `docs/js/sampling.js` and `docs/js/hillshade.js` are direct ports of `sampling.py`/`hillshade.py`'s algorithms, kept dependency-free (no DOM/fetch) specifically so `tests-js/*.test.mjs` can unit-test them under plain Node. No CRS reprojection logic exists anywhere in the web app — everything stays in EPSG:6675 meters, so it's pure affine math (pixel↔geo), not a lat/lng web map.

- **`docs/js/geotiff-loader.js`** — fetches a DEM URL as raw bytes and parses with `GeoTIFF.fromArrayBuffer()` (vendored `geotiff.js`). Deliberately *not* `GeoTIFF.fromUrl(url, {allowFullFile: true})`: that code path assumes/attempts HTTP Range requests, and throws (`RangeError: Invalid field type: 0`) when fetching from a server that just returns 200 with the full body (Python's `http.server`, and generally not guaranteed on GitHub Pages either) — this was an actual bug hit and fixed during development, not a hypothetical. `fromArrayBuffer` on a manually-fetched full response sidesteps it entirely, which is fine since the downsampled DEMs are only single-digit-to-30MB.
- **`docs/js/hillshade.js`** — Lambertian shading from a central-difference surface normal dotted with a light direction vector from azimuth/altitude; conceptually the same thing `matplotlib.colors.LightSource.hillshade()` does in `hillshade.py`, just hand-rolled since there's no equivalent browser library in play. Outputs a `Float32Array` of intensities (NaN at nodata) plus `hillshadeToRgba()` to turn that into a canvas `ImageData`-ready buffer with nodata as fully transparent.
- **`docs/js/sampling.js`** — port of `sampling.py`'s station-generation/sampling/long-format-stacking logic (`generateStations`/`sampleDemAlongLine`/`buildProfileData`), same out-of-bounds/nodata→NaN behavior.
- **`docs/js/picker.js`** — canvas equivalent of `picker.py`: `createPicker()` draws the hillshade, tracks clicks, converts canvas-pixel→geo via the DEM's bbox, and fires a callback after 2 clicks (a 3rd click starts a fresh selection instead of requiring a reset button). Since a browser can't block synchronously the way `plt.show()` does, this is callback-based rather than return-value-based.
- **`docs/js/profileChart.js`** — renders the long-format rows via vendored Chart.js, one dataset per `dem` value, legend pinned to `position: "bottom"` (its own reserved band, so it can't overlap the plotted lines) — same intent as `plotting.py`'s `bbox_to_anchor` legend placement, different mechanism.
- **`docs/vendor/`** — `geotiff.js` and `chart.umd.min.js`, copied from npm (`geotiff`, `chart.js`) rather than CDN-linked, so the published page doesn't depend on a third-party CDN staying up/unchanged. See `docs/vendor/VERSIONS.md` for exact versions and how to update them.
- **`docs/app.js`** — wires the above together and also sets `window.__state.{hillshadeReady,picked,profile}` purely as a test hook for `tools/e2e/check.mjs` to poll via `page.waitForFunction()`; not used by the UI itself. DEM sources are no longer hardcoded constants: `index.html`'s "0. DEMファイルを選択" section holds dynamic rows (path text input + "陰影図に使う" radio + 凡例名 text input + 削除 button, "+ DEMを追加" to add more), built/read by `addDemRow()`/`readDemRows()`. On load (and whenever "この設定で読み込む" is clicked) `loadFromForm()` re-fetches whichever paths are currently entered, computes the hillshade from the radio-selected row, and rebuilds the picker (`picker.destroy()` on the old one first) — so switching DEMs doesn't need a page reload. Paths are plain relative/absolute URLs fetched via the existing `loadDem()` (still no local-filesystem-path access — browsers can't do that from a text field), prefilled by default with the three `docs/data/*.tif` paths so the out-of-the-box flow (and `tools/e2e/check.mjs`) behaves exactly as before without any user interaction. Each row's 凡例名 field is optional — `currentDemEntries` uses it verbatim when non-blank, falling back to `nameFromPath()` (the basename) otherwise, mirroring `sampling.build_profile_dataframe()`'s `names` override on the Python side.

**`tools/e2e/`** — a Playwright harness, `npm install`+`playwright install chromium` once, then `node check.mjs`. It spawns `.venv/Scripts/python.exe -m http.server` directly (not `uv run python -m http.server`) — `uv run` is a supervisor process, and killing it from Node's `child_process` doesn't reliably kill the actual `python.exe` child on Windows, which left orphaned servers holding the port across runs during development. This harness is the reason the web app's click-driven flow has *more* automated coverage than the desktop GUI: `picker.py`'s real window still needs a human, but `picker.js`'s real clicks are driven headlessly end-to-end (hillshade load → 2 clicks → chart render → CSV button enabled → Esc-cancel), not just unit-tested in isolation. Clicks use `canvas.click({ position })` (element-relative, auto-scrolling), not `page.mouse.click(pageX, pageY)` — the latter broke when the "0. DEMファイルを選択" section was added and pushed the canvas below the fixed 1200px test viewport, since absolute page coordinates don't account for page length/scroll.

### Data layout (not code, but relevant when picking transects)

- `dem/*.tif` — three GeoTIFF DEMs, all EPSG:6675, 0.5m resolution, `float32`, nodata=3.4e38: `bfeq_pref_*` (before earthquake), `afeq_mliti_*` (after earthquake), `afst_*` (after the storm/flooding). Gitignored — largest is ~613MB, over GitHub's 100MB-without-LFS limit, and not needed by anyone who only runs the web app.
- These DEMs do **not** spatially overlap much: `bfeq_pref` covers y=101250–156000, while `afeq_mliti`/`afst` cover y=156000–160500 — they only meet at the y=156000 boundary. A transect meant to compare before/after must be chosen near/within that shared boundary region; otherwise the before-earthquake DEM will come back all-NaN (this is expected behavior, not a bug — see `task01_results.md`).
- `docs/data/*.tif` — the same three DEMs downsampled to 2m (via `prepare_web_data`) specifically so the web app's total payload (~50MB) fits GitHub Pages' constraints; this is a real fidelity trade-off (0.5m → 2m), not just a performance optimization, and was chosen with the user's explicit sign-off.
- `roi/` — a reference-area shapefile, currently unused by the tool.
