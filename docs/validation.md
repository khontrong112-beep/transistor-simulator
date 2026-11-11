# Validation — hand calculation vs. program output

Everything below was computed by hand (calculator only, no code) and then
compared with the value printed by the Flask app. Both must agree.

## 1. Reference data set (from the lab sheet)

`VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`,
`β = 100`, `VBE = 0.70 V`

### Step 1 — Thevenin equivalent of the base divider

```
VTH = VCC · R2 / (R1 + R2) = 12 × 22 / 122 = 2.1639 V
RTH = R1 · R2 / (R1 + R2) = 100 × 22 / 122 = 18.0328 kΩ
```

### Step 2 — Base current

```
IB = (VTH − VBE) / (RTH + (β + 1)·RE)
   = (2.1639 − 0.70) / (18 032.8 + 101 × 1000)
   = 1.4639 / 119 032.8
   = 12.298 µA
```

### Step 3 — Currents

```
IC = β · IB     = 100 × 12.298 µA = 1.2298 mA
IE = (β+1) · IB = 101 × 12.298 µA = 1.2421 mA
```

### Step 4 — Voltages

```
VE  = IE · RE   = 1.2421 mA × 1 kΩ = 1.2421 V
VB  = VE + VBE  = 1.2421 + 0.70    = 1.9421 V
VC  = VCC − IC·RC = 12 − 1.2298 mA × 2.2 kΩ = 12 − 2.7056 = 9.2944 V
VCE = VC − VE   = 9.2944 − 1.2421  = 8.0523 V
```

### Step 5 — Cross-check (collector–emitter loop)

```
VCE = VCC − IC·RC − IE·RE
    = 12 − 2.7056 − 1.2421
    = 8.0523 V        ✓ matches step 4
```

### Comparison

| Quantity | Hand calculation | Web app | Agree? |
| --- | --- | --- | --- |
| VTH | 2.164 V | 2.164 V | ✓ |
| RTH | 18.033 kΩ | 18.033 kΩ | ✓ |
| IB | 12.299 µA | 12.299 µA | ✓ |
| IC | 1.230 mA | 1.230 mA | ✓ |
| IE | 1.242 mA | 1.242 mA | ✓ |
| VB | 1.942 V | 1.942 V | ✓ |
| VE | 1.242 V | 1.242 V | ✓ |
| VC | 9.294 V | 9.294 V | ✓ |
| VCE | 8.052 V | 8.052 V | ✓ |
| Region | `VTH > VBE`, `VCE = 8.05 V > 0.2 V` → Active | Active | ✓ |

`IC·RC + IE·RE + VCE = 2.706 + 1.242 + 8.052 = 12.000 V = VCC` — the operating
point is self-consistent.

## 2. Unit handling

The same circuit entered in ohms
(`R1 = 100000`, `R2 = 22000`, `RC = 2200`, `RE = 1000`, unit = Ω) must produce
an identical result. Checked by
`UnitHandlingTest.test_ohms_and_kilohms_are_equivalent` — currents and voltages
agree to 12 decimal places.

## 3. Outside the model — Cutoff

`VCC = 12 V, R1 = 100 kΩ, R2 = 1 kΩ`

```
VTH = 12 × 1 / 101 = 0.1188 V < VBE = 0.70 V
```

The base–emitter junction is not forward biased, so the forward-active
equations cannot be used. Expected and observed behaviour:

| Quantity | Expected by physics | Web app |
| --- | --- | --- |
| IB, IC, IE | 0 | 0 |
| VE | 0 V | 0.000 V |
| VB | 0.119 V (unloaded divider) | 0.119 V |
| VC | 12 V (no drop across RC) | 12.000 V |
| VCE | 12 V | 12.000 V |
| Region | Cutoff + warning | Cutoff + warning |

## 4. Outside the model — Saturation / near saturation

Saturation example: `VCC = 5 V, R1 = 47 kΩ, R2 = 100 kΩ, RC = 1 kΩ,
RE = 0.1 kΩ, β = 100, VBE = 0.7 V`

```
VTH = 3.401 V, RTH = 31.973 kΩ
IB  = (3.401 − 0.7) / (31 973 + 101 × 100) = 64.2 µA
IC  = 6.42 mA  →  VC = 5 − 6.42 mA × 1 kΩ = −1.42 V
```

A negative `VC` is impossible, so the transistor is saturated and the model
answer is meaningless. The app reports region = **Saturation** with a warning
instead of presenting −1.42 V as a valid collector voltage.

Near-saturation example: reference circuit with `RC = 8.5 kΩ`

```
VC = 12 − 1.230 mA × 8.5 kΩ = 1.546 V
VCE = 1.546 − 1.242 = 0.304 V   → 0.2 V < VCE < 1.0 V
```

Result is shown with a "close to saturation" warning: the number is still in
the forward-active region, but only just.

## 5. Input validation

| Input | Expected | Observed |
| --- | --- | --- |
| `R1 = 0` | error on R1 | "R1 ต้องมากกว่า 0 Ω" |
| `RC = −2.2` | error on RC | "RC ต้องมากกว่า 0 Ω" |
| `β = 0` | error on β | "β ต้องมากกว่า 0" |
| `R2 = abc` | non-numeric error | "R2 ต้องเป็นตัวเลข (ได้รับ: abc)" |
| `VCC` empty | missing-field error | "กรุณากรอกค่า VCC" |
| `VCC = 0` | error on VCC | "VCC ต้องมากกว่า 0 V" |
| `VBE = 12` (VBE ≥ VCC) | error on VBE | "VBE ต้องอยู่ระหว่าง 0 V ถึง VCC" |

In every case the response is the form again with HTTP 200 and an error banner.
No traceback reaches the browser.

## 6. Automated tests

```
$ python -m unittest discover -s tests -v
...
Ran 19 tests in 0.062s

OK
```

- 15 tests cover `dc_bias.py`: reference operating point, Kirchhoff check, unit
  equivalence, cutoff, saturation, and seven validation cases.
- 4 tests cover the HTTP layer: `GET /`, valid POST, invalid resistor POST, and
  non-numeric POST.
