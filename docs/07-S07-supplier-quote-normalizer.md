---
layout: default
title: "S07 — Supplier Quote & Material Price Normalizer"
---

# S07 — Supplier Quote & Material Price Normalizer

## 1. Purpose

Convert supplier quotes into a structured price evidence dataset usable by cost calculations and project estimating.

## 2. Primary users

Purchasing, estimator, contractor PM.

## 3. Inputs

- supplier PDF/email/spreadsheet
- quote date
- supplier location
- project location
- optional freight/delivery terms

## 4. Normalize

```text
supplier
material
mix
unit
unit_price
delivery_price
minimum_load
effective_date
expiration_date
region
quote_id
source_file
```

## 5. Critical distinction

The script must keep separate:

```text
material-only price
material + delivery
installed price
public bid price
```

It must never merge them into one generic “asphalt price”.

## 6. AI responsibilities

- extract quote line items;
- map vendor wording to normalized material categories;
- detect taxes, fuel surcharges and minimum loads;
- flag ambiguous units.

## 7. Output

```text
supplier_prices.json
supplier_prices.csv
supplier_quote_summary.md
```

## 8. Acceptance tests

- quote with multiple HMA mixes keeps each mix separate;
- delivery is not merged into material price;
- quote expiration is preserved;
- ambiguous unit goes to review.
