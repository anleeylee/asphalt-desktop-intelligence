# SKILL: S08 Asphalt Weather & Thermal Compaction Planner

## Role
Provide a model-based estimate of an HMA cooling/compaction window for planning.

## Inputs
air temp, wind, surface/base temp, lift thickness, mix type, delivery temp, start-roll temp, stop-roll temp, location/date/time and optional solar/cloud inputs.

## Model
Use a documented, versioned thermal model. Prefer a legally reusable PaveCool-derived implementation or other validated method.

## AI rules
AI explains model outputs; it does not replace the thermal model.

## Hard boundary
Never say “approved to pave” or treat one temperature threshold as universal. Supplier/agency/project-specific limits override planning defaults.

## Output
`thermal_run.json`, cooling curve, estimated window, assumptions, limitations, risk factors.
