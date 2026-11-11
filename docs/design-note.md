# Design Note — BJT DC Bias Web App

## Problem

Students need to see the difference between an HTML file that only *looks*
like an application and a real client–server program. The deliverable must
therefore be served by Python, accept user input over HTTP, and compute the
answer on the server.

## Scope (Lab 02)

In scope:

- one circuit: NPN common emitter, voltage-divider bias
- one analysis: DC operating point with the forward-active approximation
- input validation and operating-region warnings
- automated tests for both the engineering math and the HTTP layer

Out of scope (later weeks): AC small signal, Bode plot, transient analysis,
load line, multiple bias templates, SPICE, FET.

## Architecture

```
Browser ──POST /calculate──> Flask route ──> dc_bias.parse_form
                                    │              │
                                    │              └─> dc_bias.calculate
                                    └─> templates/index.html (Jinja)
```

Decisions:

1. **Separate engineering module.** `dc_bias.py` knows nothing about Flask or
   HTML, so a wrong equation is caught by a unit test in milliseconds instead
   of by clicking through a browser.
2. **Validate at the boundary.** `parse_form` converts strings and units into
   SI values once, so no equation has to defend against `"abc"` or kΩ.
3. **Warn, do not hide.** Cutoff and saturation results are still displayed,
   but labelled as outside the model's assumption. The alternative — silently
   printing a number that looks valid — is the failure mode this lab is
   designed to teach against.
4. **Two test files.** `test_dc_bias.py` checks physics; `test_web.py` checks
   that a form submission produces HTML containing the right numbers and that
   bad input returns a readable page instead of a 500.
5. **Server-rendered HTML.** No JavaScript framework: the point of the lab is
   the request/response cycle, and a single template keeps the diff readable.

## Data contract

| Field | Unit | Validation |
| --- | --- | --- |
| `vcc` | V | `> 0` |
| `r1`, `r2`, `rc`, `re` | Ω or kΩ | `> 0` after unit conversion |
| `beta` | – | `> 0` |
| `vbe` | V | `0 ≤ VBE < VCC` |
| `unit` | `ohm` \| `kohm` | one of the two |

Result object: `vth`, `rth`, `ib`, `ic`, `ie`, `vb`, `ve`, `vc`, `vce`,
`region`, `warnings`.

## Known limitations

- β and VBE are constants; real devices vary with current and temperature.
- No Early effect, so the output is optimistic about `r_o`.
- Saturation is detected with a fixed `VCE_SAT = 0.2 V`, not solved.
- Cutoff is detected from the unloaded divider voltage `VTH ≤ VBE`, which
  ignores base leakage.

## Alternatives considered

- **Client-side JavaScript calculator** — rejected: it would not demonstrate a
  Python backend, and the lab's whole point is the server round trip.
- **Solving the full Ebers–Moll model** — rejected: needs a numerical solver
  and hides the textbook equations students are expected to reproduce by hand.
- **Single `app.py` with calculations inline** — rejected: untestable math and
  it recreates the "one big file" habit the lab is trying to break.
