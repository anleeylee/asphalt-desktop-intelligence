#!/usr/bin/env python3
"""S07 — Supplier Quote & Material Price Normalizer.

Convert supplier quotes into a structured price evidence dataset usable by cost
calculations and project estimating.

Hard separation (never merged into one generic "asphalt price"):
  material-only price / material + delivery / installed price / public bid price

Taxes, fuel surcharges and minimum loads are kept as separate fields; ambiguous
units go to the review queue.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.errors import UnsupportedFileError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402
from common.pdftext import PDFText  # noqa: E402
from common.schemas import ReviewQueue  # noqa: E402

PRICE_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d{1,3})?)\s*(?:/\s*|per\s+)(ton|t|sf|sq\s*ft|square\s*foot|yd|yard|lb|kg)", re.I
)
DELIVERY_RE = re.compile(r"(?:delivered|delivery|freight|haul)\b", re.I)
INSTALLED_RE = re.compile(r"(?:installed|install\b|lay\b|place\b)", re.I)
BID_RE = re.compile(r"(?:bid\b|public bid|award)", re.I)
MIN_LOAD_RE = re.compile(r"(?:minimum\s*load|min\s*load|minimum\s*order)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.I)
SURCHARGE_RE = re.compile(r"(fuel|tax|surcharge|escalat)", re.I)
EFFECTIVE_RE = re.compile(r"(?:effective|valid\s*from)\s*[:=]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I)
EXPIRY_RE = re.compile(r"(?:expires?|valid\s*until|expiration)\s*[:=]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I)
MIX_RE = re.compile(r"\b(PG\s*\d{2,3}-\d{2,3}|(?:Type|Mix)\s*[A-Z0-9.\-]+)\b", re.I)


def add_extra_args(parser):
    parser.add_argument("--supplier", help="supplier name (override)")
    parser.add_argument("--region", help="supplier location / region")
    parser.add_argument("--project-location", dest="project_location", help="project location")
    parser.add_argument("--quote-date", help="quote date (YYYY-MM-DD)")
    parser.add_argument("--freight-terms", dest="freight_terms", help="freight/delivery terms note")


def classify_basis(text: str) -> str:
    lowered = text.lower()
    if INSTALLED_RE.search(lowered):
        return "installed"
    if BID_RE.search(lowered):
        return "public_bid"
    if DELIVERY_RE.search(lowered):
        return "delivered"
    return "material_only"


def parse_supplier_text(text: str, source_file: str, args, seq: list[int]) -> tuple[list[dict], ReviewQueue]:
    review = ReviewQueue()
    items: list[dict] = []
    doc_surcharges = SURCHARGE_RE.findall(text)
    eff = EFFECTIVE_RE.search(text)
    exp = EXPIRY_RE.search(text)

    for line in text.splitlines():
        m = PRICE_RE.search(line)
        if not m:
            continue
        seq[0] += 1
        price = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        if unit == "t":
            unit = "us_ton"
        elif unit == "sf":
            unit = "sq_ft"
        basis = classify_basis(line)  # per-item basis from the line wording
        mix = MIX_RE.search(line)
        material = "AGG_BASE" if re.search(r"(aggregate|base|crush)", line, re.I) else "HMA"
        min_load = MIN_LOAD_RE.search(line)
        surcharge = SURCHARGE_RE.search(line)
        items.append(
            {
                "item_id": f"SI-{seq[0]:03d}",
                "supplier": args.supplier or "UNSPECIFIED",
                "material": material,
                "mix": mix.group(0).upper() if mix else None,
                "unit": unit,
                "unit_price": price,
                "delivery_price": None,
                "minimum_load": float(min_load.group(1)) if min_load else None,
                "surcharge": (surcharge.group(1).lower() if surcharge else (doc_surcharges[0].lower() if doc_surcharges else None)),
                "price_basis": basis,
                "effective_date": args.quote_date or (eff.group(1) if eff else None),
                "expiration_date": exp.group(1) if exp else None,
                "region": args.region,
                "quote_id": f"SUP-{seq[0]:03d}",
                "source_file": source_file,
                "project_location": args.project_location,
                "freight_terms": args.freight_terms,
                "state": "EXTRACTED",
            }
        )
        if unit not in ("us_ton", "sq_ft", "yd"):
            review.add("ambiguous supplier unit", f"unit {unit!r} on {source_file}", 0.5)
    return items, review


def pipeline(args, config, audit):
    from common.hashing import sha256_file

    input_path = Path(args.input or ".")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*")) if input_path.is_dir() else []
    if not files:
        raise UnsupportedFileError(f"No supplier quote files found under {input_path}")
    supported = {".pdf", ".txt", ".md", ".csv", ".json"}
    files = [f for f in files if f.suffix.lower() in supported]
    if not files:
        raise UnsupportedFileError(f"No supported supplier quote files under {input_path}")

    seq = [0]
    review = ReviewQueue()
    items: list[dict] = []
    for f in files:
        digest = sha256_file(f)
        audit.add_input(str(f), digest)
        log(args, f"[S07] processing {f.name}")
        ext = f.suffix.lower()
        if ext == ".pdf":
            pdf = PDFText(f)
            text = pdf.full_text()
        elif ext == ".csv":
            rows = _csv_rows(f)
            # re-serialize as text with headers for the shared parser
            text = "\n".join(",".join(row.values()) for row in rows)
        elif ext == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            text = json.dumps(data, ensure_ascii=False)
        else:
            text = f.read_text(encoding="utf-8", errors="replace")
        parsed, item_review = parse_supplier_text(text, str(f), args, seq)
        items.extend(parsed)
        for item in item_review.items:
            review.items.append(item)

    rows = [
        {
            "supplier": i["supplier"],
            "mix": i["mix"] or "",
            "unit": i["unit"],
            "unit_price": i["unit_price"],
            "price_basis": i["price_basis"],
            "delivery_price": i.get("delivery_price") or "",
            "minimum_load": i.get("minimum_load") or "",
            "surcharge": i.get("surcharge") or "",
            "effective_date": i.get("effective_date") or "",
            "expiration_date": i.get("expiration_date") or "",
            "region": i.get("region") or "",
            "quote_id": i["quote_id"],
            "source_file": i["source_file"],
        }
        for i in items
    ]

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["supplier_prices"] = (str(project_out / "supplier_prices.json"), "json", {"prices": items, "count": len(items)})
    outputs["supplier_csv"] = (str(project_out / "supplier_prices.csv"), "csv", rows)
    outputs["summary"] = (str(project_out / "supplier_quote_summary.md"), "md", _summary(rows, items, review))
    return outputs


def _csv_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _summary(rows, items, review) -> list[tuple[str, str]]:
    bases = sorted({i["price_basis"] for i in items})
    sections = [
        ("Supplier Quote Summary", f"- line items: {len(items)}\n- price bases kept separate: {', '.join(bases)}"),
        ("Normalized Prices", _table_to_markdown(rows)),
    ]
    if review.items:
        sections.append(("Human Review", "\n".join(f"- {line} — see review queue" for line in review.summary_lines())))
    return sections


def main() -> int:
    parser = build_parser("s07_supplier_quote_normalizer", "Supplier quote & material price normalizer (S07)", add_extra_args)
    return run_lifecycle(parser, "s07_supplier_quote_normalizer", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
