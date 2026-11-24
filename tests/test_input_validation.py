"""Regression tests for input validation and Roark case selection.

Run from the project root: python -m unittest discover -s tests -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cases import calculate_case
from input_validation import validate_inputs


VALID = {
    "od": 6.0,
    "id": 2.0,
    "working_pressure": 1000.0,
    "test_pressure": 1500.0,
    "yield_strength": 80000.0,
    "derating_factor": 1.0,
    "axial_load": 0.0,
    "pressure_type": "internal",
    "end_condition": "capped",
}


class InputValidationTests(unittest.TestCase):
    def reject(self, key, value, expected_message):
        with self.subTest(key=key, value=value):
            with self.assertRaisesRegex(ValueError, expected_message):
                calculate_case(dict(VALID, **{key: value}))

    def test_positive_geometry_and_yield(self):
        for key in ("od", "id", "yield_strength"):
            for value in (0, -0.5):
                self.reject(key, value, "must be greater than zero")
        self.reject("id", 6, "OD must be greater than ID")
        self.reject("id", 7, "OD must be greater than ID")

    def test_pressure_validation(self):
        self.reject("working_pressure", -1, "Working Pressure must not be negative")
        self.reject("test_pressure", -1, "Test Pressure must not be negative")
        self.reject("test_pressure", 999, "Test Pressure must be greater than")
        result = calculate_case(dict(VALID, working_pressure=0.0, test_pressure=0.0))
        self.assertEqual(result["working"]["sigma_vm"], 0)
        self.assertEqual(result["test"]["sigma_vm"], 0)

    def test_derating_bounds(self):
        for value in (0, -0.1, 1.001):
            self.reject("derating_factor", value, "Temperature Derating Factor")
        self.assertEqual(validate_inputs(dict(VALID, derating_factor=1))["derating_factor"], 1)
        self.assertEqual(validate_inputs(dict(VALID, derating_factor=0.5))["derating_factor"], 0.5)

    def test_nonfinite_and_invalid_numbers(self):
        for key in ("od", "id", "yield_strength", "working_pressure",
                    "test_pressure", "derating_factor", "axial_load"):
            for value in ("nan", float("inf"), float("-inf"), "1e9999"):
                self.reject(key, value, "finite number")
            self.reject(key, "not a number!", "valid number")

    def test_missing_required_or_choices(self):
        for key in ("od", "id", "yield_strength", "working_pressure", "test_pressure"):
            self.reject(key, "", "is required")
        self.reject("pressure_type", "sideways", "Pressure Direction")
        self.reject("end_condition", "unknown", "End Configuration")

    def test_optional_defaults_and_axial_sign(self):
        clean = validate_inputs(dict(VALID, derating_factor="  ", axial_load=""))
        self.assertEqual(clean["derating_factor"], 1.0)
        self.assertEqual(clean["axial_load"], 0.0)
        clean = validate_inputs({k: v for k, v in VALID.items()
                                 if k not in ("derating_factor", "axial_load")})
        self.assertEqual(clean["derating_factor"], 1.0)
        self.assertEqual(clean["axial_load"], 0.0)
        result_tension = calculate_case(dict(VALID, axial_load=10000.0))
        result_compression = calculate_case(dict(VALID, axial_load=-10000.0))
        self.assertGreater(result_tension["working"]["sigma_long"],
                           result_compression["working"]["sigma_long"])

    def test_strings_are_converted_to_numbers(self):
        raw = {k: str(v) if isinstance(v, (float, int)) else v for k, v in VALID.items()}
        cleaned = validate_inputs(raw)
        self.assertIsInstance(cleaned["od"], float)
        self.assertEqual(calculate_case(raw)["wall_type"], "Thick Wall")

    def test_existing_roark_selection_and_shear(self):
        for pressure_type in ("internal", "external"):
            for end_condition in ("capped", "open"):
                with self.subTest(pressure_type=pressure_type, end_condition=end_condition):
                    inputs = dict(VALID, pressure_type=pressure_type,
                                  end_condition=end_condition)
                    result = calculate_case(inputs)
                    self.assertEqual(result["wall_type"], "Thick Wall")
                    self.assertAlmostEqual(result["working"]["tau"], 1125.0)
                    self.assertAlmostEqual(result["working"]["allowable_vm"], 80000 * 2/3)
                    self.assertAlmostEqual(result["test"]["allowable_vm"], 80000 * 0.9)
                    self.assertEqual(result["working"]["sigma_radial"],
                                     -1000 if pressure_type == "internal" else 0)
        # Mean-radius/thickness > 10, with the original membrane method.
        thin = calculate_case(dict(VALID, od=21.002, id=19.002))
        self.assertEqual(thin["wall_type"], "Thin Wall")
        self.assertIsNone(thin["working"]["tau"])


if __name__ == "__main__":
    unittest.main()
