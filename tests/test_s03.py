"""S03 — CAD/DXF takeoff tests (acceptance: known areas < 0.1% error)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s03_cad_takeoff as s03
from common.dxf import parse_dxf
from common.validation import within_percent


class TestDXFParser:
    def test_rect_5000(self, fixtures: Path):
        doc = parse_dxf((fixtures / "dxf" / "rect_5000.dxf").read_text(encoding="utf-8"))
        assert doc.units_label == "feet"
        layers = doc.entity_layers()
        assert "PAV-ASPH" in layers
        polys = [e for e in doc.entities_of_layer("PAV-ASPH") if e.kind == "LWPOLYLINE"]
        closed = [e for e in polys if e.closed]
        open_ = [e for e in polys if not e.closed]
        assert len(closed) == 2  # original + duplicate
        assert len(open_) == 1

    def test_circle_area(self, fixtures: Path):
        doc = parse_dxf((fixtures / "dxf" / "rect_5000.dxf").read_text(encoding="utf-8"))
        circles = [e for e in doc.entities if e.kind == "CIRCLE"]
        assert len(circles) == 1
        from common.dxf import entity_area

        assert within_percent(entity_area(circles[0], 1.0), 3.141592653589793 * 100, 0.001)

    def test_lshape_area(self, fixtures: Path):
        doc = parse_dxf((fixtures / "dxf" / "mill_lshape_2700.dxf").read_text(encoding="utf-8"))
        poly = [e for e in doc.entities if e.kind == "LWPOLYLINE"][0]
        from common.dxf import entity_area

        assert within_percent(entity_area(poly, 1.0), 2700.0, 0.001)

    def test_unknown_units(self, fixtures: Path):
        doc = parse_dxf((fixtures / "dxf" / "unitless_unknown.dxf").read_text(encoding="utf-8"))
        assert doc.units is None


class TestS03:
    def test_golden_areas(self, empty_project, fixtures: Path):
        rc = run_script(s03, ["--project", str(empty_project), "--input", str(fixtures / "dxf")])
        assert rc == 0
        data = json.loads((empty_project / "output" / "cad_takeoff.json").read_text(encoding="utf-8"))
        layers = {l["layer"]: l for f in data["files"] for l in f["layers"].values()}
        # rect 5000 + circle 314.159 = 5314.159; duplicate polygon excluded
        assert within_percent(layers["PAV-ASPH"]["area_sq_ft"], 5314.159, 0.1)
        assert layers["PAV-ASPH"]["semantic_type"] == "HMA"
        assert layers["PAV-ASPH"]["open_entities"] == 1
        assert "duplicate_geometry" in layers["PAV-ASPH"]["geometry_flags"]
        assert within_percent(layers["BASE-AGG"]["area_sq_ft"], 6000.0, 0.1)
        assert within_percent(layers["MILL-AREA"]["area_sq_ft"], 2700.0, 0.1)

    def test_unknown_units_to_review(self, empty_project, fixtures: Path):
        run_script(s03, ["--project", str(empty_project), "--input", str(fixtures / "dxf" / "unitless_unknown.dxf")])
        review = json.loads((empty_project / "output" / "review_queue.json").read_text(encoding="utf-8"))
        assert any("units unknown" in line for line in review["summary"])

    def test_dwg_rejected(self, empty_project, tmp_path):
        dwg = tmp_path / "bad.dwg"
        dwg.write_text("binary-ish")
        rc = run_script(s03, ["--project", str(empty_project), "--input", str(dwg)])
        assert rc != 0
