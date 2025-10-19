<!-- Copilot instructions for the Gcode-Generator repository -->
# Gcode-Generator — AI assistant guide

This file tells an AI coding assistant how this repository is organized and what conventions to follow when making edits. Keep suggestions minimal, local, and consistent with existing styles.

- Project: Python-based CNC G-code generator with a Tkinter UI.
- Key UI: `GUI.py` (Tkinter front-end, image helpers, translation loading).
- Core logic: `main_tkinter.py` (G-code generation functions: surfacing, contour_drilling, matrix_drilling, threading, corner_radius).
- Config & i18n: `config.json` contains persisted operation defaults; `translations.json` contains UI strings.

High-level architecture and intent
- The app provides six 'modes' (surfacing, contour drilling, matrix drilling, corner radius, oblong hole, threading). The UI maps mode selection -> form fields -> calls into `main_tkinter.py` functions to produce G-code strings.
- UI code and generation logic are intentionally decoupled: `GUI.py` controls widgets, defaults come from `config.json` and translations; `main_tkinter.py` contains deterministic G-code templates and returns both gcode and bounding coordinates for stock calculation.

Important project patterns
- Config is read/written as plain JSON with top-level sections matching mode names: e.g. `"surfacing"`, `"threading"`.
- Path type values may be either numeric codes or human labels (e.g. `"1"` or `"Opposition"`) — functions map both forms. Preserve this dual-format handling when editing.
- G-code functions return (gcode_string, start_x, start_y, start_z, current_z, end_x, end_y, clearance_height). Use this contract when calling or refactoring.
- UI images are selected by constructed filenames (see `generate_image_filename` in `GUI.py`). When adding new modes or image variants, follow same naming pattern under `images/` and update `generate_image_filename` mapping.

Developer workflows (what an AI should suggest/modify)
- Running locally: open the repo in an environment with Python 3.x, Pillow installed (PIL). The UI is started by running `GUI.py` or `main_tkinter.py` depending on intent. (No tests found.)
- When changing parameter names in `main_tkinter.py`, update `GUI.py`'s `mode_params` mapping and `config.json` defaults to match keys exactly.
- For translations: add keys to `translations.json` under `translations[<lang>]` and reference them in `GUI.py` using existing keys like `fields`, `path_types`, `corner_types`, etc.

Safety and minimal edits
- Make minimal, localized edits. Avoid cross-cutting renames unless you update `config.json`, `GUI.py`'s `mode_params`, and any place that reads the key.
- Preserve existing string formats in returned G-code (don't change line endings or header semantics unless intentionally improving the header via `generate_header`).

Examples (copy/pasteable pointers)
- To add a new field for surfacing named `coolant_on`: add default to `config.json` under `surfacing`, then add a line in `mode_params["1"]` in `GUI.py` and handle it in `main_tkinter.surfacing` by reading from `config.get("surfacing", {})`.
- To change image selection for mode 5 set of cases, edit `generate_image_filename` (it maps numeric mode and path_type -> image filename) and add the corresponding PNG to `images/`.

Files to inspect when making changes
- `GUI.py` — UI logic, translations loader, image filename logic, `mode_params` form definitions.
- `main_tkinter.py` — generation functions and `generate_header`, calculate_stock_dimensions.
- `config.json` — persisted defaults. Update when adding/removing fields.
- `translations.json` — add localization strings; `language_display_names` in `GUI.py` maps UI language names.

If anything is unclear, ask for the specific change intent (feature, bugfix, refactor) and which mode(s) it affects.

Quick start (PowerShell)
- Create a venv, install dependencies from the repository `requirement.txt` (this repo uses Pillow for images):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirement.txt
```

- Run the GUI (will open a Tkinter window):

```powershell
python GUI.py
```

- Smoke test without GUI (call a generator function and print header):

```powershell
python - <<'PY'
import json
from main_tkinter import load_config, surfacing, generate_header, calculate_stock_dimensions
cfg = load_config()
gcode, sx, sy, sz, cz, ex, ey, ch = surfacing(cfg)
hx, hy, hz = calculate_stock_dimensions([(gcode, sx, sy, sz, cz, ex, ey, ch)])
print(generate_header(cfg.get('project_name','proj'), cfg.get('machine','machine'), hx, hy, hz))
print(gcode.splitlines()[:20])
PY
```
