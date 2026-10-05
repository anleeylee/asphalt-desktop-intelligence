---
layout: default
title: "S10 — Asphalt Estimate & Audit Report Builder"
---

# S10 — Asphalt Estimate & Audit Report Builder

## 1. Purpose

Turn already structured takeoff, specification, quote, supplier and ticket data into one reproducible project estimate/report.

This is a report builder, not a mega-agent. It does not discover documents on its own and does not silently invent missing values.

## 2. Primary user

Estimator / PM.

## 3. Inputs

- validated `project.json`
- takeoff records
- spec requirements
- supplier prices
- quote comparison
- ticket reconciliation
- optional weather analysis

## 4. Output formats

- Markdown
- JSON
- CSV
- XLSX
- PDF

## 5. Report structure

```text
Project Summary
Takeoff
Pavement Sections
Material Quantities
Order Quantities
Truckloads
Cost Basis
Supplier Evidence
Quote Comparison
Delivery Reconciliation
Weather/Compaction Notes
Risk & Review Flags
Source Register
Calculation Register
```

## 6. Calculation policy

All asphalt quantities should use the AsphaltCosts engine where supported. Every calculated field records the engine/version or calculation run ID.

## 7. Evidence table

| Field | Value | Source | State | Confidence |
|---|---:|---|---|---|
| Paving Area | 84,200 SF | C3.1.pdf p12 | VERIFIED | 1.00 |
| Density | 145 lb/ft³ | planning default | VALIDATED | 0.80 |
| Thickness | 3 in | spec p34 | EXTRACTED | 0.94 |

## 8. Red flags

Use explicit statuses:

```text
INFO
REVIEW
WARNING
MISMATCH
MISSING DATA
```

No overall “good/bad contractor” score.

## 9. Acceptance tests

- every number in the report traces to a source or a named calculation run;
- report regenerated from same project data produces the same deterministic numeric values;
- missing fields are displayed as missing, not filled by AI guess.
