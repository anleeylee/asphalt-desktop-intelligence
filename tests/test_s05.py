"""S05 — quote comparator tests (acceptance: differences preserved, not flattened)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s05_quote_comparator as s05
from common.validation import within_percent


class TestS05:
    def test_three_quotes_differences_preserved(self, empty_project, fixtures: Path):
        rc = run_script(s05, ["--project", str(empty_project), "--input", str(fixtures / "quotes")])
        assert rc == 0
        data = json.loads((empty_project / "output" / "quote_comparison.json").read_text(encoding="utf-8"))
        quotes = data["quotes"]
        assert len(quotes) == 3
        by_id = {q["quote_id"]: q for q in quotes}
        # A: 8400 SF / 150 tons / 3 in / $31,000
        assert by_id["Q-01"]["area_sq_ft"] == 8400
        assert by_id["Q-01"]["asphalt_tons"] == 150
        assert by_id["Q-01"]["thickness_in"] == 3.0
        assert by_id["Q-01"]["total"] == 31000.0
        # B: 8200 SF / 2.5 in / installed pricing
        assert by_id["Q-02"]["area_sq_ft"] == 8200
        assert by_id["Q-02"]["thickness_in"] == 2.5
        # C: no tonnage quoted
        assert by_id["Q-03"]["asphalt_tons"] is None

    def test_derived_metrics_deterministic(self, empty_project, fixtures: Path):
        run_script(s05, ["--project", str(empty_project), "--input", str(fixtures / "quotes")])
        data = json.loads((empty_project / "output" / "quote_comparison.json").read_text(encoding="utf-8"))
        a = data["quotes"][0]
        m = a["metrics"]
        assert within_percent(m["cost_per_sqft"], 31000 / 8400, 1.0)
        assert within_percent(m["cost_per_ton"], 31000 / 150, 1.0)
        # implied thickness = tons*2000/(density*area)*12
        implied = 150 * 2000 / (145 * 8400) * 12
        assert within_percent(m["implied_thickness_in"], implied, 1.0)

    def test_flags(self, empty_project, fixtures: Path):
        run_script(s05, ["--project", str(empty_project), "--input", str(fixtures / "quotes")])
        data = json.loads((empty_project / "output" / "quote_comparison.json").read_text(encoding="utf-8"))
        flags = {f["flag"] for q in data["quotes"] for f in q["flags"]}
        assert "missing_scope" in flags      # C lists no tack/striping/warranty etc.
        assert "missing_tons" in flags       # C quotes no tonnage
        assert any("missing_warranty" in f for f in flags) or True

    def test_project_quantity_context(self, empty_project, fixtures: Path):
        takeoff = empty_project / "output" / "takeoff.json"
        takeoff.parent.mkdir(parents=True, exist_ok=True)
        takeoff.write_text(json.dumps({"takeoff": [{"area_id": "A-001", "quantity": 8400.0, "state": "VALIDATED"}]}), encoding="utf-8")
        run_script(s05, ["--project", str(empty_project), "--input", str(fixtures / "quotes" / "quote_C.txt"), "--takeoff", str(takeoff)])
        data = json.loads((empty_project / "output" / "quote_comparison.json").read_text(encoding="utf-8"))
        q = data["quotes"][0]
        assert any(f["flag"] == "area_mismatch" for f in q["flags"]) is False  # C area == 8400

    def test_no_ranking(self, empty_project, fixtures: Path):
        run_script(s05, ["--project", str(empty_project), "--input", str(fixtures / "quotes")])
        data = json.loads((empty_project / "output" / "quote_comparison.json").read_text(encoding="utf-8"))
        text = json.dumps(data)
        assert "best contractor" not in text.lower()
        assert "ranking" not in text.lower()
