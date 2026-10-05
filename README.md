# Asphalt Desktop Intelligence

**Desktop companion tools for the [AsphaltCosts.com](https://asphaltcosts.com/) web calculation engine** — project workspace, PDF/CAD takeoff, specification checking, quote comparison, delivery-ticket reconciliation, supplier price normalization, weather/thermal compaction planning, field photo screening and audit-ready estimate reporting.

The web site stays the deterministic calculation layer: **tons, volume, coverage, truckloads and material cost come from the AsphaltCosts engine**, never from re-implemented desktop math. These scripts solve the tasks that need local files, batch processing, OCR, CAD parsing, project evidence, AI document understanding or local automation — and they feed normalized, validated values *into* the engine.

> ⚠️ **Planning tool, not engineering design.** All outputs are planning estimates. Results must never be presented as "approved to pave" or as an engineering verdict.

---

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

Run any script with `--help` for its options. Every script shares the same CLI convention:

```text
--project <path>   --input <path>   --output <path>
--format json|csv|md|xlsx|pdf       --config <path>   --verbose   --dry-run
```

---

## The scripts

| ID | Script | Primary user | Main input | Main output |
|---|---|---|---|---|
| S01 | `s01_project_workspace.py` | estimator / PM / foreman | files + project metadata | normalized project workspace (`project.json`, manifest, source index) |
| S02 | `s02_pdf_plan_takeoff.py` | estimator / PM | civil/paving PDFs | paving takeoff table + engine quantities |
| S03 | `s03_cad_takeoff.py` | estimator / engineer | DWG (→DXF) / DXF | geometry quantities |
| S04 | `s04_specification_checker.py` | estimator / PM | specification PDFs | structured requirements + conflicts |
| S05 | `s05_quote_comparator.py` | homeowner / PM / estimator | contractor quotes | comparable quote table + flags |
| S06 | `s06_delivery_ticket_reconcile.py` | foreman / PM | ticket PDFs/images/CSV | delivered-vs-estimated reconciliation |
| S07 | `s07_supplier_quote_normalizer.py` | purchaser / estimator | supplier quotes | normalized material price dataset |
| S08 | `s08_weather_compaction_planner.py` | superintendent / foreman | weather + project parameters | paving window analysis (thermal model) |
| S09 | `s09_field_photo_analyzer.py` | foreman / homeowner / PM | site photos | visual condition screening |
| S10 | `s10_estimate_report_builder.py` | estimator / PM | structured project data | audit-ready estimate/report |

## How it works

- **Standard lifecycle** — every script runs `DISCOVER → INGEST → EXTRACT → NORMALIZE → VALIDATE → CALCULATE/CLASSIFY → OUTPUT → AUDIT`.
- **Evidence state machine** — every important value carries `{value, unit, source_file, source_page, source_region, method, confidence, state, verified}` and moves `EXTRACTED → NORMALIZED → VALIDATED → VERIFIED`. It is valid to stop at any earlier state.
- **AI boundary** — AI may extract candidates, map synonyms and explain anomalies; it may never invent dimensions, silently change a source value, replace a deterministic calculator result, or mark a value verified without evidence. The shipped default is a deterministic heuristic extractor; an OpenAI-compatible backend is optional (env `ADI_AI_API_KEY`).
- **Human-in-the-loop** — low-confidence values, ambiguous scales, conflicts and missing data land in a compact review queue (`review_queue.json` / summary in each report), never a silent fix.
- **Audit** — every run writes `run_id`, script, timings, input hashes, engine version, warnings, errors and outputs to `<project>/audit/`.

## Security & privacy

- Local files stay local by default; AI upload requires explicit per-run configuration.
- API keys live in environment variables (`ASPHALTCOSTS_API_KEY`, `ADI_AI_API_KEY`) or Windows Credential Manager — never in source code.
- File hashes are recorded so every report identifies the exact source version used.
- Never overwrite or delete a source file automatically; derived files live in `working/` or `output/`.

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

## License

MIT — see [LICENSE](LICENSE).

## The web calculation engine

[**AsphaltCosts.com**](https://asphaltcosts.com/) — asphalt tonnage, cost, coverage, truckload and paving calculators: area → compacted volume → net tons → order tons (allowance applied once) → truckloads → material cost, with sourced planning defaults (145 lb/ft³ FHWA density, editable allowance and truck capacity).
