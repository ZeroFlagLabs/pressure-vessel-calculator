from calculator import *
from input_validation import validate_inputs


def calculate_case(inputs):
    """
    Main case selector and dispatcher.

    - Determines thin vs thick wall using Roark definition (R_mean / t)
    - Selects correct calculation function based on:
        - Pressure type (internal / external)
        - End condition (capped / open)
    - Runs both working and test cases
    """

    # Shared input validation (also protects direct, non-GUI calls).
    inputs = validate_inputs(inputs)

    # =========================
    # GEOMETRY
    # =========================
    od = inputs["od"]
    id_ = inputs["id"]

    ro = od / 2.0                 # Outer radius
    ri = id_ / 2.0                # Inner radius
    t = ro - ri                   # Wall thickness
    r_mean = (ro + ri) / 2.0      # Mean radius (Roark definition)

    # =========================
    # WALL THICKNESS RATIO (Roark)
    # =========================
    # Thin if R/t > 10, else thick
    ratio = r_mean / t

    # =========================
    # SELECT FUNCTION SET
    # =========================
    pressure_type = inputs["pressure_type"]
    end_condition = inputs["end_condition"]

    if pressure_type == "internal":
        if end_condition == "capped":
            thick_func = internal_capped_thick
            thin_func = internal_capped_thin
        elif end_condition == "open":
            thick_func = internal_open_thick
            thin_func = internal_open_thin
        else:
            raise ValueError("Invalid end condition")

    elif pressure_type == "external":
        if end_condition == "capped":
            thick_func = external_capped_thick
            thin_func = external_capped_thin
        elif end_condition == "open":
            thick_func = external_open_thick
            thin_func = external_open_thin
        else:
            raise ValueError("Invalid end condition")

    else:
        raise ValueError("Invalid pressure type")

    # =========================
    # THIN / THICK SELECTION
    # =========================
    if ratio <= 10:
        func = thick_func
        wall_type = "Thick Wall"
    else:
        func = thin_func
        wall_type = "Thin Wall"

    # =========================
    # RUN CALCULATIONS
    # =========================
    # Allowables:
    # - Working: 2/3 SMYS
    # - Test: 0.9 SMYS (API 6X)
    working = func(inputs, inputs["working_pressure"], 2 / 3, "Working")
    test = func(inputs, inputs["test_pressure"], 0.9, "Test")

    # =========================
    # RETURN RESULTS
    # =========================
    return {
        "wall_type": wall_type,
        "ratio": ratio,
        "working": working,
        "test": test,
    }