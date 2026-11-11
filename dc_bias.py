"""DC bias calculations for a BJT common-emitter voltage-divider circuit.

The model is the standard Forward-Active approximation: constant beta and a
constant base-emitter voltage drop (VBE).  It is *not* a SPICE solver, so the
result is only trustworthy while the transistor really is in forward active.
Anything outside that region must be reported with a warning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

# Typical collector-emitter saturation voltage used to detect the limit of the
# forward-active assumption.
VCE_SAT = 0.2
# Below this value the model still runs but the result is flagged as marginal.
NEAR_SATURATION = 1.0

OHM_UNITS = {"ohm": 1.0, "kohm": 1_000.0, "mohm": 1_000_000.0}

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "β (hFE)",
    "vbe": "VBE",
}

REGION_ACTIVE = "active"
REGION_CUTOFF = "cutoff"
REGION_SATURATION = "saturation"


class BiasInputError(ValueError):
    """Raised when the submitted form data cannot be used."""

    def __init__(self, field_name: str, message: str) -> None:
        super().__init__(message)
        self.field_name = field_name
        self.message = message


@dataclass(frozen=True)
class BiasInput:
    """Validated circuit values in SI units (V, ohm, A)."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class BiasResult:
    """DC operating point, all voltages in V and currents in A."""

    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...] = ()

    @property
    def ib_ua(self) -> float:
        return self.ib * 1e6

    @property
    def ic_ma(self) -> float:
        return self.ic * 1e3

    @property
    def ie_ma(self) -> float:
        return self.ie * 1e3

    @property
    def rth_kohm(self) -> float:
        return self.rth / 1e3


def _parse_number(raw: Mapping[str, str], key: str) -> float:
    text = str(raw.get(key, "")).strip()
    if not text:
        raise BiasInputError(key, f"กรุณากรอกค่า {FIELD_LABELS[key]}")
    try:
        value = float(text)
    except ValueError:
        raise BiasInputError(
            key, f"{FIELD_LABELS[key]} ต้องเป็นตัวเลข (ได้รับ: {text})"
        ) from None
    if not math.isfinite(value):
        raise BiasInputError(key, f"{FIELD_LABELS[key]} ต้องเป็นจำนวนจริงจำกัด")
    return value


def _parse_unit(raw: Mapping[str, str]) -> float:
    unit = str(raw.get("unit", "kohm")).strip().lower() or "kohm"
    if unit not in OHM_UNITS:
        raise BiasInputError("unit", "หน่วยความต้านทานไม่ถูกต้อง")
    return OHM_UNITS[unit]


def parse_form(raw: Mapping[str, str]) -> BiasInput:
    """Validate raw form strings and convert them to SI units."""

    scale = _parse_unit(raw)

    vcc = _parse_number(raw, "vcc")
    r1 = _parse_number(raw, "r1") * scale
    r2 = _parse_number(raw, "r2") * scale
    rc = _parse_number(raw, "rc") * scale
    re = _parse_number(raw, "re") * scale
    beta = _parse_number(raw, "beta")
    vbe = _parse_number(raw, "vbe")

    if vcc <= 0:
        raise BiasInputError("vcc", "VCC ต้องมากกว่า 0 V")
    for key, value in (("r1", r1), ("r2", r2), ("rc", rc), ("re", re)):
        if value <= 0:
            raise BiasInputError(key, f"{FIELD_LABELS[key]} ต้องมากกว่า 0 Ω")
    if beta <= 0:
        raise BiasInputError("beta", "β ต้องมากกว่า 0")
    if vbe < 0 or vbe >= vcc:
        raise BiasInputError("vbe", "VBE ต้องอยู่ระหว่าง 0 V ถึง VCC")

    return BiasInput(vcc=vcc, r1=r1, r2=r2, rc=rc, re=re, beta=beta, vbe=vbe)


def calculate(circuit: BiasInput) -> BiasResult:
    """Solve the DC operating point of a voltage-divider biased NPN stage."""

    vth = circuit.vcc * circuit.r2 / (circuit.r1 + circuit.r2)
    rth = circuit.r1 * circuit.r2 / (circuit.r1 + circuit.r2)

    # No forward bias possible: the transistor is cut off.  With IB = 0 the
    # base sits at the unloaded divider voltage, the emitter at ground and the
    # collector at VCC (no drop across RC).
    if vth <= circuit.vbe:
        return BiasResult(
            vth=vth,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=circuit.vcc,
            vce=circuit.vcc,
            region=REGION_CUTOFF,
            warnings=(
                "VTH ≤ VBE: ทรานซิสเตอร์อยู่ในช่วง Cutoff "
                "แบบจำลอง Forward-Active ใช้ไม่ได้",
            ),
        )

    ib = (vth - circuit.vbe) / (rth + (circuit.beta + 1.0) * circuit.re)
    ic = circuit.beta * ib
    ie = ic + ib
    ve = ie * circuit.re
    vb = ve + circuit.vbe
    vc = circuit.vcc - ic * circuit.rc
    vce = vc - ve

    warnings: list[str] = []
    if vce <= VCE_SAT:
        region = REGION_SATURATION
        warnings.append(
            f"VCE = {vce:.3f} V ≤ {VCE_SAT:.2f} V: ทรานซิสเตอร์อิ่มตัว "
            "(Saturation) ค่าที่คำนวณได้ไม่ใช่จุดทำงานจริง"
        )
    else:
        region = REGION_ACTIVE
        if vce < NEAR_SATURATION:
            warnings.append(
                f"VCE = {vce:.3f} V ต่ำใกล้ Saturation "
                "ผลลัพธ์อาจคลาดเคลื่อนจากของจริง"
            )

    return BiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=tuple(warnings),
    )
