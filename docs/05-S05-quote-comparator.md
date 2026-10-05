# S05 — Asphalt Contractor Quote Comparator

## 1. Purpose

Turn one or more contractor quotes into a standardized scope/quantity/cost comparison.

## 2. Users

- homeowner comparing bids;
- property manager;
- estimator/PM benchmarking subcontractor quotes.

## 3. Inputs

- PDF/scan quote
- email-exported quote
- spreadsheet quote
- optional project takeoff/specification

## 4. Extract fields

### Scope

- paving area
- asphalt tons
- asphalt thickness
- base thickness
- milling
- removal
- hauling
- tack coat
- sealant
- striping
- drainage
- mobilization
- warranty

### Cost

- material
- delivery
- labor
- equipment
- lump sum
- unit prices
- allowances
- exclusions
- taxes/fees
- total

## 5. Output

```text
quote_comparison.xlsx
quote_comparison.json
quote_flags.md
```

## 6. AI responsibilities

AI extracts, normalizes and explains scope differences.

AI must not produce a “best contractor” ranking. It should instead report objective differences and unresolved omissions.

## 7. Automatic derived metrics

When project quantity is known:

```text
quoted $/sq ft
quoted $/ton
implied tonnage per 1,000 sq ft
implied thickness
scope inclusion rate
```

These derived metrics should use deterministic formulas.

## 8. Flags

Examples:

- quoted area differs from plan by > configured threshold;
- quote omits known major scope item;
- thickness differs from specification;
- bid uses a lump sum where quantity is expected;
- unit price is present but extension is missing;
- duplicate fee;
- warranty terms missing.

## 9. Acceptance

Three fixture quotes with deliberately different scopes must result in a normalized table where differences are preserved rather than flattened.
