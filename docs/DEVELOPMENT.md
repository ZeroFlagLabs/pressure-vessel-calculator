# Development and testing

Windows, Python 3.13.16, PySide6 6.12.0 and PyInstaller 6.22.3 were used for the first public version.

```powershell
py -3.13 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe src\main.py --self-test
& .\.venv\Scripts\python.exe tools\Build-OneFile-Portable.py
```

For normal development double-click `tools/run_app.bat`. The source engine is in `src/calculator.py`, `src/cases.py` and `src/input_validation.py`; geometry selection is separate. Main interface, Settings and Inspector are in `src/main.py`, `src/ui/` and `src/inspect_results.py`. The PNG renderer is `src/snapshot.py`. Original schematic images can be regenerated using `tools/generate_schematics.py`.

The legacy-equivalence test uses the expected digest of 4,456 cases evaluated with the final original v1.3 executable. This is regression evidence, not independent certification of the engineering model. Geometry selection is checked against a deterministic dense grid of physical configurations. The source/frozen application self-test exercises geometry, both result tabs, report export, Settings and update handling.
