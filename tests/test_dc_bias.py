"""Unit tests for the engineering calculations in ``dc_bias.py``.

Run from the project root:

    python -m unittest discover -s tests -v
"""

import unittest

from dc_bias import (
    REGION_ACTIVE,
    REGION_CUTOFF,
    REGION_SATURATION,
    BiasInputError,
    calculate,
    parse_form,
)

LAB_FORM = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
    "unit": "kohm",
}


def form(**overrides):
    data = dict(LAB_FORM)
    data.update(overrides)
    return data


class ReferenceOperatingPointTest(unittest.TestCase):
    """Reference values worked out by hand for the lab data set."""

    def setUp(self):
        self.result = calculate(parse_form(LAB_FORM))

    def test_region_is_forward_active(self):
        self.assertEqual(self.result.region, REGION_ACTIVE)
        self.assertEqual(self.result.warnings, ())

    def test_equivalent_circuit(self):
        self.assertAlmostEqual(self.result.vth, 2.1639, places=3)
        self.assertAlmostEqual(self.result.rth_kohm, 18.0328, places=3)

    def test_currents(self):
        self.assertAlmostEqual(self.result.ib_ua, 12.2986, places=3)
        self.assertAlmostEqual(self.result.ic_ma, 1.2299, places=3)
        self.assertAlmostEqual(self.result.ie_ma, 1.2422, places=3)

    def test_terminal_voltages(self):
        self.assertAlmostEqual(self.result.vb, 1.9422, places=3)
        self.assertAlmostEqual(self.result.ve, 1.2422, places=3)
        self.assertAlmostEqual(self.result.vc, 9.2943, places=3)
        self.assertAlmostEqual(self.result.vce, 8.0522, places=3)

    def test_kirchhoff_around_the_collector_emitter_loop(self):
        circuit = parse_form(LAB_FORM)
        expected = circuit.vcc - self.result.ic * circuit.rc - self.result.ie * circuit.re
        self.assertAlmostEqual(self.result.vce, expected, places=9)


class UnitHandlingTest(unittest.TestCase):
    def test_ohms_and_kilohms_are_equivalent(self):
        in_kohm = calculate(parse_form(LAB_FORM))
        in_ohm = calculate(
            parse_form(
                form(
                    r1="100000",
                    r2="22000",
                    rc="2200",
                    re="1000",
                    unit="ohm",
                )
            )
        )
        self.assertAlmostEqual(in_kohm.ic, in_ohm.ic, places=12)
        self.assertAlmostEqual(in_kohm.vce, in_ohm.vce, places=12)

    def test_per_field_units_are_independent(self):
        mixed = {
            "vcc": "12",
            "vcc_unit": "v",
            "r1": "100",
            "r1_unit": "kohm",
            "r2": "22000",
            "r2_unit": "ohm",
            "rc": "2.2",
            "rc_unit": "kohm",
            "re": "1000",
            "re_unit": "ohm",
            "beta": "100",
            "vbe": "700",
            "vbe_unit": "mv",
        }
        reference = calculate(parse_form(LAB_FORM))
        result = calculate(parse_form(mixed))
        self.assertAlmostEqual(reference.ic, result.ic, places=12)
        self.assertAlmostEqual(reference.vce, result.vce, places=12)

    def test_unknown_unit_is_rejected(self):
        with self.assertRaises(BiasInputError) as ctx:
            parse_form(form(r1_unit="furlong"))
        self.assertEqual(ctx.exception.field_name, "r1_unit")


class OperatingRegionTest(unittest.TestCase):
    def test_cutoff_when_divider_voltage_below_vbe(self):
        result = calculate(parse_form(form(r2="1")))
        self.assertEqual(result.region, REGION_CUTOFF)
        self.assertEqual(result.ic, 0.0)
        self.assertAlmostEqual(result.vce, 12.0, places=9)
        self.assertTrue(result.warnings)

    def test_saturation_when_collector_is_pulled_below_emitter(self):
        result = calculate(
            parse_form(
                form(vcc="5", r1="47", r2="100", rc="1", re="0.1")
            )
        )
        self.assertEqual(result.region, REGION_SATURATION)
        self.assertLessEqual(result.vce, 0.2)
        self.assertTrue(result.warnings)


class InputValidationTest(unittest.TestCase):
    def assert_field_error(self, data, field_name):
        with self.assertRaises(BiasInputError) as ctx:
            parse_form(data)
        self.assertEqual(ctx.exception.field_name, field_name)
        self.assertTrue(ctx.exception.message)

    def test_zero_resistor_is_rejected(self):
        self.assert_field_error(form(r1="0"), "r1")

    def test_negative_resistor_is_rejected(self):
        self.assert_field_error(form(rc="-2.2"), "rc")

    def test_zero_beta_is_rejected(self):
        self.assert_field_error(form(beta="0"), "beta")

    def test_non_numeric_value_is_rejected(self):
        self.assert_field_error(form(r2="abc"), "r2")

    def test_missing_value_is_rejected(self):
        self.assert_field_error(form(vcc=""), "vcc")

    def test_zero_supply_is_rejected(self):
        self.assert_field_error(form(vcc="0"), "vcc")

    def test_vbe_must_be_below_supply(self):
        self.assert_field_error(form(vbe="12"), "vbe")


if __name__ == "__main__":
    unittest.main()
