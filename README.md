# Gcode-Generator

Small Python app (Tkinter) that generates G-code files from user parameters.

Quick start (Windows)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install runtime dependencies (file is currently named `requirement.txt`):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirement.txt
```

3. Run the GUI:

```powershell
python GUI.py
```

Build a distributable executable (PyInstaller)

There is a helper script that uses PyInstaller:

```powershell
# Activate the venv first
.\.venv\Scripts\Activate.ps1
# One-dir build
.\scripts\build_exe.ps1
# Or single-file build
.\scripts\build_exe.ps1 -OneFile
```

Create an installer (Inno Setup)

An Inno Setup script template is included at `scripts/installer/gcode_installer.iss` and a helper `scripts/make_installer.ps1` will attempt to:
 - Run the PyInstaller build (calls `scripts/build_exe.ps1`) and
 - Invoke Inno Setup (ISCC.exe) if it is installed on your machine.

If Inno Setup is not installed, the helper will leave the `dist/` output and instructions are printed so you can build the installer manually.

Notes / troubleshooting
- The repository contains a minimal smoke test using `pytest` in `tests/test_smoke.py`.
- The requirements file is currently named `requirement.txt` — consider renaming to `requirements.txt` for tooling compatibility.
- If images or data files are missing in the PyInstaller build, adjust `--add-data` lines in `scripts/build_exe.ps1`.

If you want, I can (A) run a full build here (PyInstaller) and attempt to create the installer (if Inno Setup is present), or (B) update `requirement.txt` -> `requirements.txt` and add `pytest` to it. Tell me which.

```
