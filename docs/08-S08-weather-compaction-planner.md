# S08 — Asphalt Weather & Thermal Compaction Planner

## 1. Purpose

Provide a model-based planning estimate of HMA cooling/compaction window for a selected paving operation.

## 2. Primary users

Superintendent, paving foreman, estimator planning a workday.

## 3. Inputs

- project location
- paving date/time
- air temperature
- wind speed
- surface/base temperature
- lift thickness
- mix type
- delivery temperature
- start-rolling temperature
- stop-rolling temperature
- optional sky/solar inputs

Weather can be manually entered or supplied by an approved weather source.

## 4. Model requirement

Use a documented PaveCool-derived or other validated thermal model. Model version must be stored with every result.

```text
weather + surface + mix + lift + thermal inputs
→ cooling curve
→ time to start/stop thresholds
→ estimated window
```

## 5. Output

```text
estimated_window_minutes
start_rolling_time
stop_rolling_time
temperature_curve
model_version
assumptions
limitations
risk_factors
```

## 6. Engineering boundary

- do not hard-code one universal stop temperature for every mix;
- allow supplier/agency/user-specific thresholds;
- label all results as planning estimates;
- never issue “approved to pave” language.

## 7. AI responsibilities

AI explains why a window is shorter or longer using only model inputs and documented sources.

## 8. Acceptance tests

- benchmark against selected published PaveCool cases;
- changing wind speed must affect the result in expected direction;
- thinner lift generally cools faster under otherwise identical conditions;
- model/version and input snapshot are always recorded.
