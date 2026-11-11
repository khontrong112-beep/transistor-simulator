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
    BiasResult,
    calculate,
    parse_form,
)

app = Flask(__name__)

DEFAULT_FORM = {
    "vcc": "12.0",
    "vcc_unit": "v",
    "r1": "100",
    "r1_unit": "kohm",
    "r2": "22",
    "r2_unit": "kohm",
    "rc": "2.2",
    "rc_unit": "kohm",
    "re": "1.0",
    "re_unit": "kohm",
    "beta": "100",
    "vbe": "0.70",
    "vbe_unit": "v",
}

FORM_FIELDS = tuple(DEFAULT_FORM)

REGION_TITLES = {
    REGION_ACTIVE: "Active region approximation OK",
    REGION_CUTOFF: "Cutoff region — model not applicable",
    REGION_SATURATION: "Saturation — model not applicable",
}

REGION_LEVELS = {
    REGION_ACTIVE: "ok",
    REGION_CUTOFF: "warn",
    REGION_SATURATION: "bad",
}


def _read_form() -> dict[str, str]:
    return {key: request.form.get(key, "").strip() for key in FORM_FIELDS}


UNIT_SYMBOLS = {
    "v": "V",
    "kv": "kV",
    "mv": "mV",
    "ohm": "Ω",
    "kohm": "kΩ",
    "mohm": "MΩ",
}


def _fmt_volts(value: float) -> str:
    if value < 1.0:
        return f"{value * 1e3:g} mV"
    return f"{value:g} V"


def _fmt_ohms(value: float) -> str:
    if value >= 1e6:
        scaled, unit = value / 1e6, "MΩ"
    elif value >= 1e3:
        scaled, unit = value / 1e3, "kΩ"
    else:
        scaled, unit = value, "Ω"
    text = f"{scaled:g}"
    if "." not in text and scaled < 10:
        text += ".0"
    return f"{text} {unit}"


def _circuit_labels(raw: dict[str, str]) -> dict[str, str]:
    """Values printed next to the schematic symbols."""

    unknown = {"vcc": "?", "r1": "?", "r2": "?", "rc": "?", "re": "?", "beta": "?"}
    try:
        circuit = parse_form(raw)
    except BiasInputError:
        return _raw_circuit_labels(raw)
    return {
        "vcc": _fmt_volts(circuit.vcc),
        "r1": _fmt_ohms(circuit.r1),
        "r2": _fmt_ohms(circuit.r2),
        "rc": _fmt_ohms(circuit.rc),
        "re": _fmt_ohms(circuit.re),
        "beta": f"{circuit.beta:g}",
    }


def _raw_circuit_labels(raw: dict[str, str]) -> dict[str, str]:
    """Fallback while the form is invalid: show the text exactly as typed."""

    def label(key: str) -> str:
        value = str(raw.get(key, "")).strip() or "?"
        unit = UNIT_SYMBOLS.get(str(raw.get(f"{key}_unit", "")).strip().lower(), "")
        return f"{value} {unit}".strip()

    return {key: label(key) for key in ("vcc", "r1", "r2", "rc", "re", "beta")}


def _result_rows(result: BiasResult) -> list[dict[str, str]]:
    """Rows of the results table, already formatted for display."""

    return [
        {"symbol": "V<sub>B</sub>", "value": f"{result.vb:.2f}", "unit": "V"},
        {"symbol": "V<sub>E</sub>", "value": f"{result.ve:.2f}", "unit": "V"},
        {"symbol": "V<sub>C</sub>", "value": f"{result.vc:.2f}", "unit": "V"},
        {"symbol": "V<sub>CE</sub>", "value": f"{result.vce:.2f}", "unit": "V"},
        {"symbol": "I<sub>B</sub>", "value": f"{result.ib_ua:.1f}", "unit": "µA"},
        {"symbol": "I<sub>C</sub>", "value": f"{result.ic_ma:.2f}", "unit": "mA"},
        {"symbol": "I<sub>E</sub>", "value": f"{result.ie_ma:.2f}", "unit": "mA"},
    ]


