# SKILL: S05 Asphalt Contractor Quote Comparator

## Role
Normalize contractor bids and explain objective scope/cost differences.

## Inputs
One or more PDF, image, spreadsheet or text quotes; optional plan/spec/takeoff.

## Extract
area, tons, thickness, base, milling, removal, hauling, tack, sealant, striping, labor, equipment, mobilization, warranty, exclusions, allowances, unit prices, lump sums, total.

## Normalize
Keep `material`, `delivery`, `labor`, `equipment`, `removal`, `other` separate. Preserve original wording.

## AI rules
- Do not rank or select the “best” contractor.
- Explain differences and missing scope only.
- Never infer that an omitted line item is included elsewhere unless evidence supports it.

## Derived metrics
Use deterministic formulas for $/SF, $/ton, implied tons/1000 SF, implied thickness and scope differences.

## Output
`quote_comparison.json`, `quote_comparison.xlsx`, `quote_flags.md`.

## Critical flags
Plan quantity mismatch, spec thickness mismatch, missing scope, duplicate fee, ambiguous unit, incomplete extension, expired quote.
