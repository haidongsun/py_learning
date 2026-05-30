# AGENTS.md

## Project

Python learning/experimentation sandbox. Single entry point: `main.py`. Data files live in `resource/`.

## Environment

- Python 3.10.7 (CPython)
- `.venv` exists but is incomplete — pandas is installed in system Python only, not in the venv
- JetBrains IDE project (`.idea/`)

## Running

```bash
python main.py          # uses system Python (pandas available there)
```

The venv must be activated or dependencies installed before it can run inside `.venv`.

## Dependencies

`main.py` requires **pandas** and **openpyxl** (the Excel engine for `pd.read_excel`). openpyxl is NOT currently installed anywhere — running `main.py` will fail on `pd.read_excel()` until it is added:

```bash
pip install openpyxl
```

## Gotchas

- `resource/` paths use raw Windows strings (`r'resource/test.xlsx'`) — keep this pattern for local file references
- No requirements.txt exists; dependencies are implicitly system-level