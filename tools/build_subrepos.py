"""Build 8 standalone, self-contained GitHub repos — one per business script.

Each repo carries its own script, the shared common/ foundation it needs,
its fixtures, tests, SKILL definition and spec doc, plus a README that links
back to the AsphaltCosts.com calculation engine. Every repo is independently
cloneable and testable.

Repos built here:
  asphalt-pdf-plan-takeoff            (S02)
  asphalt-specification-checker       (S04)
  asphalt-quote-comparator            (S05)
  asphalt-delivery-ticket-reconciler  (S06)
  asphalt-supplier-quote-normalizer   (S07)
  asphalt-weather-compaction-planner  (S08)
  asphalt-field-photo-analyzer        (S09)
  asphalt-estimate-report-builder     (S10)

Run from the repo root:
    python tools/build_subrepos.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent.parent.parent / "asphalt-tools"

WEBSITE = "https://asphaltcosts.com/"

ENGINE_NOTE = (
    "## The calculation engine\n\n"
    f"[**AsphaltCosts.com**]({WEBSITE}) is the deterministic calculation layer: "
    "area → compacted volume → net tons → order tons (allowance applied once) → "
    "truckloads → material cost, with sourced planning defaults "
    "(145 lb/ft\u00b3 FHWA density, editable allowance and truck capacity). "
    "This tool feeds measured and validated inputs into that engine (or its "
    "labeled local mirror, `asphaltcosts-web-engine/1.0-mirror`) and never "
    "re-implements the formulas.\n"
)

README_TEMPLATE = """# {title}

{one_line}

> &#9888; **All tonnage, coverage and cost math is powered by [AsphaltCosts.com]({website})**
> — the web asphalt tonnage & cost calculator. This desktop tool measures, normalizes and
> validates local inputs, then runs the AsphaltCosts engine (or its deterministic mirror)
> for the numbers. It never re-implements the formulas.

## What it does

