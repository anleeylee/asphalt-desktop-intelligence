"""S10 — estimate & audit report builder tests."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s10_estimate_report_builder as s10


def seed_project(project: Path) -> None:
    (project / "output").mkdir(parents=True, exist_ok=True)
    (project / "project.json").write_text(
        json.dumps(
            {
                "project_id": "P-1",
                "name": "Oak St",
                "documents": [{"doc_id": "doc-1", "path": "plans/civil.pdf", "sha256": "a" * 64, "category": "plans"}],
            }
        ),
        encoding="utf-8",
    )
    (project / "output" / "takeoff.json").write_text(
        json.dumps(
            {
                "takeoff": [
                    {
                        "area_id": "A-001",
                        "sheet": "C3.1",
                        "surface": "HMA",
                        "quantity": 8400.0,
                        "unit": "sq_ft",
                        "thickness": 3.0,
                        "method": "vector_geometry",
                        "confidence": 0.99,
                        "state": "VALIDATED",
                    }
                ],
                "conflicts": [],
            }
        ),
        encoding="utf-8",
    )


class TestS10:
    def test_report_generated(self, empty_project):
        seed_project(empty_project)
        rc = run_script(s10, ["--project", str(empty_project), "--format", "json"])
        assert rc == 0
        report = json.loads((empty_project / "output" / "estimate_report.json").read_text(encoding="utf-8"))
        assert "takeoff" in report["sections"]
        assert report["sections"]["source_register"]
        mq = report["sections"]["material_quantities"]
        assert mq and mq[0]["engine_version"].endswith("mirror")
        assert report["sections"]["calculation_register"]

    def test_engine_numbers_deterministic(self, empty_project):
        seed_project(empty_project)
        run_script(s10, ["--project", str(empty_project)])
        first = json.loads((empty_project / "output" / "estimate_report.json").read_text(encoding="utf-8"))
        run_script(s10, ["--project", str(empty_project)])
        second = json.loads((empty_project / "output" / "estimate_report.json").read_text(encoding="utf-8"))
        a = first["sections"]["material_quantities"]
        b = second["sections"]["material_quantities"]
        assert a == b
        # deterministic engine math: 8400 SF @ 3 in, 145 pcf, 5% -> net/order
        assert a[0]["net_tons"] == 8400 * 0.25 * 145 / 2000
        assert a[0]["order_tons"] == round(a[0]["net_tons"] * 1.05, 6)

    def test_missing_data_not_invented(self, empty_project):
        seed_project(empty_project)
        run_script(s10, ["--project", str(empty_project)])
        report = json.loads((empty_project / "output" / "estimate_report.json").read_text(encoding="utf-8"))
        statuses = {f["status"] for f in report["flags"]}
        assert "MISSING DATA" in statuses  # no supplier evidence present
        assert report["sections"]["supplier_evidence"] == []

    def test_markdown_output(self, empty_project):
        seed_project(empty_project)
        rc = run_script(s10, ["--project", str(empty_project), "--format", "md"])
        assert rc == 0
        md = (empty_project / "output" / "estimate_report.md").read_text(encoding="utf-8")
        for section in ("Project Summary", "Takeoff", "Material Quantities", "Source Register", "Calculation Register"):
            assert section in md
