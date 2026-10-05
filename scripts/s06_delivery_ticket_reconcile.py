#!/usr/bin/env python3
"""S06 — Asphalt Delivery Ticket Reconciliation.

Extract asphalt delivery ticket data and reconcile delivered material with
estimated quantity, purchase orders and paving records.

Validation: gross - tare ~ net; duplicate ticket IDs; impossible timestamps;
missing net weight; mix mismatch against specification. Every cause of a
variance is labeled OBSERVED / POSSIBLE / UNVERIFIED — never stated as fact
without evidence.
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
from common.config import get as cfg_get  # noqa: E402
from common.errors import UnsupportedFileError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402
from common.pdftext import PDFText  # noqa: E402
from common.schemas import ReviewQueue  # noqa: E402

FIELD_ALIASES = {
    "plant": ["plant", "plant name", "facility"],
    "supplier": ["supplier", "vendor", "company", "producer"],
    "truck_id": ["truck", "truck id", "truck no", "vehicle", "unit"],
    "load_id": ["load", "load id", "load no", "ticket no", "ticket", "ticket number", "scale ticket"],
    "date": ["date", "delivery date"],
    "time": ["time", "time in", "time out"],
    "mix": ["mix", "mix id", "mix design", "material", "type"],
    "net_tons": ["net", "net tons", "net tonnage", "tons", "nett"],
    "gross": ["gross", "gross weight", "gross tons"],
    "tare": ["tare", "tare weight", "tare tons"],
}

TONS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:tons?|t)\b", re.I)
DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")
DATE_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(am|pm)?", re.I)


def add_extra_args(parser):
    parser.add_argument("--estimate", type=float, help="estimated tons (or reads from takeoff calc when --takeoff given)")
    parser.add_argument("--takeoff", help="optional takeoff.json containing engine calc results")
    parser.add_argument("--po", help="optional purchase order JSON")
    parser.add_argument("--mix-spec", help="expected mix designation; mismatches are flagged")
    parser.add_argument("--date-range", help="YYYY-MM-DD..YYYY-MM-DD delivery window")


def _find_column(reader_headers: list[str], keys: list[str]) -> str | None:
    lowered = [h.strip().lower() for h in reader_headers]
    for key in keys:
        for i, h in enumerate(lowered):
            if h == key or h.startswith(key) or key in h:
                return reader_headers[i]
    return None


def parse_ticket_csv(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    headers = list(rows[0].keys()) if rows else []
    tickets: list[dict] = []
    for row in rows:
        t: dict = {"source_file": str(path), "source_kind": "csv"}
        for field, aliases in FIELD_ALIASES.items():
            col = _find_column(headers, aliases)
            if col and row.get(col):
                t[field] = row[col].strip()
        tickets.append(t)
    return tickets


def parse_ticket_text(text: str, path: Path) -> list[dict]:
    """Heuristic ticket parsing from extracted text/OCR blocks."""
    tickets: list[dict] = []
    # a ticket typically contains multiple tonnage numbers; split by blank lines
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        if len(block.strip()) < 10:
            continue
        tons = [float(m.group(1)) for m in TONS_RE.finditer(block)]
        if not tons:
            continue
        t: dict = {"source_file": str(path), "source_kind": "text"}
        m = DATE_RE.search(block) or DATE_ISO_RE.search(block)
        if m:
            t["date"] = m.group(0)
        tm = TIME_RE.search(block)
        if tm:
            t["time"] = tm.group(0)
        # last numeric tonnage is usually net; previous two gross/tare
        t["net_tons"] = tons[-1]
        if len(tons) >= 3:
            t["gross"] = tons[-3]
            t["tare"] = tons[-2]
        elif len(tons) >= 2:
            t["net_tons"] = tons[-1]
        mix = re.search(r"\b(PG\s*\d{2,3}-\d{2,3}|[A-Z]{1,4}\s*[-_ ]?\d+(?:\.\d+)?)\b", block, re.I)
        if mix:
            t["mix"] = mix.group(0)
        t["load_id"] = re.sub(r"\s+", "", block[:60])
        tickets.append(t)
    return tickets


def _as_float(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"[\d,]+(?:\.\d+)?", str(v))
    return float(m.group(0).replace(",", "")) if m else None


def validate_tickets(tickets: list[dict], config: dict, mix_spec: str | None) -> tuple[list[dict], ReviewQueue]:
    review = ReviewQueue()
    seen_ids: dict[str, str] = {}
    tol = cfg_get(config, "validation.ticket_gross_tare_tolerance_tons", 0.5)
    now = datetime.now(timezone.utc)

    for t in tickets:
        t.setdefault("exceptions", [])
        t["net_tons"] = _as_float(t.get("net_tons"))
        t["gross"] = _as_float(t.get("gross"))
        t["tare"] = _as_float(t.get("tare"))

        # gross - tare ~ net
        if t["gross"] is not None and t["tare"] is not None and t["net_tons"] is not None:
            diff = abs((t["gross"] - t["tare"]) - t["net_tons"])
            if diff > tol:
                t["exceptions"].append({"code": "E010", "message": f"gross - tare ({t['gross'] - t['tare']:.2f}) != net ({t['net_tons']:.2f}) by {diff:.2f} tons"})
        elif t["net_tons"] is None:
            t["exceptions"].append({"code": "E004", "message": "missing net weight"})
            review.add("missing net weight", f"{t.get('load_id', 'unknown load')}: no net tons", 0.4, t)

        # duplicate ticket / load ids
        lid = t.get("load_id")
        if lid:
            if lid in seen_ids:
                t["exceptions"].append({"code": "E006", "message": f"duplicate ticket id {lid!r} (also {seen_ids[lid]})"})
                review.add("duplicate ticket", f"load_id {lid!r} duplicated", 0.99, t)
            else:
                seen_ids[lid] = t.get("source_file", "")

        # impossible timestamps
        date_str = t.get("date")
        if date_str:
            try:
                m = DATE_RE.search(date_str) or DATE_ISO_RE.search(date_str)
                if m:
                    parts = m.groups()
                    if len(parts[2]) == 2:
                        year = 2000 + int(parts[2]) if int(parts[2]) < 80 else 1900 + int(parts[2])
                    else:
                        year = int(parts[2])
                    dt = datetime(int(year), int(parts[0]), int(parts[1]), tzinfo=timezone.utc)
                    if dt > now:
                        t["exceptions"].append({"code": "E004", "message": f"future/impossible date {date_str}"})
                        review.add("impossible timestamp", date_str, 0.9, t)
            except ValueError:
                t["exceptions"].append({"code": "E004", "message": f"unparseable date {date_str}"})

        # mix mismatch
        if mix_spec and t.get("mix") and mix_spec.lower() not in str(t["mix"]).lower():
            t["exceptions"].append({"code": "E005", "message": f"mix {t['mix']} does not match spec {mix_spec}"})

        t["exceptions"] = sorted(t["exceptions"], key=lambda e: e["code"])
    return tickets, review


def reconcile(tickets: list[dict], estimated_tons: float | None) -> dict:
    # Records with quantity-integrity exceptions (missing net, gross-tare
    # mismatch) or duplicate ids are moved to review and excluded from the
    # clean delivered total; mix-mismatch flags do not affect quantity.
    excluded_codes = {"E004", "E006", "E010"}
    clean = [t for t in tickets if not (t.get("exceptions") and any(e["code"] in excluded_codes for e in t["exceptions"]))]
    delivered = sum(t["net_tons"] for t in clean if t["net_tons"] is not None)
    all_rows = sum(t["net_tons"] for t in tickets if t["net_tons"] is not None)
    truck_count = len({t.get("truck_id") for t in tickets if t.get("truck_id")})
    load_count = len(tickets)
    variance_tons = delivered - estimated_tons if estimated_tons else None
    variance_percent = variance_tons / estimated_tons * 100 if estimated_tons else None
    causes = []
    if estimated_tons and variance_percent is not None and abs(variance_percent) > 2:
        if variance_percent > 0:
            causes.extend(
                [
                    {"label": "POSSIBLE", "cause": "order allowance included in placed quantity"},
                    {"label": "POSSIBLE", "cause": "thicker effective placement than estimated"},
                    {"label": "POSSIBLE", "cause": "subgrade/base corrections consumed additional mix"},
                ]
            )
        else:
            causes.extend(
                [
                    {"label": "POSSIBLE", "cause": "short placement or unrecorded returns"},
                    {"label": "POSSIBLE", "cause": "estimate included scope not yet delivered"},
                ]
            )
    return {
        "delivered_total_tons": round(delivered, 6),
        "all_rows_total_tons": round(all_rows, 6),
        "estimated_tons": estimated_tons,
        "variance_tons": round(variance_tons, 6) if variance_tons is not None else None,
        "variance_percent": round(variance_percent, 3) if variance_percent is not None else None,
        "truck_count": truck_count,
        "load_count": load_count,
        "exceptions": [e for t in tickets for e in t["exceptions"]],
        "variance_causes": causes,
    }


def pipeline(args, config, audit):
    from common.hashing import sha256_file

    input_path = Path(args.input or ".")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*")) if input_path.is_dir() else []
    if not files:
        raise UnsupportedFileError(f"No ticket files found under {input_path}")
    supported = {".csv", ".pdf", ".txt", ".jpg", ".jpeg", ".png"}
    files = [f for f in files if f.suffix.lower() in supported]
    if not files:
        raise UnsupportedFileError(f"No supported ticket files under {input_path} (CSV/PDF/TXT/JPG/PNG)")

    estimated = args.estimate
    if estimated is None and args.takeoff and Path(args.takeoff).exists():
        with open(args.takeoff, "r", encoding="utf-8") as fh:
            takeoff = json.load(fh)
        for rec in takeoff.get("takeoff", []):
            calc = rec.get("calc")
            if calc and calc.get("order_tons"):
                estimated = (estimated or 0) + float(calc["order_tons"])

    review = ReviewQueue()
    tickets: list[dict] = []
    for f in files:
        digest = sha256_file(f)
        audit.add_input(str(f), digest)
        ext = f.suffix.lower()
        log(args, f"[S06] processing {f.name}")
        if ext == ".csv":
            tickets.extend(parse_ticket_csv(f))
        elif ext in (".pdf", ".txt"):
            if ext == ".pdf":
                pdf = PDFText(f)
                text = pdf.full_text()
            else:
                text = f.read_text(encoding="utf-8", errors="replace")
            tickets.extend(parse_ticket_text(text, f))
        else:  # images: OCR if available, else route to review
            text = _try_ocr(f)
            if text:
                tickets.extend(parse_ticket_text(text, f))
            else:
                review.add(
                    "OCR unavailable",
                    f"{f.name}: image ticket needs OCR (install pytesseract + Tesseract) or manual entry",
                    0.0,
                    {"source_file": str(f)},
                )

    tickets, ticket_review = validate_tickets(tickets, config, args.mix_spec)
    for item in ticket_review.items:
        review.items.append(item)

    # chronological sorting
    tickets_sorted = sorted(tickets, key=lambda t: (t.get("date") or "", t.get("time") or ""))

    result = reconcile(tickets_sorted, estimated)
    result["tickets"] = tickets_sorted
    result["review_summary"] = review.summary_lines()

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["reconciliation"] = (str(project_out / "delivery_reconciliation.json"), "json", result)
    outputs["reconciliation_csv"] = (
        str(project_out / "delivery_reconciliation.csv"),
        "csv",
        [
            {
                "load_id": t.get("load_id", ""),
                "date": t.get("date", ""),
                "time": t.get("time", ""),
                "mix": t.get("mix", ""),
                "plant": t.get("plant", ""),
                "truck_id": t.get("truck_id", ""),
                "gross": t.get("gross", ""),
                "tare": t.get("tare", ""),
                "net_tons": t.get("net_tons", ""),
                "exceptions": "; ".join(e["code"] for e in t.get("exceptions", [])),
            }
            for t in tickets_sorted
        ],
    )
    outputs["exceptions"] = (str(project_out / "exceptions.md"), "md", _exceptions_md(result, tickets_sorted))
    return outputs


def _try_ocr(path: Path) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        return pytesseract.image_to_string(Image.open(path))
    except (ImportError, Exception):  # noqa: BLE001 - OCR is best-effort
        return ""


def _exceptions_md(result, tickets) -> list[tuple[str, str]]:
    summary_rows = [
        {"metric": k, "value": v}
        for k, v in result.items()
        if k not in ("tickets", "review_summary")
        and not isinstance(v, list)
    ]
    def fmt(v) -> str:
        return f"{v:,.3f}" if isinstance(v, (int, float)) else str(v)

    sections = [
        ("Delivery Reconciliation",
         f"- delivered (clean tickets): {fmt(result['delivered_total_tons'])} tons\n- estimated: {fmt(result['estimated_tons'])} tons\n- variance: {fmt(result['variance_tons'])} tons ({fmt(result['variance_percent'])}%)"),
        ("Summary", _table_to_markdown(summary_rows)),
    ]
    exceptions = [(e, t) for t in tickets for e in t.get("exceptions", [])]
    if exceptions:
        sections.append(
            ("Exceptions",
             "\n".join(f"- [{e['code']}] {e['message']} ({t.get('load_id', '?')})" for e, t in exceptions))
        )
    if result.get("variance_causes"):
        sections.append(
            ("Variance Causes (labeled, not facts)",
             "\n".join(f"- [{c['label']}] {c['cause']}" for c in result["variance_causes"]))
        )
    return sections


def main() -> int:
    parser = build_parser("s06_delivery_ticket_reconcile", "Asphalt delivery ticket reconciliation (S06)", add_extra_args)
    return run_lifecycle(parser, "s06_delivery_ticket_reconcile", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
