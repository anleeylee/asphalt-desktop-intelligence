#!/usr/bin/env python3
"""S10 — Asphalt Estimate & Audit Report Builder.

Turn already structured takeoff, specification, quote, supplier and ticket
data into one reproducible project estimate/report. A report builder, not a
mega-agent: it does not discover documents on its own and does not silently
invent missing values.

All asphalt quantities use the AsphaltCosts engine where supported; every
calculated field records the engine/version or calculation run ID.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.asphaltcosts_client import AsphaltCostsClient  # noqa: E402
from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.errors import MissingSourceError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402

STATUSES = ("INFO", "REVIEW", "WARNING", "MISMATCH", "MISSING DATA")


def add_extra_args(parser):
    parser.add_argument("--density", type=float, default=145.0, help="density lb/ft3 for engine calculations")
    parser.add_argument("--allowance", type=float, default=0.05, help="order allowance")
    parser.add_argument("--truck-capacity", dest="truck_capacity", type=float, default=20.0, help="truck capacity tons")


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def build_report(args, config) -> dict:
    project_dir = Path(args.project)
    pj = _load(project_dir / "project.json")
    out = project_dir / "output"
    takeoff = _load(out / "takeoff.json")
    specs = _load(out / "spec_requirements.json")
    conflicts = _load(out / "conflicts.json")
    quotes = _load(out / "quote_comparison.json")
    suppliers = _load(out / "supplier_prices.json")
    tickets = _load(out / "delivery_reconciliation.json")
    weather = _load(out / "thermal_run.json")
    cad = _load(out / "cad_takeoff.json")
    photos = _load(out / "photo_analysis.json")

    report: dict = {
        "report_title": f"Project Estimate — {(pj or {}).get('name') or 'Unnamed Project'}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": pj or {},
        "sections": {},
        "flags": [],
    }

    def flag(status: str, item: str, detail: str) -> None:
        if status not in STATUSES:
            status = "INFO"
        report["flags"].append({"status": status, "item": item, "detail": detail})

    # ---- Takeoff -----------------------------------------------------------
    takeoff_records = (takeoff or {}).get("takeoff", [])
    report["sections"]["takeoff"] = takeoff_records
    if not takeoff_records:
        flag("MISSING DATA", "takeoff", "no takeoff.json found in project output")
    for rec in takeoff_records:
        if rec.get("state") != "VERIFIED" and rec.get("confidence", 0) < 0.95:
            flag("REVIEW", f"takeoff {rec['area_id']}", f"state={rec['state']} confidence={rec['confidence']:.2f}")

    # ---- Engine material quantities ---------------------------------------
    client = AsphaltCostsClient(config)
    material_quantities: list[dict] = []
    calc_register: list[dict] = []
    for rec in takeoff_records:
        if not rec.get("thickness"):
            continue
        calc = client.calculate_quantity(
            rec["quantity"],
            rec["thickness"],
            density_pcf=args.density,
            order_allowance=args.allowance,
            truck_capacity_tons=args.truck_capacity,
            calc_id=f"report-{rec['area_id']}",
        )
        material_quantities.append(
            {
                "area_id": rec["area_id"],
                "area_sq_ft": rec["quantity"],
                "thickness_in": rec["thickness"],
                "net_tons": calc["net_tons"],
                "order_tons": calc["order_tons"],
                "truckloads": calc["truckloads"],
                "engine_version": calc["engine_version"],
                "calc_id": calc["calc_id"],
            }
        )
        calc_register.append(
            {
                "calc_id": calc["calc_id"],
                "engine_version": calc["engine_version"],
                "method": calc["method"],
                "inputs": {
                    "area_sq_ft": rec["quantity"],
                    "thickness_in": rec["thickness"],
                    "density_pcf": args.density,
                    "allowance": args.allowance,
                },
                "output": {"net_tons": calc["net_tons"], "order_tons": calc["order_tons"]},
            }
        )
    report["sections"]["material_quantities"] = material_quantities
    report["sections"]["order_quantities"] = [
        {"area_id": m["area_id"], "order_tons": m["order_tons"], "truckloads": m["truckloads"]}
        for m in material_quantities
    ]
    total_order_tons = sum(m["order_tons"] for m in material_quantities)
    report["sections"]["totals"] = {"total_order_tons": round(total_order_tons, 3), "total_net_tons": round(sum(m["net_tons"] for m in material_quantities), 3)}

    # ---- Specs / conflicts -------------------------------------------------
    report["sections"]["specifications"] = (specs or {}).get("requirements", [])
    report["sections"]["conflicts"] = (conflicts or {}).get("conflicts", [])
    for c in (conflicts or {}).get("conflicts", []):
        flag("MISMATCH", f"{c['mode']} {c['field']}", f"{c['value_a']} vs {c['value_b']}")

    # ---- Quotes ------------------------------------------------------------
    report["sections"]["quote_comparison"] = (quotes or {}).get("comparison", [])
    for q in (quotes or {}).get("quotes", []):
        for f in q.get("flags", []):
            flag(f.get("status", "REVIEW"), f"quote {q.get('quote_id')}", f.get("detail", f["flag"]))

    # ---- Suppliers ---------------------------------------------------------
    report["sections"]["supplier_evidence"] = (suppliers or {}).get("prices", [])
    if not (suppliers or {}).get("prices"):
        flag("MISSING DATA", "supplier evidence", "no supplier_prices.json found")

    # ---- Tickets -----------------------------------------------------------
    report["sections"]["delivery_reconciliation"] = {k: v for k, v in (tickets or {}).items() if k not in ("tickets", "review_summary")}
    if tickets:
        vp = tickets.get("variance_percent")
        if vp is not None and abs(vp) > 5:
            flag("WARNING", "delivery variance", f"{tickets.get('variance_tons')} tons ({vp:.1f}%) vs estimate")

    # ---- Weather / photos --------------------------------------------------
    report["sections"]["weather_notes"] = (
        {k: weather[k] for k in ("estimated_window_minutes", "model_version", "status", "risk_factors")}
        if weather
        else None
    )
    if weather and weather.get("risk_factors"):
        for r in weather["risk_factors"]:
            flag("WARNING", r["label"], r["detail"])
    report["sections"]["photo_screening"] = {
        "photos": len((photos or {}).get("photos", [])),
        "screening_only": (photos or {}).get("screening_only", True),
    }

    # ---- Source register ---------------------------------------------------
    sources = []
    for d in (pj or {}).get("documents", []):
        sources.append({"doc_id": d["doc_id"], "path": d["path"], "sha256": d["sha256"], "category": d["category"]})
    report["sections"]["source_register"] = sources
    report["sections"]["calculation_register"] = calc_register
    report["engine_version"] = client.engine_version
    return report


def pipeline(args, config, audit):
    from common.asphaltcosts_client import AsphaltCostsClient

    client = AsphaltCostsClient(config)
    audit.set_engine(client.engine_version)
    project_dir = Path(args.project)
    if not (project_dir / "project.json").exists():
        raise MissingSourceError(f"project.json not found under {project_dir}; run S01 first")

    report = build_report(args, config)
    fmt = args.format or "json"

    project_out = project_dir / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["report_json"] = (str(project_out / "estimate_report.json"), "json", report)
    outputs["report_md"] = (str(project_out / "estimate_report.md"), "md", _report_sections(report))
    if fmt == "xlsx":
        outputs["report_xlsx"] = (str(project_out / "estimate_report.xlsx"), "xlsx", _xlsx_sheets(report))
    if fmt == "pdf":
        outputs["report_pdf"] = (str(project_out / "estimate_report.pdf"), "pdf", ("Project Estimate", _report_sections(report)))
    if fmt == "csv":
        outputs["report_csv"] = (str(project_out / "estimate_report.csv"), "csv", _csv_rows(report))
    return outputs


def _report_sections(report: dict) -> list[tuple[str, str]]:
    s: list[tuple[str, str]] = [
        ("Project Summary",
         f"- {report['report_title']}\n- generated: {report['generated_at']}\n- project_id: {(report['project'] or {}).get('project_id')}"),
    ]
    takeoff = report["sections"].get("takeoff", [])
    s.append(("Takeoff", _table_to_markdown([
        {"area_id": r["area_id"], "sheet": r["sheet"], "surface": r["surface"], "quantity": f"{r['quantity']:,.0f}", "unit": r["unit"], "thickness": r.get("thickness") or "", "state": r["state"]}
        for r in takeoff
    ])))
    mq = report["sections"].get("material_quantities", [])
    s.append(("Material Quantities", _table_to_markdown([
        {"area_id": m["area_id"], "net_tons": f"{m['net_tons']:,.2f}", "order_tons": f"{m['order_tons']:,.2f}", "truckloads": m["truckloads"], "engine": m["engine_version"]}
        for m in mq
    ])))
    s.append(("Order Quantities & Truckloads", _table_to_markdown(report["sections"].get("order_quantities", []))))
    specs = report["sections"].get("specifications", [])
    s.append(("Specification Requirements", _table_to_markdown([
        {"field": r["label"], "value": r["value"], "classification": r["classification"], "page": r["source_page"]}
        for r in specs[:30]
    ])))
    quotes = report["sections"].get("quote_comparison", [])
    s.append(("Quote Comparison", _table_to_markdown(quotes)))
    suppliers = report["sections"].get("supplier_evidence", [])
    s.append(("Supplier Evidence", _table_to_markdown([
        {"supplier": p["supplier"], "mix": p.get("mix") or "", "unit": p["unit"], "unit_price": p["unit_price"], "basis": p["price_basis"], "expires": p.get("expiration_date") or ""}
        for p in suppliers[:30]
    ])))
    tickets = report["sections"].get("delivery_reconciliation") or {}
    s.append(("Delivery Reconciliation", _table_to_markdown([
        {"metric": k, "value": v} for k, v in tickets.items() if not isinstance(v, list)
    ])))
    weather = report["sections"].get("weather_notes")
    if weather:
        s.append(("Weather / Compaction Notes", _table_to_markdown([
            {"metric": k, "value": v} for k, v in weather.items() if not isinstance(v, list)
        ])))
    flags = report["flags"]
    s.append(("Risk & Review Flags", _table_to_markdown(flags) if flags else "_no flags_"))
    sources = report["sections"].get("source_register", [])
    s.append(("Source Register", _table_to_markdown([
        {"doc_id": d["doc_id"], "path": d["path"], "category": d["category"], "sha256": d["sha256"][:12]} for d in sources
    ])))
    calcs = report["sections"].get("calculation_register", [])
    s.append(("Calculation Register", _table_to_markdown([
        {"calc_id": c["calc_id"], "engine": c["engine_version"], "method": c["method"], "area_sq_ft": c["inputs"]["area_sq_ft"], "net_tons": c["output"]["net_tons"]}
        for c in calcs
    ])))
    return s


def _xlsx_sheets(report: dict) -> dict:
    return {
        "Project": [{"field": k, "value": v} for k, v in (report.get("project") or {}).items() if not isinstance(v, list)],
        "Takeoff": report["sections"].get("takeoff", []),
        "Material Quantities": report["sections"].get("material_quantities", []),
        "Flags": report["flags"],
    }


def _csv_rows(report: dict) -> list[dict]:
    return [
        {"status": f["status"], "item": f["item"], "detail": f["detail"]}
        for f in report["flags"]
    ]


def main() -> int:
    parser = build_parser("s10_estimate_report_builder", "Asphalt estimate & audit report builder (S10)", add_extra_args)
    return run_lifecycle(parser, "s10_estimate_report_builder", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