def _steps(circuit, result: BiasResult) -> list[dict[str, str]]:
    """Substitution trail so every displayed number can be re-checked by hand."""

    r1, r2, rc, re = (
        _fmt_ohms(circuit.r1),
        _fmt_ohms(circuit.r2),
        _fmt_ohms(circuit.rc),
        _fmt_ohms(circuit.re),
    )
    beta = f"{circuit.beta:g}"

    if result.region == REGION_CUTOFF:
        return [
            {
                "name": "V<sub>TH</sub>",
                "expr": f"{circuit.vcc:g} V × {r2} / ({r1} + {r2})",
                "value": f"{result.vth:.3f} V",
            },
            {
                "name": "เงื่อนไข",
                "expr": "V<sub>TH</sub> ≤ V<sub>BE</sub> → ไม่มีกระแสฐาน",
                "value": "I<sub>B</sub> = 0",
            },
        ]

    return [
        {
            "name": "V<sub>TH</sub>",
            "expr": f"{circuit.vcc:g} V × {r2} / ({r1} + {r2})",
            "value": f"{result.vth:.3f} V",
        },
        {
            "name": "R<sub>TH</sub>",
            "expr": f"{r1} × {r2} / ({r1} + {r2})",
            "value": f"{result.rth_kohm:.2f} kΩ",
        },
        {
            "name": "I<sub>B</sub>",
            "expr": (
                f"({result.vth:.3f} V − {circuit.vbe:g} V) / "
                f"({result.rth_kohm:.2f} kΩ + ({beta}+1) × {re})"
            ),
            "value": f"{result.ib_ua:.2f} µA",
        },
        {
            "name": "I<sub>C</sub>",
            "expr": f"{beta} × {result.ib_ua:.2f} µA",
            "value": f"{result.ic_ma:.3f} mA",
        },
        {
            "name": "V<sub>CE</sub>",
            "expr": (
                f"{circuit.vcc:g} V − {result.ic_ma:.3f} mA × {rc} "
                f"− {result.ie_ma:.3f} mA × {re}"
            ),
            "value": f"{result.vce:.2f} V",
        },
    ]


def _status_detail(result: BiasResult) -> str:
    if result.region == REGION_ACTIVE:
        return f"V<sub>CE</sub> = {result.vce:.2f} V &gt; 0.2 V (transistor in active region)"
    if result.region == REGION_CUTOFF:
        return (
            f"V<sub>TH</sub> = {result.vth:.2f} V ≤ V<sub>BE</sub>: "
            "no base current, equations do not apply"
        )
    return (
        f"V<sub>CE</sub> = {result.vce:.2f} V ≤ 0.2 V "
        "(transistor saturated, equations do not apply)"
    )


@app.get("/")
def index():
    form = dict(DEFAULT_FORM)
    return render_template(
        "index.html",
        form=form,
        circuit=_circuit_labels(form),
        result=None,
        rows=[],
        steps=[],
        error=None,
        status=None,
    )


@app.post("/calculate")
def calculate_route():
    raw = _read_form()
    labels = _circuit_labels(raw)
    try:
        circuit = parse_form(raw)
        result = calculate(circuit)
    except BiasInputError as exc:
        return render_template(
            "index.html",
            form=raw,
            circuit=labels,
            result=None,
            rows=[],
            steps=[],
            error=exc,
            status=None,
        )

    return render_template(
        "index.html",
        form=raw,
        circuit=labels,
        result=result,
        rows=_result_rows(result),
        steps=_steps(circuit, result),
        error=None,
        status={
            "level": REGION_LEVELS[result.region],
            "title": REGION_TITLES[result.region],
            "detail": _status_detail(result),
            "warnings": result.warnings,
        },
    )


if __name__ == "__main__":
    app.run(debug=True)
