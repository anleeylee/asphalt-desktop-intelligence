# Implementation Playbook — Build Order & Shared Development Standard

## 1. Recommended build sequence

### Wave 1 — foundation

```text
S01 Project Workspace
S05 Quote Comparator
S06 Delivery Ticket Reconciler
```

Reason: these have clear inputs/outputs and immediately create useful structured project data.

### Wave 2 — document takeoff

```text
S02 PDF Plan Takeoff
S04 Specification Checker
S07 Supplier Quote Normalizer
```

### Wave 3 — professional field tools

```text
S03 CAD Takeoff
S08 Weather & Compaction Planner
S09 Field Photo Analyzer
```

### Wave 4 — reporting

```text
S10 Estimate & Audit Report Builder
```

## 2. Recommended repository

```text
asphalt-desktop/
├── scripts/
│   ├── s01_project_workspace.py
│   ├── s02_pdf_plan_takeoff.py
│   ├── s03_cad_takeoff.py
│   ├── s04_specification_checker.py
│   ├── s05_quote_comparator.py
│   ├── s06_delivery_ticket_reconcile.py
│   ├── s07_supplier_quote_normalizer.py
│   ├── s08_weather_compaction_planner.py
│   ├── s09_field_photo_analyzer.py
│   └── s10_estimate_report_builder.py
├── skills/
│   ├── s02_pdf_plan_takeoff/SKILL.md
│   ├── s04_specification_checker/SKILL.md
│   ├── s05_quote_comparator/SKILL.md
│   ├── s06_delivery_ticket_reconcile/SKILL.md
│   ├── s07_supplier_quote_normalizer/SKILL.md
│   ├── s08_weather_compaction_planner/SKILL.md
│   └── s09_field_photo_analyzer/SKILL.md
├── common/
├── schemas/
├── fixtures/
└── reports/
```

## 3. Skill format

Each `SKILL.md` must contain:

```text
Purpose
When to use
Inputs
Outputs
Workflow
Tools
AI instructions
Validation rules
Error handling
Human review triggers
Examples
Acceptance tests
```

## 4. Tool choice

Prefer deterministic local parsing before AI:

```text
vector/text extraction
→ geometry/parser/OCR
→ AI semantic interpretation
→ deterministic validation
```

AI should not be the first choice for arithmetic or geometry when a deterministic parser can solve it.

## 5. Computer vision rule

For images/PDF scans:

```text
image enhancement
→ OCR / layout extraction
→ object/region detection
→ AI interpretation
→ human review if confidence low
```

Never repeat expensive OCR unnecessarily; cache page/image hashes and extracted artifacts.

## 6. API integration

Create one configurable `AsphaltCostsClient`:

```python
client.calculate_quantity(...)
client.calculate_cost(...)
```

Actual endpoints, authentication and rate limits must be loaded from configuration rather than hardcoded into each script.

## 7. Logging

Every run writes:

```text
run_id
script_id
start_time
end_time
input_hashes
model/provider
engine_version
warnings
errors
outputs
```

## 8. Error classes

```text
E001 UnsupportedFile
E002 MissingScale
E003 AmbiguousUnit
E004 LowConfidenceExtraction
E005 ConflictingSpecification
E006 DuplicateRecord
E007 InvalidGeometry
E008 APIError
E009 MissingSource
E010 CalculationValidationFailure
```

## 9. Golden tests

Maintain fixtures for:

- known plan area;
- known CAD geometry;
- known specification requirements;
- known quote comparison;
- known delivery tickets;
- known thermal scenario;
- known photo classification.

CI should fail when numeric outputs drift unexpectedly.

## 10. Human-in-the-loop rule

The user should see a compact review queue:

```text
3 values need verification
2 plan/spec conflicts
1 ambiguous supplier unit
```

Do not force the user to read the entire AI reasoning trace.
