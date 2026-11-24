# Engineering scope and limitations

The stress engine is the final legacy v1.3 engine, byte-for-byte unchanged. It uses the adopted Roark sixth-edition Tables 28 and 32 formulations and API 6X second-edition-based allowables described in the README. Thin wall applies for mean-radius/thickness ratio greater than 10. Thick-wall longitudinal, hoop and radial stresses are evaluated consistently at the bore; maximum shear uses all three principal stresses. Thin-wall radial stress is neglected and separate shear utilisation is not calculated. Derating applies only to working pressure.

## Geometry and tolerances

Enter any two of OD, ID and thickness. The remaining dimension is derived. For independent OD and ID, the original minimum OD / maximum ID basis is intentionally retained, even when another physical geometry might govern some particular criterion.

For independent diameter and thickness, the program respects their joint tolerance rectangle, reconstructs the other diameter, and selects the geometry with the greatest utilisation across both pressure conditions and applicable criteria. All displayed stresses and utilisation values are evaluated at that same geometry; individual results are not independently maximised. The governing dimensions are shown in Inspect Results, the main analysis tooltip and, for alternative toleranced input, on the report.

For ratio x=R/t, at fixed x stresses are affine in 1/t² (axial load contribution); von Mises and maximum shear are convex in this quantity. The maximum therefore lies on the physical tolerance rectangle boundary. Along each constant-diameter or constant-thickness boundary the principal-stress differences have form a*x+b+c/x. The square of von Mises is proportional to the sum of squared differences; stationary points satisfy a quartic. Shear is the maximum absolute pair difference divided by two. The selector evaluates boundary ends and stationary points and separates thin/thick methods at x=10, checking both sides numerically. The selection is performed in finite precision and is verified by deterministic sampled comparisons, not a formal proof of every floating-point case.

Geometry ranges must be physically valid, and pressure/material inputs are validated. No buckling, fatigue, local stress concentrations, thermal gradients or full code compliance assessment is provided. Use qualified engineering review for design decisions.
