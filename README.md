# Asphalt Desktop Intelligence

**Python toolkit for asphalt paving estimating** — turn plan PDFs, CAD drawings, specifications, contractor quotes, delivery tickets, supplier prices and site photos into **audit-ready estimates** for the [AsphaltCosts.com](https://asphaltcosts.com/) calculation engine.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CLI](https://img.shields.io/badge/CLI-command--line-blue)](#quick-start)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6)](https://www.microsoft.com/windows)
[![AsphaltCosts.com](https://img.shields.io/badge/engine-AsphaltCosts.com-0a7d4c)](#the-web-calculation-engine)

**English** | [简体中文](./README.zh-CN.md)

---

## What it solves

Manual asphalt takeoff is slow and error-prone: dimensions live inside PDF plans and CAD drawings, requirements hide in long specification documents, contractor bids are formatted differently on every sheet, and delivery tickets rarely match the estimate. This project replaces the copy-paste-and-spreadsheet workflow with a **deterministic, evidence-backed desktop pipeline** for asphalt and paving estimators, project managers, foremen and homeowners.

Every script runs a standard lifecycle — `DISCOVER → INGEST → EXTRACT → NORMALIZE → VALIDATE → CALCULATE/CLASSIFY → OUTPUT → AUDIT` — and every important value carries `{value, unit, source_file, source_page, source_region, method, confidence, state, verified}`.

## Features

- **Quantity takeoff from plan PDFs and CAD/DXF drawings** — area, thickness, tons, order tons and truckloads with per-region evidence
- **Specification checking** — structured requirements and SPEC-vs-ADDENDUM / PLAN-vs-SPEC / SPEC-vs-BID conflict detection
- **Contractor quote comparison** — normalized side-by-side bids with $/SF, $/ton and scope flags (no ranking)
- **Delivery ticket reconciliation** — delivered vs estimated tons from CSV / PDF / image tickets with gross−tare validation
- **Supplier price normalization** — evidence-backed material price dataset with basis and validity windows
- **Weather & compaction planning** — HMA cooling/compaction window from a documented lumped thermal model
- **Field photo screening** — potholes, cracking, rutting and surface anomaly detection for QA
- **Audit-ready estimate reports** — JSON / Markdown / XLSX / PDF with source and calculation registers
- **Human-in-the-loop** — low-confidence values and conflicts land in a review queue, never silently fixed

## The scripts

| ID | Script | Primary user | Main input | Main output |
|---|---|---|---|---|
| S01 | `scripts/s01_project_workspace.py` | estimator / PM / foreman | files + project metadata | normalized project workspace (`project.json`, manifest, source index) |
| S02 | `scripts/s02_pdf_plan_takeoff.py` | estimator / PM | civil/paving plan PDFs | paving takeoff table + engine quantities |
| S03 | `scripts/s03_cad_takeoff.py` | estimator / engineer | DWG (→DXF) / DXF | geometry quantities |
| S04 | `scripts/s04_specification_checker.py` | estimator / PM | specification PDFs | structured requirements + conflicts |
| S05 | `scripts/s05_quote_comparator.py` | homeowner / PM / estimator | contractor quotes | comparable quote table + flags |
| S06 | `scripts/s06_delivery_ticket_reconcile.py` | foreman / PM | ticket PDFs/images/CSV | delivered-vs-estimated reconciliation |
| S07 | `scripts/s07_supplier_quote_normalizer.py` | purchaser / estimator | supplier quotes | normalized material price dataset |
| S08 | `scripts/s08_weather_compaction_planner.py` | superintendent / foreman | weather + project parameters | paving window analysis (thermal model) |
| S09 | `scripts/s09_field_photo_analyzer.py` | foreman / homeowner / PM | site photos | visual condition screening |
| S10 | `scripts/s10_estimate_report_builder.py` | estimator / PM | structured project data | audit-ready estimate/report |

## Tech stack

- **Python 3.12+** (Windows 11 first-class, cross-platform CLI)
- **PDF parsing** — PyMuPDF-based text / vector / scale-note extraction
- **CAD** — DXF geometry parsing for takeoff (DWG via conversion)
- **AI boundary** — deterministic heuristic extractor by default; optional OpenAI-compatible backend (`ADI_AI_API_KEY`) for candidate extraction and anomaly explanation only
- **CLI conventions** — every script shares `--project <path> --input <path> --output <path> --format json|csv|md|xlsx|pdf --config <path> --verbose --dry-run`
- **Testing** — golden fixture suite (`pytest`) with tolerance gates (±0.5% plan areas, <0.1% DXF geometry)

## Quick start

```powershell
# Python 3.12+ on Windows 11
pip install -r requirements.txt

# 1) Create a normalized project workspace from any mixture of files
python scripts/s01_project_workspace.py --project .\Project01 --input .\Project01\input

# 2) Take off paving quantities from a plan PDF (vector or dimension-derived)
python scripts/s02_pdf_plan_takeoff.py --project .\Project01 --input .\Project01\input\plans\civil-set.pdf

# 3) Pull material quantities through the AsphaltCosts engine
python scripts/s10_estimate_report_builder.py --project .\Project01 --format md
```

Run any script with `--help` for its options.

## How it works

- **Standard lifecycle** — every script runs `DISCOVER → INGEST → EXTRACT → NORMALIZE → VALIDATE → CALCULATE/CLASSIFY → OUTPUT → AUDIT`.
- **Evidence state machine** — every important value moves `EXTRACTED → NORMALIZED → VALIDATED → VERIFIED`; it is valid to stop at any earlier state.
- **AI boundary** — AI may extract candidates, map synonyms and explain anomalies; it may never invent dimensions, silently change a source value, replace a deterministic calculator result, or mark a value verified without evidence.
- **Human-in-the-loop** — low-confidence values, ambiguous scales, conflicts and missing data land in a compact review queue (`review_queue.json` / summary in each report), never a silent fix.
- **Audit** — every run writes `run_id`, script, timings, input hashes, engine version, warnings, errors and outputs to `<project>/audit/`.

## Configuration

Copy `config.example.json` to `config.json` (or point `--config` at your own file). Endpoints, rate limits and AI provider settings load from configuration; the `asphaltcosts.api_endpoint` field enables direct HTTP calls to the calculation engine when such an endpoint is published — until then the client uses the documented web-engine math as a labeled local mirror (`engine_version: asphaltcosts-web-engine/1.0-mirror`).

## Development

```powershell
pip install -r requirements.txt
python tools/make_pdf_fixtures.py   # golden plan PDFs (needs pymupdf)
python tools/make_photo_fixtures.py # golden photos (needs Pillow)
pytest -q
```

Golden tests cover known plan areas (±0.5%), known DXF geometry (<0.1%), specification extraction, quote comparison, 100-ticket reconciliation, thermal-model direction checks, photo screening and report determinism.

## Repository layout

```text
common/     shared thin foundation (units, schemas, provenance, validation,
            audit, engine client, AI adapter, CLI, DXF parser, output writers)
scripts/    S01–S10
schemas/    JSON contracts (value envelope, takeoff record, project.json)
fixtures/   golden DXF / quotes / specs / tickets / suppliers / weather
tests/      pytest suite
tools/      fixture generators
skills/     AI-agent skill definitions (SKILL.md per script)
docs/       architecture & per-script specifications
```

## Standalone per-tool repositories

Each business scenario is also published as its **own standalone GitHub repository** (own README, tests, fixtures, license and its own visible link back to [AsphaltCosts.com](https://asphaltcosts.com/)), rebuilt from this monorepo with `python tools/build_subrepos.py`:

| Repository | Script |
|---|---|
| [asphalt-pdf-plan-takeoff](https://github.com/anleeylee/asphalt-pdf-plan-takeoff) | S02 |
| [asphalt-specification-checker](https://github.com/anleeylee/asphalt-specification-checker) | S04 |
| [asphalt-quote-comparator](https://github.com/anleeylee/asphalt-quote-comparator) | S05 |
| [asphalt-delivery-ticket-reconciler](https://github.com/anleeylee/asphalt-delivery-ticket-reconciler) | S06 |
| [asphalt-supplier-quote-normalizer](https://github.com/anleeylee/asphalt-supplier-quote-normalizer) | S07 |
| [asphalt-weather-compaction-planner](https://github.com/anleeylee/asphalt-weather-compaction-planner) | S08 |
| [asphalt-field-photo-analyzer](https://github.com/anleeylee/asphalt-field-photo-analyzer) | S09 |
| [asphalt-estimate-report-builder](https://github.com/anleeylee/asphalt-estimate-report-builder) | S10 |

## The web calculation engine

[**AsphaltCosts.com**](https://asphaltcosts.com/) — asphalt tonnage, cost, coverage, truckload and paving calculators: area → compacted volume → net tons → order tons (allowance applied once) → truckloads → material cost, with sourced planning defaults (145 lb/ft³ FHWA density, editable allowance and truck capacity).

The web site stays the deterministic calculation layer: **tons, volume, coverage, truckloads and material cost come from the AsphaltCosts engine, never from re-implemented desktop math.** These scripts solve the tasks that need local files, batch processing, OCR, CAD parsing, project evidence, AI document understanding or local automation — and they feed normalized, validated values *into* the engine.

> ⚠️ **Planning tool, not engineering design.** All outputs are planning estimates. Results must never be presented as "approved to pave" or as an engineering verdict.

## Security & privacy

- Local files stay local by default; AI upload requires explicit per-run configuration.
- API keys live in environment variables (`ASPHALTCOSTS_API_KEY`, `ADI_AI_API_KEY`) or Windows Credential Manager — never in source code.
- File hashes are recorded so every report identifies the exact source version used.
- Never overwrite or delete a source file automatically; derived files live in `working/` or `output/`.

## License

MIT — see [LICENSE](LICENSE).
