"""Flask application for the ENG29 2121 BJT DC bias calculator.

Routes only handle HTTP concerns; every electrical equation lives in
``dc_bias.py`` so the engineering logic stays testable on its own.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    REGION_ACTIVE,
    REGION_CUTOFF,
    REGION_SATURATION,
    BiasInputError,
    calculate,
    parse_form,
)

app = Flask(__name__)

DEFAULT_FORM = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
    "unit": "kohm",
}

FORM_FIELDS = tuple(DEFAULT_FORM)

REGION_LABELS = {
    REGION_ACTIVE: "Active (Forward-Active)",
    REGION_CUTOFF: "Cutoff",
    REGION_SATURATION: "Saturation",
}


def _read_form() -> dict[str, str]:
    return {key: request.form.get(key, "").strip() for key in FORM_FIELDS}


@app.get("/")
def index():
    return render_template(
        "index.html",
        form=dict(DEFAULT_FORM),
        result=None,
        error=None,
        region_labels=REGION_LABELS,
    )


@app.post("/calculate")
def calculate_route():
    raw = _read_form()
    try:
        result = calculate(parse_form(raw))
    except BiasInputError as exc:
        return render_template(
            "index.html",
            form=raw,
            result=None,
            error=exc,
            region_labels=REGION_LABELS,
        )
    return render_template(
        "index.html",
        form=raw,
        result=result,
        error=None,
        region_labels=REGION_LABELS,
    )


if __name__ == "__main__":
    app.run(debug=True)
