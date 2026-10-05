"""S04 — specification checker tests."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s04_specification_checker as s04


class TestS04:
    def test_extract_known_fields(self, empty_project, fixtures: Path):
        rc = run_script(s04, ["--project", str(empty_project), "--input", str(fixtures / "specs")])
        assert rc == 0
        data = json.loads((empty_project / "output" / "spec_requirements.json").read_text(encoding="utf-8"))
        reqs = data["requirements"]
        by_field = {}
        for r in reqs:
            by_field.setdefault(r["field"], []).append(r)
        assert any(round(float(r["value"]), 1) == 3.0 for r in by_field["thickness"])
        assert any("PG 64-22" in str(r["value"]) for r in by_field["pg"])
        assert any(r["field"] == "density" and round(float(r["value"])) == 92 for r in reqs)
        assert any(r["field"] == "temperature" for r in reqs)
        # page evidence present
        for r in reqs:
            assert r["source_file"] and r["source_page"]

    def test_classification(self, empty_project, fixtures: Path):
        run_script(s04, ["--project", str(empty_project), "--input", str(fixtures / "specs")])
        data = json.loads((empty_project / "output" / "spec_requirements.json").read_text(encoding="utf-8"))
        classifications = {r["classification"] for r in data["requirements"]}
        assert "REQUIRED" in classifications
        assert "OPTIONAL" in classifications or "EXAMPLE" in classifications

    def test_addendum_conflict_detected(self, empty_project, fixtures: Path):
        run_script(s04, ["--project", str(empty_project), "--input", str(fixtures / "specs")])
        conflicts = json.loads((empty_project / "output" / "conflicts.json").read_text(encoding="utf-8"))
        spec_vs_add = [c for c in conflicts["conflicts"] if c["mode"] == "SPEC vs ADDENDUM"]
        assert len(spec_vs_add) >= 1
        assert spec_vs_add[0]["status"] == "REVIEW REQUIRED"

    def test_plan_vs_spec(self, empty_project, fixtures: Path):
        takeoff = empty_project / "output" / "takeoff.json"
        takeoff.parent.mkdir(parents=True, exist_ok=True)
        # plan says 3.5 in, spec_base says 3 in -> conflict
        takeoff.write_text(json.dumps({"takeoff": [{"area_id": "A-001", "quantity": 5000, "thickness": 3.5, "state": "VALIDATED"}]}), encoding="utf-8")
        run_script(s04, ["--project", str(empty_project), "--input", str(fixtures / "specs" / "spec_base.txt"), "--takeoff", str(takeoff)])
        conflicts = json.loads((empty_project / "output" / "conflicts.json").read_text(encoding="utf-8"))
        modes = {c["mode"] for c in conflicts["conflicts"]}
        assert "PLAN vs SPEC" in modes
