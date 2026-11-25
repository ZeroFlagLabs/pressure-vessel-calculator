# Pressure Vessel Calculator

A compact ZeroFlagLabs Windows engineering calculator for cylindrical vessel stress assessment. Version 2.0.8 continues the original v1.0–v1.3 application history, using the final v1.3 equations with the redesigned ZeroFlagLabs interface.


## v2.0.8 status bar centring

Vertically centred status text with a stable baseline; standard font, colours, height and message behaviour retained. Calculation engine unchanged.

## v2.0.7 status bar maintenance

Standardised the full-width status bar: Segoe UI 9 pt regular, dark blue text, neutral grey background and disabled resize grip. Calculation engine unchanged.

## v2.0.6 interface maintenance

Reset restores the full startup state, and action buttons and input alignment are standardised. Calculation equations unchanged.

## v2.0.5 dialogue positioning

Settings and Inspect Results are centred on the main window, with screen-edge protection. Calculations and layout unchanged.

## v2.0.4 input maintenance

Numeric input selection excludes unit suffixes; the calculation engine and input formatting are unchanged.

## Download

Download the [latest Windows portable ZIP](https://github.com/ZeroFlagLabs/pressure-vessel-calculator/releases/latest), extract the single EXE and double-click it. No installation or Python runtime required. The EXE is unsigned; Windows may display a SmartScreen warning. Verify the ZIP checksum shown in the release notes.

## Features

On launch, material yield and both pressures default to zero; temperature derating defaults to 1.00 and additional axial load to zero. Reset restores all geometry, material, loading and configuration startup defaults.

- Enter any two of OD, ID and wall thickness in inches. Independent symmetrical tolerances or limits; third dimension derived.
- Material yield, temperature derating, working/test pressures, optional axial loading and internal/external, open/capped conditions.
- Automatic thin/thick analysis, working and test results, mathematical inspection, copy/save PNG report.
- Settings, detailed Roark case references, case-specific calculation basis in Inspect Results and optional GitHub stable release checks. No automatic downloads or installation.

The original OD/ID minimum-OD/maximum-ID calculation basis is retained. With diameter/thickness tolerances the selector respects physically possible diameter pairs and reports the geometry giving the largest utilisation across both pressure conditions. All results correspond to that one geometry, not independent extrema. See [engineering scope](docs/ENGINEERING_SCOPE.md).

## 📐 Methodology

Calculations are based on:

**Roark’s Formulas for Stress and Strain (6th Edition)**

- Table 28 → Thin-walled cylinders: case 1b (open), case 1c (capped), for either pressure direction
- Table 32 → Thick-walled cylinders: cases 1a (internal/open), 1b (internal/capped), 1c (external/open), 1d (external/capped)

Allowable stresses are based on:

**API 6X (2nd Edition)**

------------------------------------------------------------------------

## 🧱 Geometry

- Outer radius:
  rₒ = OD / 2

- Inner radius:
  rᵢ = ID / 2

- Wall thickness:
  t = rₒ − rᵢ

- Mean radius (thin wall only):
  R = (rₒ + rᵢ) / 2

------------------------------------------------------------------------

## 🔍 Thin vs Thick Wall Criteria

Thin-wall assumptions are valid when:

R / t > 10

Otherwise, thick-wall equations are used.

------------------------------------------------------------------------

## 📊 Stress Definitions

- σ₁ → Longitudinal stress
- σ₂ → Hoop (circumferential) stress
- σ₃ → Radial stress

Sign convention:
- Positive = tensile
- Negative = compressive

------------------------------------------------------------------------

## 📐 Thin-Walled Formulation

Hoop stress:

σ₂ = ± (P · R / t)

Longitudinal stress (capped ends only):

σ₁ = ± (P · R / (2t))

Radial stress:

σ₃ ≈ 0

Notes:
- Internal pressure → positive stresses
- External pressure → negative stresses
- Open ends → no pressure-induced longitudinal stress

------------------------------------------------------------------------

## 📐 Thick-Walled Formulation (Lamé Equations)

Internal pressure:

σ₂ = P · (rₒ² + rᵢ²) / (rₒ² − rᵢ²)
σ₃ = -P

External pressure:

σ₂ = -P · (2rₒ²) / (rₒ² − rᵢ²)
σ₃ = 0 at the inner surface (r = rᵢ)

Longitudinal stress:
- Capped ends → includes pressure term
- Open ends → pressure term = 0

### Stress Evaluation Location

For the thick-walled cylinder cases covered by this calculator (internal or external pressure, open or capped ends, and optional uniform axial load), **maximum von Mises and maximum shear stresses occur at the inner surface (bore)**. The equivalent-stress calculations therefore use the hoop, radial and longitudinal stresses evaluated at that same location.

For external pressure, Roark identifies the radial stress of greatest magnitude as **σ₃ = −q at the outer surface**. At the **inner surface**, radial stress is **σ₃ = 0**. Both values are correct at their respective locations, but individual stress extrema from different locations must not be combined to calculate von Mises or maximum shear stress.

------------------------------------------------------------------------

## ➕ Axial Load Contribution

An optional axial load may be applied:

σ₁ (axial) = F / A

Where:

A = π (rₒ² − rᵢ²)

This contribution is added to the longitudinal stress for all cases.

------------------------------------------------------------------------

## 🧮 Failure Criteria

### Von Mises Stress

σ_vm = √[0.5((σ₁−σ₂)² + (σ₂−σ₃)² + (σ₃−σ₁)²)]

### Shear Stress (Thick Wall Only)

τ_max = (max(σ₁, σ₂, σ₃) − min(σ₁, σ₂, σ₃)) / 2

For internal and external pressure without additional axial load, this agrees with Roark’s maximum-shear expression. The external-pressure radial stress is evaluated at the inner surface, consistent with the hoop-stress location.

------------------------------------------------------------------------

## 📉 Allowable Stress

### Working Condition

σ_allow = (2/3) · yield_strength · derating_factor

### Test Condition

σ_allow = 0.9 · yield_strength

*(Temperature derating applies to working condition only)*

### Shear Allowable

τ_allow = 0.6 · σ_allow

------------------------------------------------------------------------

## ⚠️ Behaviour Notes

- Internal and external pressure cases use consistent sign conventions
- Thin-wall hoop stress uses magnitude with sign applied based on pressure direction
- For capped thin-wall cases, internal and external pressure produce identical von Mises stress due to symmetry of the membrane stress components
- For open thin-wall cases, Von Mises stress differs between internal and external pressure when axial load is present

------------------------------------------------------------------------

## Input validation

The application validates inputs before calculating and displays a list of any errors in the status bar (rather than attempting an invalid calculation).

- **OD and ID:** both greater than zero; OD greater than ID.
- **Material Yield:** greater than zero.
- **Working and Test Pressure:** zero or positive; Test Pressure not lower than Working Pressure.
- **Temperature Derating Factor (optional):** greater than zero and no more than 1; enter **1** for no derating (direct engine calls also default to 1 if omitted).
- **Additional Axial Load (optional):** finite number, including positive (tension), negative (compression) or zero; enter **0 lbf** for no additional axial load (direct engine calls also default to zero if omitted).
- **All numeric inputs:** must be valid, finite numbers; invalid entries and `NaN`/infinity are rejected.
- **Pressure Direction / End Configuration:** a valid selection is required.

These checks also run when the calculation dispatcher is used directly outside the GUI.

**Calculation scope is unchanged:** thin/thick wall selection remains `R/t > 10` per Roark, with the original thin-wall and thick-wall equations and existing von Mises utilisation method. No external-pressure buckling check or new assessment criteria have been added.

------------------------------------------------------------------------

## Development and licences

See [Development](docs/DEVELOPMENT.md) for running from source, tests and reproducible build instructions. The original code and original artwork are MIT licensed; [third-party notices](docs/THIRD_PARTY_NOTICES.md) and [LGPL rebuild instructions](docs/ONEFILE_REBUILD_AND_LGPL.md) cover the independently licensed bundled components.

This calculator is for preliminary stress assessment and cross-checking, not independent certification of full code compliance. External-pressure buckling is not assessed.
