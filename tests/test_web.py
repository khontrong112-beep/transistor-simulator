"""HTTP tests for the Flask routes using the built-in test client."""

import unittest

from app import app

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


class WebRouteTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_get_index_shows_the_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Calculate DC Bias", response.data)
        self.assertIn(b'name="vcc"', response.data)

    def test_post_calculates_the_operating_point(self):
        response = self.client.post("/calculate", data=LAB_FORM)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Active", body)
        self.assertIn("8.05", body)  # VCE
        self.assertIn("1.23", body)  # IC in mA
        self.assertIn("1.94", body)  # VB
        self.assertIn("ขั้นตอนการคำนวณ", body)  # substitution trail
        self.assertIn("2.164", body)  # VTH shown in the steps panel

    def test_post_invalid_resistor_returns_a_readable_error(self):
        response = self.client.post("/calculate", data={**LAB_FORM, "r1": "0"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("ข้อมูลไม่ถูกต้อง", body)
        self.assertIn("มากกว่า 0", body)
        self.assertNotIn('class="results"', body)

    def test_post_non_numeric_value_does_not_crash(self):
        response = self.client.post("/calculate", data={**LAB_FORM, "r2": "abc"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("ต้องเป็นตัวเลข", body)

    def test_post_uses_the_unit_dropdowns(self):
        data = {
            "vcc": "12",
            "vcc_unit": "v",
            "r1": "100",
            "r1_unit": "kohm",
            "r2": "22",
            "r2_unit": "kohm",
            "rc": "2200",
            "rc_unit": "ohm",
            "re": "1000",
            "re_unit": "ohm",
            "beta": "100",
            "vbe": "700",
            "vbe_unit": "mv",
        }
        response = self.client.post("/calculate", data=data)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("8.05", body)  # VCE is unchanged by the unit choice


if __name__ == "__main__":
    unittest.main()
