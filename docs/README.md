# Asphalt Desktop Intelligence — Development Package

This package turns the AsphaltCosts web calculator into a modular desktop workflow. It deliberately avoids a single giant AI agent.

## Files

- `00-DESKTOP-ARCHITECTURE.md` — overall architecture and shared standards
- `01-S01-project-workspace.md` — project workspace manager
- `02-S02-pdf-plan-takeoff.md` — PDF plan takeoff
- `03-S03-cad-takeoff.md` — CAD/DXF/DWG takeoff
- `04-S04-specification-checker.md` — specification reader + conflict checker
- `05-S05-quote-comparator.md` — contractor quote comparator
- `06-S06-delivery-ticket-reconcile.md` — delivery ticket reconciliation
- `07-S07-supplier-quote-normalizer.md` — supplier pricing normalizer
- `08-S08-weather-compaction-planner.md` — weather/thermal compaction planner
- `09-S09-field-photo-analyzer.md` — field photo screening
- `10-S10-estimate-report-builder.md` — estimate/audit report
- `11-IMPLEMENTATION-PLAYBOOK.md` — development conventions

## Core principle

```text
One script = one primary user + one primary scenario + one clear input family + one output contract.
```

The website remains the deterministic calculation engine; desktop scripts acquire, structure, validate and explain project information.
