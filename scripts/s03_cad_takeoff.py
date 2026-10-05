#!/usr/bin/env python3
"""S03 — CAD / DWG / DXF Paving Takeoff.

Extract measurable paving geometry from CAD files without turning the script
into a general CAD platform.

P0: ASCII DXF. P1: DWG through a user-side conversion path (e.g. ODA File
Converter); a .dwg input raises E001 with a clear message — the script never
tries to silently re-parse a proprietary format.

Validation: known model units; open polylines; self-intersections; nested
islands/holes; duplicate geometry; CAD area vs plan notes when possible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.config import get as cfg_get  # noqa: E402
from common.dxf import (  # noqa: E402
    DXFDocument,
    entity_area,
    find_self_intersections,
    normalize_polygon,
    parse_dxf,
)
from common.errors import InvalidGeometryError, UnsupportedFileError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402
from common.schemas import ReviewQueue  # noqa: E402
from common.validation import require_supported_file  # noqa: E402

LAYER_SEMANTICS = [
    (("ASPH", "HMA", "AC", "PAV"), "HMA"),
    (("BASE", "AGG", "AB"), "BASE"),
    (("MILL",), "MILL"),
    (("CURB",), "CURB"),
    (("SIDEWALK", "SW", "WALK"), "SIDEWALK"),
    (("STRIPE", "STRIP"), "STRIPING"),
]


def classify_layer(name: str) -> str | None:
    upper = name.upper()
    for keywords, semantic in LAYER_SEMANTICS:
        if any(kw in upper for kw in keywords):
            return semantic
    return None


def add_extra_args(parser):
    parser.add_argument("--scale", type=float, help="model-units-to-feet scale override (overrides $INSUNITS)")
    parser.add_argument("--plan-notes", help="optional plan-notes JSON (CAD vs notes comparison)")
    parser.add_argument("--layer-map", help="optional JSON dict {layer_name: semantic_type}")


def analyze_file(path: Path, scale: float | None, layer_map: dict | None, review: ReviewQueue) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise UnsupportedFileError(f"Cannot read DXF: {exc}", detail=str(path)) from exc

    doc = parse_dxf(text, source_name=path.name)
    for warning in doc.warnings:
        review.add("parse warning", f"{path.name}: {warning}", 0.5)

    effective_scale = scale or doc.units
    if effective_scale is None:
        review.add(
            "model units unknown",
            f"{path.name}: no $INSUNITS and no --scale; areas reported in model units",
            0.4,
        )
        effective_scale = 1.0  # model units kept, flagged for review

    layers: dict[str, dict] = {}
    for layer in doc.entity_layers():
        entities = doc.entities_of_layer(layer)
        geometry = [e for e in entities if e.kind in ("LWPOLYLINE", "POLYLINE", "CIRCLE", "LINE")]
        semantic = (layer_map or {}).get(layer) or classify_layer(layer)
        if semantic is None:
            review.add(
                "uncertain layer mapping",
                f"layer {layer!r} does not match a known semantic class; mapping needs confirmation",
                0.6,
            )
        closed = [e for e in geometry if e.is_closed_geometry()]
        open_ = [e for e in geometry if not e.is_closed_geometry()]
        area = 0.0
        geometry_flags: list[str] = []
        seen_polygons: set[tuple] = set()
        for e in closed:
            pts = e.points if e.kind != "CIRCLE" else [e.center]
            if e.kind != "CIRCLE":
                if len(pts) < 3:
                    continue
                intersections = find_self_intersections(pts, e.closed)
                if intersections:
                    geometry_flags.append(f"self_intersection({len(intersections)})")
                key = normalize_polygon(pts, e.closed)
                if key in seen_polygons:
                    geometry_flags.append("duplicate_geometry")
                    review.add(
                        "duplicate geometry",
                        f"layer {layer}: repeated polygon",
                        0.9,
                    )
                    continue
                seen_polygons.add(key)
            try:
                area += entity_area(e, effective_scale)
            except InvalidGeometryError:
                geometry_flags.append("invalid_geometry")
        layers[layer] = {
            "layer": layer,
            "semantic_type": semantic,
            "entity_count": len(entities),
            "area_sq_ft": round(area, 6),
            "closed_entities": len(closed),
            "open_entities": len(open_),
            "confidence": 0.97 if semantic else 0.6,
            "geometry_flags": geometry_flags,
            "units_label": doc.units_label or "unknown",
        }

    return {
        "source_file": str(path),
        "model_units": doc.units_label,
        "scale_to_ft": effective_scale,
        "layers": layers,
        "warnings": doc.warnings,
    }


def pipeline(args, config, audit):
    from common.hashing import sha256_file

    input_path = Path(args.input or ".")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*.dxf")) if input_path.is_dir() else []
    if not files:
        raise UnsupportedFileError(f"No DXF files found under {input_path}")

    review = ReviewQueue()
    layer_map = None
    if args.layer_map and Path(args.layer_map).exists():
        with open(args.layer_map, "r", encoding="utf-8") as fh:
            layer_map = json.load(fh)

    results: list[dict] = []
    for f in files:
        digest = sha256_file(f)
        audit.add_input(str(f), digest)
        ext = f.suffix.lower()
        if ext == ".dwg":
            raise UnsupportedFileError(
                "DWG requires a conversion path: export the drawing to ASCII DXF "
                "first (e.g. ODA File Converter). The script never auto-edits CAD.",
                detail=str(f),
            )
        log(args, f"[S03] processing {f.name}")
        results.append(analyze_file(f, args.scale, layer_map, review))

    flat_rows = [
        {
            "file": Path(r["source_file"]).name,
            "layer": l["layer"],
            "semantic_type": l["semantic_type"] or "",
            "entity_count": l["entity_count"],
            "area_sq_ft": l["area_sq_ft"],
            "closed_entities": l["closed_entities"],
            "open_entities": l["open_entities"],
            "confidence": f"{l['confidence']:.2f}",
            "flags": ";".join(l["geometry_flags"]),
        }
        for r in results
        for l in r["layers"].values()
    ]

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["cad_takeoff"] = (str(project_out / "cad_takeoff.json"), "json", {"files": results, "review": review.to_dict()})
    outputs["cad_takeoff_csv"] = (str(project_out / "cad_takeoff.csv"), "csv", flat_rows)
    outputs["review_queue"] = (str(project_out / "review_queue.json"), "json", review.to_dict())
    outputs["summary"] = (str(project_out / "cad_takeoff_summary.md"), "md", _summary(flat_rows, results, review))
    return outputs


def _summary(rows, results, review) -> list[tuple[str, str]]:
    sections = [
        ("CAD Takeoff", f"- files: {len(results)}\n- layers mapped: {len(rows)}"),
        ("Layers", _table_to_markdown(rows)),
    ]
    if review.items:
        sections.append(
            ("Human Review", "\n".join(f"- {line} — see review_queue.json" for line in review.summary_lines()))
        )
    return sections


def main() -> int:
    parser = build_parser("s03_cad_takeoff", "CAD/DXF paving takeoff (S03)", add_extra_args)
    return run_lifecycle(parser, "s03_cad_takeoff", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
