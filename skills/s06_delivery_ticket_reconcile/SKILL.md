# SKILL: S06 Asphalt Delivery Ticket Reconciler

## Role
Extract asphalt delivery ticket data and reconcile delivered material with estimate/PO/project records.

## Inputs
Ticket JPG/PNG/PDF/CSV; optional estimate and PO.

## Extract
plant, supplier, truck_id, load_id, date, time, mix, gross, tare, net_tons.

## Validation
- gross - tare consistency;
- duplicate ticket IDs;
- impossible timestamps;
- missing net weight;
- mix mismatch;
- duplicate image/document detection.

## AI rules
Every extracted value must keep source file/page/image and confidence.

## Variance analysis
Compare delivered vs estimated quantity using deterministic math. AI may describe possible causes but must label causes `OBSERVED`, `POSSIBLE`, or `UNVERIFIED`.

## Output
`delivery_reconciliation.json`, `delivery_reconciliation.csv`, `exceptions.md`.
