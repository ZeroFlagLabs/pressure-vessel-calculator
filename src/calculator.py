import math


# ==========================================================
# CASE WRAPPERS (DISPATCH TO COMMON FUNCTIONS)
# ==========================================================

# Internal Pressure
def internal_capped_thick(inputs, pressure, allowable_factor, label):
    return thick_common(inputs, pressure, allowable_factor, label, capped=True, external=False)

def internal_capped_thin(inputs, pressure, allowable_factor, label):
    return thin_common(inputs, pressure, allowable_factor, label, capped=True, external=False)

def internal_open_thick(inputs, pressure, allowable_factor, label):
    return thick_common(inputs, pressure, allowable_factor, label, capped=False, external=False)

def internal_open_thin(inputs, pressure, allowable_factor, label):
    return thin_common(inputs, pressure, allowable_factor, label, capped=False, external=False)


# External Pressure
def external_capped_thick(inputs, pressure, allowable_factor, label):
    return thick_common(inputs, pressure, allowable_factor, label, capped=True, external=True)

def external_capped_thin(inputs, pressure, allowable_factor, label):
    return thin_common(inputs, pressure, allowable_factor, label, capped=True, external=True)

def external_open_thick(inputs, pressure, allowable_factor, label):
    return thick_common(inputs, pressure, allowable_factor, label, capped=False, external=True)

def external_open_thin(inputs, pressure, allowable_factor, label):
    return thin_common(inputs, pressure, allowable_factor, label, capped=False, external=True)


# ==========================================================
# THICK WALL CALCULATION (LAMÉ EQUATIONS)
# ==========================================================

def thick_common(inputs, pressure, allowable_factor, label, capped, external):
    """
    Thick wall cylinder stresses using Lamé equations.

    Assumptions:
    - Elastic behaviour
    - Uniform pressure loading
    - No temperature gradients
    """

    # -------------------------
    # INPUTS
    # -------------------------
    od = inputs["od"]
    id_ = inputs["id"]
    yield_strength = inputs["yield_strength"]
    # Apply temperature derating only for Working condition
    derating = inputs["derating_factor"] if label == "Working" else 1.0
    axial_load = inputs.get("axial_load", 0.0)

    # -------------------------
    # GEOMETRY
    # -------------------------
    ro = od / 2.0
    ri = id_ / 2.0

    denom = ro**2 - ri**2           # Lamé denominator
    area = math.pi * (ro**2 - ri**2)

    # -------------------------
    # STRESS CALCULATION
    # -------------------------
    if external:
        # External pressure (compressive)
        sigma_hoop = -pressure * (2.0 * ro**2 / denom)
        sigma_radial = 0.0  # At the inner surface (r = ri)

        if capped:
            sigma_long = -pressure * (ro**2 / denom)
        else:
            sigma_long = 0.0

    else:
        # Internal pressure
        sigma_hoop = pressure * ((ro**2 + ri**2) / denom)
        sigma_radial = -pressure

        if capped:
            sigma_long = pressure * (ri**2 / denom)
        else:
            sigma_long = 0.0

    # -------------------------
    # AXIAL LOAD CONTRIBUTION
    # -------------------------
    sigma_long += axial_load / area

    # -------------------------
    # VON MISES STRESS
    # -------------------------
    sigma_vm = math.sqrt(
        0.5 * (
            (sigma_long - sigma_hoop) ** 2 +
            (sigma_hoop - sigma_radial) ** 2 +
            (sigma_radial - sigma_long) ** 2
        )
    )

    # -------------------------
    # MAX SHEAR STRESS
    # -------------------------
    tau = (max(sigma_long, sigma_hoop, sigma_radial) -
           min(sigma_long, sigma_hoop, sigma_radial)) / 2.0

    # -------------------------
    # ALLOWABLES (API 6X STYLE)
    # -------------------------
    allowable_vm = allowable_factor * yield_strength * derating
    allowable_tau = allowable_factor * 0.6 * yield_strength * derating

    return build_result(
        label,
        pressure,
        sigma_hoop,
        sigma_long,
        sigma_radial,
        sigma_vm,
        tau,
        allowable_vm,
        allowable_tau,
    )


# ==========================================================
# THIN WALL CALCULATION (ROARK – MEAN RADIUS)
# ==========================================================

def thin_common(inputs, pressure, allowable_factor, label, capped, external):
    """
    Thin wall cylinder stresses using Roark formulation.

    Key assumption:
    - R/t > 10
    - Stress uniform through thickness
    - Mean radius used (Roark definition)
    """

    # -------------------------
    # INPUTS
    # -------------------------
    od = inputs["od"]
    id_ = inputs["id"]
    yield_strength = inputs["yield_strength"]
    # Apply temperature derating only for Working condition
    derating = inputs["derating_factor"] if label == "Working" else 1.0
    axial_load = inputs.get("axial_load", 0.0)

    # -------------------------
    # GEOMETRY
    # -------------------------
    ro = od / 2.0
    ri = id_ / 2.0
    t = ro - ri
    R = (ro + ri) / 2.0            # Mean radius (Roark)

    area = math.pi * (ro**2 - ri**2)

    # -------------------------
    # SIGN CONVENTION
    # -------------------------
    sign = -1.0 if external else 1.0

    # -------------------------
    # STRESSES
    # -------------------------
    sigma_hoop = sign * pressure * R / t
    sigma_radial = 0.0

    if capped:
        sigma_long = sign * pressure * R / (2.0 * t)
    else:
        sigma_long = 0.0

    # Axial load contribution
    sigma_long += axial_load / area

    # -------------------------
    # VON MISES
    # -------------------------
    sigma_vm = math.sqrt(
        0.5 * (
            (sigma_long - sigma_hoop) ** 2 +
            (sigma_hoop - sigma_radial) ** 2 +
            (sigma_radial - sigma_long) ** 2
        )
    )

    # -------------------------
    # ALLOWABLES
    # -------------------------
    allowable_vm = allowable_factor * yield_strength * derating

    return build_result(
        label,
        pressure,
        sigma_hoop,
        sigma_long,
        sigma_radial,
        sigma_vm,
        None,                  # No shear for thin wall
        allowable_vm,
        None,
    )


# ==========================================================
# RESULT PACKAGING
# ==========================================================

def build_result(
    label,
    pressure,
    sigma_hoop,
    sigma_long,
    sigma_radial,
    sigma_vm,
    tau,
    allowable_vm,
    allowable_tau,
):
    """
    Standardised result dictionary used by:
    - UI
    - main.py
    - future reporting/export
    """

    uf_vm = sigma_vm / allowable_vm
    uf_tau = tau / allowable_tau if tau is not None else None

    return {
        "label": label,
        "pressure": pressure,
        "sigma_hoop": sigma_hoop,
        "sigma_long": sigma_long,
        "sigma_radial": sigma_radial,
        "sigma_vm": sigma_vm,
        "tau": tau,
        "allowable_vm": allowable_vm,
        "allowable_tau": allowable_tau,
        "uf_vm": uf_vm,
        "uf_tau": uf_tau,
    }