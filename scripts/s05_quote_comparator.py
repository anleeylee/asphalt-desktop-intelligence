#!/usr/bin/env python3
"""S05 — Asphalt Contractor Quote Comparator.

Turn one or more contractor quotes into a standardized scope/quantity/cost
comparison. Reports objective differences and unresolved omissions only —
never a "best contractor" ranking.

Derived metrics ($/SF, $/ton, implied tons/1000 SF, implied thickness, scope
inclusion rate) use deterministic formulas.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.ai_adapter import AIAdapter  # noqa: E402
from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.config import get as cfg_get  # noqa: E402
from common.errors import UnsupportedFileError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402
from common.pdftext import PDFText  # noqa: E402
from common.schemas import ReviewQueue  # noqa: E402

MONEY_RE = re.compile(r"\$?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:/|per\s+|\s+)?", re.I)
MONEY_UNIT_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d{1,2})?)\s*(?:/\s*(ton|sf|sq\s*ft|square\s*foot|square\s*feet|yd|yard|ton\s*delivered)|per\s+(ton|sf|sq\s*ft|square\s*foot|square\s*feet|yd|yard))?", re.I
)
TOTAL_RE = re.compile(
    r"(?:\$\s*([\d,]+(?:\.\d{1,2})?)\s*(?:\.00)?\s*(?:total|grand\s*total|bid\s*amount)|(?:total|grand\s*total|bid\s*amount)[^$\n]{0,40}\$?\s*([\d,]+(?:\.\d{1,2})?))",
    re.I,
)
AREA_RE = re.compile(r"([\d,]+)\s*(?:sf|sq\s*ft|square\s*feet)\b", re.I)
TONS_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:us\s*)?tons?\b", re.I)
THICKNESS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(in|inch|inches|\"|mm)\s*(?:of|for)?\s*(?:hma|asphalt|ac|pavement|overlays?|surface)\b", re.I
)
THICKNESS_LABEL_RE = re.compile(r"thickness\D{0,20}?(\d+(?:\.\d+)?)\s*(in|inch|inches|\"|mm)\b", re.I)

SCOPE_KEYWORDS = {
    "milling": ["mill", "milling"],
    "removal": ["remov", "demolition", "excavat"],
    "hauling": ["haul"],
    "tack": ["tack"],
    "sealant": ["sealcoat", "seal coat", "sealant", "crack seal"],
    "striping": ["striping", "stripe"],
    "drainage": ["drain", "catch basin", "storm"],
    "mobilization": ["mobilization", "mobilisation", "mobilize"],
    "warranty": ["warrant"],
}

EXCLUSION_KEYWORDS = ["excl", "not included", "does not include"]
ALLOWANCE_KEYWORDS = ["allowance"]


def add_extra_args(parser):
    parser.add_argument("--takeoff", help="optional takeoff.json (project quantity for derived metrics)")
    parser.add_argument("--spec", help="optional spec_requirements.json (thickness check)")
    parser.add_argument("--density", type=float, default=145.0, help="density lb/ft3 for implied thickness (default 145)")


def parse_quote_text(text: str, quote_id: str, source_file: str) -> dict:
    q: dict = {
        "quote_id": quote_id,
        "source_file": source_file,
        "scope": {key: False for key in SCOPE_KEYWORDS},
        "costs": {},
        "line_items": [],
        "area_sq_ft": None,
        "asphalt_tons": None,
        "thickness_in": None,
        "base_thickness_in": None,
        "total": None,
        "raw_notes": [],
    }

    lowered = text.lower()
    for key, keywords in SCOPE_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            q["scope"][key] = True

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 4:
            continue
        m = MONEY_UNIT_RE.search(line)
        if m:
            amount = float(m.group(1).replace(",", ""))
            unit = (m.group(2) or m.group(3) or "").lower()
            q["line_items"].append({"line": line[:160], "amount": amount, "unit": unit})
        tm = TOTAL_RE.search(line)
        if tm:
            q["total"] = float((tm.group(1) or tm.group(2)).replace(",", ""))

    m = AREA_RE.search(text)
    if m:
        q["area_sq_ft"] = float(m.group(1).replace(",", ""))
    m = TONS_RE.search(text)
    if m:
        q["asphalt_tons"] = float(m.group(1).replace(",", ""))
    # thickness: pick the value on an asphalt/thickness line, not a milling note
    q["thickness_in"] = None
    for line in text.splitlines():
        if re.search(r"milling\s*\d|milling.*(?:included|removed|removal)", line, re.I):
            continue
        if re.search(r"(hma|asphalt|pavement|overlay|thickness|thick)", line, re.I):
            m = THICKNESS_RE.search(line) or THICKNESS_LABEL_RE.search(line)
            if m:
                q["thickness_in"] = float(m.group(1))
                break
    # classify base thickness vs asphalt thickness by proximity to "base"
    base_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|inches|\")\s*(?:of\s*)?(?:aggregate|base)", text, re.I)
    if base_match:
        q["base_thickness_in"] = float(base_match.group(1))

    if any(kw in lowered for kw in EXCLUSION_KEYWORDS):
        q["raw_notes"].append("exclusions mentioned")
    if any(kw in lowered for kw in ALLOWANCE_KEYWORDS):
        q["raw_notes"].append("allowances mentioned")
    return q


def parse_quote_csv(path: Path, quote_id: str) -> dict:
    q: dict = {"quote_id": quote_id, "source_file": str(path), "scope": {k: False for k in SCOPE_KEYWORDS}, "costs": {}, "line_items": [], "raw_notes": []}
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    for row in rows:
        q["line_items"].append(row)
    q["asphalt_tons"] = None
    q["area_sq_ft"] = None
    q["total"] = None
    q["thickness_in"] = None
    q["base_thickness_in"] = None
    return q


def derive_metrics(q: dict, project_area: float | None, spec_thickness: float | None, density: float) -> dict:
    metrics = {}
    total = q.get("total")
    area = q.get("area_sq_ft") or project_area
    tons = q.get("asphalt_tons")
    if total and area:
        metrics["cost_per_sqft"] = round(total / area, 4)
    if total and tons:
        metrics["cost_per_ton"] = round(total / tons, 2)
    if tons and area:
        metrics["implied_tons_per_1000_sqft"] = round(tons / area * 1000, 3)
        metrics["implied_thickness_in"] = round(tons * 2000 / (density * area) * 12, 2)
    if spec_thickness:
        metrics["spec_thickness_in"] = spec_thickness
    return metrics


def flags_for(q: dict, metrics: dict, project_area: float | None, spec_thickness: float | None) -> list[dict]:
    flags: list[dict] = []
    area = q.get("area_sq_ft")
    if project_area and area:
        diff_pct = abs(area - project_area) / project_area * 100
        if diff_pct > 5:
            flags.append({"flag": "area_mismatch", "detail": f"quoted {area:,.0f} SF vs plan {project_area:,.0f} SF ({diff_pct:.1f}%)", "status": "REVIEW"})
    elif project_area and not area:
        flags.append({"flag": "missing_area", "detail": "quote omits paving area; plan area available", "status": "MISSING DATA"})

    for key in ("milling", "removal", "tack", "striping", "warranty"):
        if not q["scope"].get(key):
            flags.append({"flag": "missing_scope", "detail": f"scope item {key!r} not mentioned", "status": "MISSING DATA"})

    if spec_thickness and q.get("thickness_in") and abs(q["thickness_in"] - spec_thickness) > 1e-9:
        flags.append({"flag": "thickness_mismatch", "detail": f"quoted {q['thickness_in']} in vs spec {spec_thickness} in", "status": "MISMATCH"})

    if not q.get("total"):
        flags.append({"flag": "missing_total", "detail": "no grand total found", "status": "MISSING DATA"})
    if q.get("asphalt_tons") is None:
        flags.append({"flag": "missing_tons", "detail": "no tonnage quoted; $/ton and implied thickness cannot be derived", "status": "MISSING DATA"})
    if q.get("asphalt_tons") and not q.get("area_sq_ft") and project_area:
        flags.append({"flag": "tons_without_area", "detail": "tons quoted but area unknown", "status": "REVIEW"})

    # unit price present but extension missing
    unit_price_lines = [li for li in q["line_items"] if isinstance(li, dict) and li.get("unit")]
    if unit_price_lines and not q.get("total"):
        flags.append({"flag": "incomplete_extension", "detail": f"{len(unit_price_lines)} unit-price line(s) without a total", "status": "REVIEW"})
    return flags


def pipeline(args, config, audit):
    from common.hashing import sha256_file

    input_path = Path(args.input or ".")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*")) if input_path.is_dir() else []
    if not files:
        raise UnsupportedFileError(f"No quote files found under {input_path}")

    takeoff = None
    if args.takeoff and Path(args.takeoff).exists():
        with open(args.takeoff, "r", encoding="utf-8") as fh:
            takeoff = json.load(fh)
    project_area = None
    if takeoff:
        recs = takeoff.get("takeoff", takeoff if isinstance(takeoff, list) else [])
        if recs:
            project_area = sum(float(r["quantity"]) for r in recs if isinstance(r, dict) and r.get("quantity"))

    spec = None
    spec_thickness = None
    if args.spec and Path(args.spec).exists():
        with open(args.spec, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        for req in spec.get("requirements", []):
            if req.get("field") == "thickness" and req.get("classification") in ("REQUIRED", "RECOMMENDED"):
                try:
                    spec_thickness = float(req["value"])
                except (TypeError, ValueError):
                    pass

    ai = AIAdapter(config)
    audit.set_model_provider(ai.provider, ai.model)
    review = ReviewQueue()

    quotes: list[dict] = []
    for idx, f in enumerate(files, start=1):
        digest = sha256_file(f)
        audit.add_input(str(f), digest)
        quote_id = f"Q-{idx:02d}"
        log(args, f"[S05] processing {f.name}")
        ext = f.suffix.lower()
        if ext == ".csv":
            q = parse_quote_csv(f, quote_id)
        elif ext == ".pdf":
            pdf = PDFText(f)
            q = parse_quote_text(pdf.full_text(), quote_id, str(f))
        elif ext in (".txt", ".md", ".json"):
            text = f.read_text(encoding="utf-8", errors="replace")
            if ext == ".json":
                try:
                    data = json.loads(text)
                    text = json.dumps(data.get("quote", data), ensure_ascii=False)
                except ValueError:
                    pass
            q = parse_quote_text(text, quote_id, str(f))
        else:
            raise UnsupportedFileError(f"Unsupported quote format: {ext}", detail=str(f))

        q["metrics"] = derive_metrics(q, project_area, spec_thickness, args.density)
        q["flags"] = flags_for(q, q["metrics"], project_area, spec_thickness)
        for flag in q["flags"]:
            review.add(flag["flag"], flag["detail"], 0.99, {"quote_id": quote_id})
        quotes.append(q)

    comparison_rows = [
        {
            "quote_id": q["quote_id"],
            "area_sq_ft": f"{q['area_sq_ft']:,.0f}" if q.get("area_sq_ft") else "",
            "asphalt_tons": q.get("asphalt_tons") or "",
            "thickness_in": q.get("thickness_in") or "",
            "total": f"${q['total']:,.2f}" if q.get("total") else "",
            "cost_per_sqft": q["metrics"].get("cost_per_sqft", ""),
            "cost_per_ton": q["metrics"].get("cost_per_ton", ""),
            "implied_tons_per_1000sqft": q["metrics"].get("implied_tons_per_1000_sqft", ""),
            "implied_thickness_in": q["metrics"].get("implied_thickness_in", ""),
            "flags": "; ".join(fl["flag"] for fl in q["flags"]),
        }
        for q in quotes
    ]

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["quote_comparison"] = (str(project_out / "quote_comparison.json"), "json", {"quotes": quotes, "comparison": comparison_rows})
    outputs["quote_xlsx"] = (str(project_out / "quote_comparison.xlsx"), "xlsx", {"Comparison": comparison_rows, "Flags": [
        {"quote_id": q["quote_id"], "flag": fl["flag"], "detail": fl["detail"], "status": fl["status"]}
        for q in quotes for fl in q["flags"]
    ]})
    outputs["quote_flags"] = (str(project_out / "quote_flags.md"), "md", _flags_md(quotes, comparison_rows, review))
    return outputs


def _flags_md(quotes, comparison_rows, review) -> list[tuple[str, str]]:
    sections = [
        ("Quote Comparison", f"- quotes compared: {len(quotes)}"),
        ("Normalized Comparison", _table_to_markdown(comparison_rows)),
    ]
    for q in quotes:
        rows = [{"flag": fl["flag"], "detail": fl["detail"], "status": fl["status"]} for fl in q["flags"]]
        sections.append((f"Flags — {q['quote_id']}", _table_to_markdown(rows) if rows else "_no flags_"))
    if review.items:
        sections.append(("Human Review", "\n".join(f"- {line} — see quote_flags.md" for line in review.summary_lines())))
    return sections


def main() -> int:
    parser = build_parser("s05_quote_comparator", "Asphalt contractor quote comparator (S05)", add_extra_args)
    return run_lifecycle(parser, "s05_quote_comparator", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
