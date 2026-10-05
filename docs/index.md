---
layout: default
title: Asphalt Desktop Intelligence
---

# Asphalt Desktop Intelligence

**Desktop companion tools for the [AsphaltCosts.com](https://asphaltcosts.com/) web calculation engine** — Python tooling for asphalt and paving estimating: PDF/CAD quantity takeoff, specification checking, quote comparison, delivery-ticket reconciliation, supplier price normalization, weather compaction planning, field photo analysis and audit-ready estimate reports.

The web site stays the deterministic calculation layer: tons, volume, coverage, truckloads and material cost come from the AsphaltCosts engine, never from re-implemented desktop math.

> ⚠️ **Planning tool, not engineering design.** All outputs are planning estimates. Results must never be presented as "approved to pave" or as an engineering verdict.

## Quick start

```powershell
pip install -r requirements.txt
python scripts/s01_project_workspace.py --project .\Project01 --input .\Project01\input
python scripts/s02_pdf_plan_takeoff.py --project .\Project01 --input .\Project01\input\plans\civil-set.pdf
python scripts/s10_estimate_report_builder.py --project .\Project01 --format md
```

## Architecture & specification documents

| Document | Description |
|---|---|
| [00 — Desktop Architecture](00-DESKTOP-ARCHITECTURE.html) | overall architecture and shared standards |
| [01 — S01 Project Workspace](01-S01-project-workspace.html) | project workspace manager |
| [02 — S02 PDF Plan Takeoff](02-S02-pdf-plan-takeoff.html) | PDF plan takeoff |
| [03 — S03 CAD Takeoff](03-S03-cad-takeoff.html) | CAD/DXF/DWG takeoff |
| [04 — S04 Specification Checker](04-S04-specification-checker.html) | specification reader + conflict checker |
| [05 — S05 Quote Comparator](05-S05-quote-comparator.html) | contractor quote comparator |
| [06 — S06 Delivery Ticket Reconcile](06-S06-delivery-ticket-reconcile.html) | delivery ticket reconciliation |
| [07 — S07 Supplier Quote Normalizer](07-S07-supplier-quote-normalizer.html) | supplier pricing normalizer |
| [08 — S08 Weather Compaction Planner](08-S08-weather-compaction-planner.html) | weather/thermal compaction planner |
| [09 — S09 Field Photo Analyzer](09-S09-field-photo-analyzer.html) | field photo screening |
| [10 — S10 Estimate Report Builder](10-S10-estimate-report-builder.html) | estimate/audit report |
| [11 — Implementation Playbook](11-IMPLEMENTATION-PLAYBOOK.html) | development conventions |

## The scripts

| ID | Script | Primary user | Main input | Main output |
|---|---|---|---|---|
| S01 | `s01_project_workspace.py` | estimator / PM / foreman | files + project metadata | normalized project workspace |
| S02 | `s02_pdf_plan_takeoff.py` | estimator / PM | civil/paving PDFs | paving takeoff table + engine quantities |
| S03 | `s03_cad_takeoff.py` | estimator / engineer | DWG (→DXF) / DXF | geometry quantities |
| S04 | `s04_specification_checker.py` | estimator / PM | specification PDFs | structured requirements + conflicts |
| S05 | `s05_quote_comparator.py` | homeowner / PM / estimator | contractor quotes | comparable quote table + flags |
| S06 | `s06_delivery_ticket_reconcile.py` | foreman / PM | ticket PDFs/images/CSV | delivered-vs-estimated reconciliation |
| S07 | `s07_supplier_quote_normalizer.py` | purchaser / estimator | supplier quotes | normalized material price dataset |
| S08 | `s08_weather_compaction_planner.py` | superintendent / foreman | weather + project parameters | paving window analysis (thermal model) |
| S09 | `s09_field_photo_analyzer.py` | foreman / homeowner / PM | site photos | visual condition screening |
| S10 | `s10_estimate_report_builder.py` | estimator / PM | structured project data | audit-ready estimate/report |

## Standalone per-tool repositories

Each business scenario is also published as its own standalone GitHub repository:

- [asphalt-pdf-plan-takeoff](https://github.com/anleeylee/asphalt-pdf-plan-takeoff)
- [asphalt-specification-checker](https://github.com/anleeylee/asphalt-specification-checker)
- [asphalt-quote-comparator](https://github.com/anleeylee/asphalt-quote-comparator)
- [asphalt-delivery-ticket-reconciler](https://github.com/anleeylee/asphalt-delivery-ticket-reconciler)
- [asphalt-supplier-quote-normalizer](https://github.com/anleeylee/asphalt-supplier-quote-normalizer)
- [asphalt-weather-compaction-planner](https://github.com/anleeylee/asphalt-weather-compaction-planner)
- [asphalt-field-photo-analyzer](https://github.com/anleeylee/asphalt-field-photo-analyzer)
- [asphalt-estimate-report-builder](https://github.com/anleeylee/asphalt-estimate-report-builder)

## The web calculation engine

[**AsphaltCosts.com**](https://asphaltcosts.com/) — asphalt tonnage, cost, coverage, truckload and paving calculators: area → compacted volume → net tons → order tons (allowance applied once) → truckloads → material cost, with sourced planning defaults (145 lb/ft³ FHWA density, editable allowance and truck capacity).

## License

MIT — see [LICENSE](LICENSE).
