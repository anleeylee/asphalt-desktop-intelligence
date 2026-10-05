"""S09 — field photo analyzer tests."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s09_field_photo_analyzer as s09


class TestS09:
    def test_clear_photo_routes_to_review(self, empty_project, photo_fixtures_ready: Path):
        rc = run_script(s09, ["--project", str(empty_project), "--input", str(photo_fixtures_ready)])
        assert rc == 0
        data = json.loads((empty_project / "output" / "photo_analysis.json").read_text(encoding="utf-8"))
        assert data["screening_only"] is True
        photos = data["photos"]
        assert len(photos) == 3
        for p in photos:
            assert p["human_review_required"] is True
            assert p["severity"] == "screening_only"

    def test_dark_photo_routed_with_quality_note(self, empty_project, photo_fixtures_ready: Path):
        run_script(s09, ["--project", str(empty_project), "--input", str(photo_fixtures_ready)])
        data = json.loads((empty_project / "output" / "photo_analysis.json").read_text(encoding="utf-8"))
        dark = [p for p in data["photos"] if "dark" in Path(p["source_file"]).name][0]
        assert dark["quality"]["brightness_mean"] < 40
        assert any("poor image quality" in n for n in dark["notes"])

    def test_no_engineering_diagnosis(self, empty_project, photo_fixtures_ready: Path):
        run_script(s09, ["--project", str(empty_project), "--input", str(photo_fixtures_ready)])
        data = json.loads((empty_project / "output" / "photo_analysis.json").read_text(encoding="utf-8"))
        blob = json.dumps(data).lower()
        assert "cbr" not in blob
        assert "structural capacity" not in blob
        assert "remaining life" not in blob
        assert "repair depth" not in blob

    def test_reference_measurement_approximate(self, empty_project, photo_fixtures_ready: Path):
        rc = run_script(
            s09,
            [
                "--project", str(empty_project),
                "--input", str(photo_fixtures_ready),
                "--reference-dim", "12",
                "--reference-label", "traffic cone",
            ],
        )
        assert rc == 0
        data = json.loads((empty_project / "output" / "photo_analysis.json").read_text(encoding="utf-8"))
        # without a vision backend, no measurement claims are produced
        for p in data["photos"]:
            assert all(m.get("status") == "APPROXIMATE" for m in p["measurements"])
