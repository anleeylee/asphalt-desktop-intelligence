# S06 — Asphalt Delivery Ticket Reconciliation Skill

## 1. Purpose

Extract and reconcile asphalt delivery tickets against estimated quantity, purchase orders and paving records.

## 2. Primary users

Foreman, superintendent, project manager, estimator.

## 3. Inputs

- ticket JPG/PNG/PDF
- ticket CSV
- estimate quantity
- purchase order (optional)
- mix specification (optional)
- date range

## 4. Fields

```text
plant
supplier
truck_id
load_id
date
time
mix
net_tons
gross
tare
```

## 5. Workflow

```text
files
↓
OCR / text extraction
↓
field extraction
↓
duplicate detection
↓
unit normalization
↓
chronological sorting
↓
quantity reconciliation
↓
variance analysis
```

## 6. Validation

- gross - tare ≈ net within document rounding tolerance;
- duplicate ticket IDs flagged;
- impossible timestamps flagged;
- missing net weight flagged;
- mix mismatch against specification flagged.

## 7. Output

```text
delivered_total_tons
estimated_tons
variance_tons
variance_percent
truck_count
load_count
exception_list
```

## 8. AI explanation

AI may explain plausible causes for variance, but every cause is labeled as:

```text
OBSERVED
POSSIBLE
UNVERIFIED
```

Never state a root cause as fact without evidence.

## 9. Acceptance tests

- 100 tickets → correct total within source precision;
- duplicates caught;
- 2 intentionally damaged tickets moved to review;
- variance calculation matches reference.
