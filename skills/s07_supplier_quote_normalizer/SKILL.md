# SKILL: S07 Supplier Quote Normalizer

## Role
Read supplier material quotes and convert them into a normalized, evidence-backed price dataset.

## Extract
Supplier, material, mix, unit, unit price, delivery/freight, minimum load, surcharge, effective date, expiration, region, quote ID.

## Hard separation
Never merge: material-only, delivered material, installed price, public bid price.

## AI rules
- Preserve vendor terminology.
- Map to normalized category only with evidence.
- Flag unclear unit or scope.
- Preserve quote validity period.

## Output
`supplier_prices.json`, `supplier_prices.csv`, `supplier_quote_summary.md`.
