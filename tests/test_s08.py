"""S08 — weather / thermal compaction planner tests."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s08_weather_compaction_planner as s08
from common.validation import within_percent


def run_thermal(project: Path, **kwargs) -> dict:
    argv = ["--project", str(project)]
    for k, v in kwargs.items():
        if isinstance(v, bool) and v:
            argv.append(f"--{k.replace('_', '-')}")
        else:
            argv.extend([f"--{k.replace('_', '-')}", str(v)])
    rc = run_script(s08, argv)
    assert rc == 0
    with open(project / "output" / "thermal_run.json", encoding="utf-8") as fh:
        return json.load(fh)


class TestS08:
    def test_wind_shortens_window(self, empty_project):
        low = run_thermal(empty_project, air_temp=60, wind=5)
        high = run_thermal(empty_project, air_temp=60, wind=20)
        assert high["estimated_window_minutes"] < low["estimated_window_minutes"]

    def test_thinner_lift_cools_faster(self, empty_project):
        thin = run_thermal(empty_project, air_temp=60, wind=5, lift_in=1.5)
        thick = run_thermal(empty_project, air_temp=60, wind=5, lift_in=4)
        assert thin["estimated_window_minutes"] < thick["estimated_window_minutes"]

    def test_higher_delivery_temp_lengthens_window(self, empty_project):
        # In this lumped model a hotter delivery shifts the whole cooling curve
        # later: stop-rolling is reached later (and start-rolling too).
        hot = run_thermal(empty_project, air_temp=60, wind=5, delivery_temp=310)
        cooler = run_thermal(empty_project, air_temp=60, wind=5, delivery_temp=285)
        import re as _re

        stop_hot = float(_re.search(r"(\d+)", hot["stop_rolling_time"]).group(1))
        stop_cool = float(_re.search(r"(\d+)", cooler["stop_rolling_time"]).group(1))
        assert stop_hot > stop_cool

    def test_model_version_and_inputs_recorded(self, empty_project):
        result = run_thermal(empty_project, air_temp=60, wind=5)
        assert result["model_version"] == "ADI-THM-v1.0"
        assert result["inputs"]["air_temp_f"] == 60
        assert result["temperature_curve"]
        assert result["assumptions"] and result["limitations"]

    def test_cold_weather_risk(self, empty_project):
        result = run_thermal(empty_project, air_temp=45, wind=5)
        assert any("cold-weather" in r["label"] for r in result["risk_factors"])

    def test_no_approved_language(self, empty_project):
        result = run_thermal(empty_project, air_temp=70, wind=5)
        blob = json.dumps(result)
        assert "approved to pave" not in blob.lower()
        assert result["status"] == "PLANNING ESTIMATE"

    def test_weather_json_input(self, empty_project, fixtures: Path):
        rc = run_script(
            s08,
            ["--project", str(empty_project), "--weather-json", str(fixtures / "weather" / "weather_snapshot.json")],
        )
        assert rc == 0
        result = json.loads((empty_project / "output" / "thermal_run.json").read_text(encoding="utf-8"))
        assert result["inputs"]["wind_mph"] == 8
        assert result["inputs"]["solar_wm2"] == 250