{intro}

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
{usage}
```

Run with `--help` for all options. Every script in this family shares the same CLI
convention: `--project <path> --input <path> --output <path> --format json|csv|md|xlsx|pdf
--config <path> --verbose --dry-run`.

## Outputs

{outputs}

## Quality gates

- deterministic schema validation on every record;
- golden sample fixtures with exact expected values (`tests/`);
- review queue: low-confidence values, ambiguous scales and conflicts land in
  `review_queue.json` / summary — never a silent fix;
- audit log: every run writes `run_id`, timings, input hashes, engine version
  and outputs to `<project>/audit/`.

## Testing

```bash
python -m pytest -q
```

## Security & privacy

Local files stay local by default. API keys live in environment variables
(`ASPHALTCOSTS_API_KEY`, `ADI_AI_API_KEY`) — never in source code. Derived files are
written to `working/` or `output/`; source files are never modified.

## License

MIT — see [LICENSE](LICENSE). Part of the Asphalt Desktop Intelligence toolkit.

{engine_note}
"""

REPOS = [
    dict(
        name="asphalt-pdf-plan-takeoff",
        module="s02_pdf_plan_takeoff",
        script_id="s02",
        skill_dir="s02_pdf_plan_takeoff",
        doc_file="02-S02-pdf-plan-takeoff.md",
        title="Asphalt PDF Plan Takeoff",
        one_line="Extract and validate paving quantities from plan PDFs, then run them through the AsphaltCosts engine.",
        intro=(
            "Reads civil/paving plan PDFs, classifies sheets, parses text, scale notes and vector "
            "drawings, and produces measurable paving regions with confidence and evidence. "
            "Ambiguous scales, conflicting dimensions and uncertain labels go to the review queue "
            "instead of being guessed. Validated quantities are sent to the AsphaltCosts engine "
            "for tons, order tons and truckloads."
        ),
        usage="python -m scripts.s02_pdf_plan_takeoff --project ./project --input ./fixtures/pdf",
        outputs=(
            "- `takeoff.json` / `takeoff.csv` — validated area records (area_id, sheet, source, quantity, unit, thickness, method, confidence, state)\n"
            "- `review_queue.json` — ambiguous scale / low-confidence / conflicting-dimension items\n"
            "- `summary.md` — plan summary and engine calculation record"
        ),
        fixtures=["pdf", "specs/spec_base.txt"],
        tools=["make_pdf_fixtures.py"],
        test_file="test_s02.py",
    ),
    dict(
        name="asphalt-specification-checker",
        module="s04_specification_checker",
        script_id="s04",
        skill_dir="s04_specification_checker",
        doc_file="04-S04-specification-checker.md",
        title="Asphalt Specification Checker",
        one_line="Turn construction specifications and addenda into structured, evidence-backed requirements and conflicts.",
        intro=(
            "Extracts thickness, density, PG binder, mix, tack, temperature, testing and acceptance "
            "requirements from specification PDFs/text, classifies every statement as REQUIRED / "
            "RECOMMENDED / OPTIONAL / EXAMPLE / REFERENCE ONLY, and detects SPEC-vs-ADDENDUM, "
            "PLAN-vs-SPEC, SPEC-vs-BID and PLAN-vs-BID conflicts. Addenda are tracked as versions, "
            "never silently overwriting the original."
        ),
        usage="python -m scripts.s04_specification_checker --project ./project --input ./fixtures/specs",
        outputs=(
            "- `spec_requirements.json` — structured requirements with source page and classification\n"
            "- `conflicts.json` — detected conflict modes with both sides preserved\n"
            "- `spec_summary.md` and `review_queue.json`"
        ),
        fixtures=["specs"],
        tools=[],
        test_file="test_s04.py",
    ),
    dict(
        name="asphalt-quote-comparator",
        module="s05_quote_comparator",
        script_id="s05",
        skill_dir="s05_quote_comparator",
        doc_file="05-S05-quote-comparator.md",
        title="Asphalt Quote Comparator",
        one_line="Normalize contractor bids and explain objective scope and cost differences — without ranking.",
        intro=(
            "Parses one or more quote texts/PDFs/spreadsheets into a comparable dataset: area, tons, "
            "thickness, scope line items, unit prices, lump sums and grand total, with material / "
            "delivery / labor / equipment / removal kept separate and original wording preserved. "
            "Deterministic derived metrics ($/SF, $/ton, implied thickness) are computed from stated "
            "quantities only. Flags call out plan-quantity mismatch, spec-thickness mismatch, missing "
            "scope, missing tonnage and missing totals. It never picks a 'best' contractor."
        ),
        usage="python -m scripts.s05_quote_comparator --project ./project --input ./fixtures/quotes",
        outputs=(
            "- `quote_comparison.json` — normalized quotes + derived metrics + flags\n"
            "- `quote_comparison.xlsx` — side-by-side comparison sheet\n"
            "- `quote_flags.md` — critical flags in human-readable form"
        ),
        fixtures=["quotes"],
        tools=[],
        test_file="test_s05.py",
    ),
    dict(
        name="asphalt-delivery-ticket-reconciler",
        module="s06_delivery_ticket_reconcile",
        script_id="s06",
        skill_dir="s06_delivery_ticket_reconcile",
        doc_file="06-S06-delivery-ticket-reconcile.md",
        title="Asphalt Delivery Ticket Reconciler",
        one_line="Extract delivery-ticket data and reconcile delivered asphalt against the estimate.",
        intro=(
            "Reads tickets from CSV, PDF or images: plant, truck, load id, date, time, mix, gross, "
            "tare and net tons. Validates gross−tare consistency, duplicate ticket ids, impossible "
            "timestamps, missing net weights and mix mismatches. Compares delivered vs estimated "
            "tons with deterministic math; any explanation of variance is labeled OBSERVED, POSSIBLE "
            "or UNVERIFIED."
        ),
        usage="python -m scripts.s06_delivery_ticket_reconcile --project ./project --input ./fixtures/tickets/tickets_10.csv --estimate 199.4",
        outputs=(
            "- `delivery_reconciliation.json` — delivered/estimated totals, variance, truck and load counts\n"
            "- `delivery_reconciliation.csv` — per-ticket normalized rows\n"
            "- `exceptions.md` — flagged tickets and variance causes"
        ),
        fixtures=["tickets"],
        tools=[],
        test_file="test_s06.py",
    ),
    dict(
        name="asphalt-supplier-quote-normalizer",
        module="s07_supplier_quote_normalizer",
        script_id="s07",
        skill_dir="s07_supplier_quote_normalizer",
        doc_file="07-S07-supplier-quote-normalizer.md",
        title="Asphalt Supplier Quote Normalizer",
        one_line="Convert supplier material quotes into a normalized, evidence-backed price dataset.",
        intro=(
            "Reads supplier quotes and extracts supplier, material, mix, unit, unit price, minimum "
            "load, surcharges, effective/expiration dates and region. It hard-separates material-only, "
            "delivered, installed and public-bid prices — never merging them — and maps to a "
            "normalized category only with evidence. Unclear units or scopes are flagged."
        ),
        usage="python -m scripts.s07_supplier_quote_normalizer --project ./project --input ./fixtures/suppliers --region \"City Rock\"",
        outputs=(
            "- `supplier_prices.json` — normalized price items with basis and validity window\n"
            "- `supplier_prices.csv`\n"
            "- `supplier_quote_summary.md`"
        ),
        fixtures=["suppliers"],
        tools=[],
        test_file="test_s07.py",
    ),
    dict(
        name="asphalt-weather-compaction-planner",
        module="s08_weather_compaction_planner",
        script_id="s08",
        skill_dir="s08_weather_compaction_planner",
        doc_file="08-S08-weather-compaction-planner.md",
        title="Asphalt Weather & Compaction Planner",
        one_line="Model-based estimate of the HMA cooling/compaction window for paving planning.",
        intro=(
            "Runs a documented, versioned lumped thermal model (ADI-THM-v1.0) over air temp, wind, "
            "surface/base temp, lift thickness and delivery temperature to estimate the start-roll / "
            "stop-roll window and cooling curve. The AI explains model outputs but never replaces the "
            "thermal model, and the tool never says 'approved to pave' — supplier/agency limits "
            "override planning defaults."
        ),
        usage="python -m scripts.s08_weather_compaction_planner --project ./project --air-temp 60 --wind 5 --lift-in 3",
        outputs=(
            "- `thermal_run.json` — inputs snapshot, model version, window, assumptions, limitations, risk factors\n"
            "- `thermal_summary.md` — planning summary"
        ),
        fixtures=["weather"],
        tools=[],
        test_file="test_s08.py",
    ),
    dict(
        name="asphalt-field-photo-analyzer",
        module="s09_field_photo_analyzer",
        script_id="s09",
        skill_dir="s09_field_photo_analyzer",
        doc_file="09-S09-field-photo-analyzer.md",
        title="Asphalt Field Photo Analyzer",
        one_line="Screen site photos for visible pavement distress and field observations.",
        intro=(
            "Analyzes JPG/PNG photos for potholes, cracking, rutting, edge deterioration, patching, "
            "standing water and surface anomalies. Photo analysis is visual screening only — it never "
            "infers CBR, structural capacity, remaining life or exact repair depth. Poor-quality "
            "images go to review, and any measured dimension is marked APPROXIMATE until verified."
        ),
        usage="python -m scripts.s09_field_photo_analyzer --project ./project --input ./fixtures/photos",
        outputs=(
            "- `photo_analysis.json` — per-photo screening results\n"
            "- `photo_summary.md`\n"
            "- `review_queue.json` — poor-quality / uncertain items"
        ),
        fixtures=["photos"],
        tools=["make_photo_fixtures.py"],
        test_file="test_s09.py",
    ),
    dict(
        name="asphalt-estimate-report-builder",
        module="s10_estimate_report_builder",
        script_id="s10",
        skill_dir="s10_estimate_report_builder",
        doc_file="10-S10-estimate-report-builder.md",
        title="Asphalt Estimate Report Builder",
        one_line="Generate a reproducible, audit-ready estimate report from already structured and validated data.",
        intro=(
            "Assembles project.json, takeoff, specifications, quotes, supplier prices, delivery "
            "tickets and weather notes into a single report with the required sections: project "
            "summary, takeoff, pavement sections, material quantities, order quantities, truckloads, "
            "cost basis, supplier evidence, quote comparison, delivery reconciliation, weather notes, "
            "risk/review flags, source register and calculation register. It never discovers new "
            "facts, fills missing values or picks a contractor; every important value traces to a "
            "source or a named deterministic engine run."
        ),
        usage="python -m scripts.s10_estimate_report_builder --project ./project --format md",
        outputs=(
            "- `estimate_report.json|md|xlsx|pdf|csv` (selected by `--format`)\n"
            "- every engine number records `engine_version` and its inputs"
        ),
        fixtures=[],
        tools=[],
        test_file="test_s10.py",
    ),
]


def write_pyproject(dst: Path, repo: dict) -> None:
    content = f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{repo['name']}"
version = "1.0.0"
description = "{repo['one_line']}"
readme = "README.md"
requires-python = ">=3.12"
license = {{ text = "MIT" }}
authors = [{{ name = "Asphalt Desktop Intelligence contributors" }}]
dependencies = [
    "PyMuPDF>=1.24",
    "pdfminer.six>=20240706",
    "openpyxl>=3.1",
    "Pillow>=10.0",
    "reportlab>=4.0",
    "requests>=2.31",
]

[project.urls]
Website = "{WEBSITE}"

[tool.setuptools]
packages = ["common", "scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
"""
    (dst / "pyproject.toml").write_text(content, encoding="utf-8")


def render_readme(repo: dict) -> str:
    return README_TEMPLATE.format(
        title=repo["title"],
        one_line=repo["one_line"],
        website=WEBSITE,
        intro=repo["intro"],
        usage=repo["usage"],
        outputs=repo["outputs"],
        engine_note=ENGINE_NOTE,
    )


def build_one(repo: dict) -> Path:
    d = OUT / repo["name"]
    d.mkdir(parents=True, exist_ok=True)
    for f in ("LICENSE", ".gitignore", "config.example.json", "requirements.txt"):
        shutil.copy2(SRC / f, d / f)
    write_pyproject(d, repo)
    (d / "README.md").write_text(render_readme(repo), encoding="utf-8")

    shutil.copytree(SRC / "common", d / "common", dirs_exist_ok=True)

    (d / "scripts").mkdir(exist_ok=True)
    shutil.copy2(SRC / "scripts" / "__init__.py", d / "scripts" / "__init__.py")
    shutil.copy2(SRC / "scripts" / f"{repo['module']}.py", d / "scripts" / f"{repo['module']}.py")

    (d / "tests").mkdir(exist_ok=True)
    shutil.copy2(SRC / "tests" / "conftest.py", d / "tests" / "conftest.py")
    shutil.copy2(SRC / "tests" / repo["test_file"], d / "tests" / repo["test_file"])

    for rel in repo["fixtures"]:
        src = SRC / "fixtures" / rel
        dst = d / "fixtures" / rel
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    if repo["tools"]:
        (d / "tools").mkdir(exist_ok=True)
        shutil.copy2(SRC / "tools" / "__init__.py", d / "tools" / "__init__.py")
        for t in repo["tools"]:
            shutil.copy2(SRC / "tools" / t, d / "tools" / t)

    (d / "skills" / repo["skill_dir"]).mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "skills" / repo["skill_dir"] / "SKILL.md", d / "skills" / repo["skill_dir"] / "SKILL.md")

    (d / "docs").mkdir(exist_ok=True)
    shutil.copy2(SRC / "docs" / "00-DESKTOP-ARCHITECTURE.md", d / "docs" / "00-DESKTOP-ARCHITECTURE.md")
    shutil.copy2(SRC / "docs" / repo["doc_file"], d / "docs" / repo["doc_file"])
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for repo in REPOS:
        build_one(repo)
        print(f"built {repo['name']}")
    print(f"{len(REPOS)} repos under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
