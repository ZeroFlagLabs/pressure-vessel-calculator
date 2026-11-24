"""Input validation shared by the GUI and calculation dispatcher.

All numeric values are converted to finite floats before any calculations run.
Raise ValueError with one user-readable message per invalid field.
"""

import math


_FIELDS = (
    ("od", "OD"),
    ("id", "ID"),
    ("yield_strength", "Material Yield"),
    ("working_pressure", "Working Pressure"),
    ("test_pressure", "Test Pressure"),
    ("derating_factor", "Temperature Derating Factor"),
    ("axial_load", "Additional Axial Load"),
)

_OPTIONAL_DEFAULTS = {"derating_factor": 1.0, "axial_load": 0.0}


def validate_inputs(inputs):
    """Return validated inputs or raise ValueError with actionable errors.

    The derating factor and additional axial load are optional. All other
    numeric inputs, pressure direction and end configuration are required.
    """
    validated = dict(inputs)
    errors = []

    for key, label in _FIELDS:
        value = inputs.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            if key in _OPTIONAL_DEFAULTS:
                value = _OPTIONAL_DEFAULTS[key]
            else:
                errors.append(f"{label} is required")
                continue

        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            errors.append(f"{label} must be a valid number")
            continue

        if not math.isfinite(number):
            errors.append(f"{label} must be a finite number")
            continue

        validated[key] = number

    for key, label in (("od", "OD"), ("id", "ID"),
                       ("yield_strength", "Material Yield")):
        if key in validated and isinstance(validated[key], float) and validated[key] <= 0:
            errors.append(f"{label} must be greater than zero")

    if all(isinstance(validated.get(key), float) for key in ("od", "id")):
        if validated["od"] <= validated["id"]:
            errors.append("OD must be greater than ID")

    for key, label in (("working_pressure", "Working Pressure"),
                       ("test_pressure", "Test Pressure")):
        if isinstance(validated.get(key), float) and validated[key] < 0:
            errors.append(f"{label} must not be negative")

    if all(isinstance(validated.get(key), float)
           for key in ("working_pressure", "test_pressure")):
        if validated["test_pressure"] < validated["working_pressure"]:
            errors.append("Test Pressure must be greater than or equal to Working Pressure")

    if isinstance(validated.get("derating_factor"), float):
        if not 0 < validated["derating_factor"] <= 1:
            errors.append("Temperature Derating Factor must be greater than zero and no more than 1")

    if inputs.get("pressure_type") not in ("internal", "external"):
        errors.append("Select a valid Pressure Direction")
    if inputs.get("end_condition") not in ("open", "capped"):
        errors.append("Select a valid End Configuration")

    if errors:
        raise ValueError("\n".join(errors))
    return validated
