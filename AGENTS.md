# AGENTS.md — conventions for AI assistants

This repository is a teaching example for ENG29 2121. Correctness of the
electrical model matters more than cleverness of the code.

## Layout rules

- `dc_bias.py` — pure Python. **No Flask import, no HTML, no request objects.**
  Every equation lives here so it can be unit tested without a web server.
- `app.py` — HTTP only: read the form, call `parse_form` + `calculate`,
  render a template. Never re-implement an equation here.
- `templates/index.html` — presentation only. No physics, no arithmetic beyond
  number formatting. Unit conversion happens in Python.
- `static/style.css` — styling only.
- `tests/` — one file per concern: engineering math vs. HTTP behaviour.

## Rules

1. Keep SI units inside Python: volts, ohms, amperes. Convert kΩ/Ω at the
   parsing boundary (`parse_form`).
2. Any new calculation needs a unit test with a hand-checked reference value in
   the same commit.
3. Anything outside the forward-active region must surface a warning. Never
   present a cutoff or saturation result as a valid operating point.
4. Invalid input returns the form with a readable message; it must never raise
   a traceback to the browser.
5. Do not add dependencies without updating `requirements.txt` and the README.
6. Never commit `.venv/`, `__pycache__/`, `.env` or credentials.

## Commands

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m flask --app app run --debug
```
