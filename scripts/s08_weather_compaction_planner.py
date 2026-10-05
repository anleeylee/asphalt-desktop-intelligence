#!/usr/bin/env python3
"""S08 — Asphalt Weather & Thermal Compaction Planner.

Model-based planning estimate of the HMA cooling / compaction window.

Model: ADI-THM-v1.0 — lumped-lift (Newton) cooling of a single lift.
  - volumetric heat capacity rho*c: 145 lb/ft3 x 0.23 BTU/lb-F
  - surface heat-transfer coefficient h [BTU/hr-ft2-F] = (5.7 + 3.8*v[m/s]) x 0.1761
    (ASHRAE exterior-surface correlation; v from wind speed)
  - dT/dt = -h/(rho*c*L) * (T - T_air) + q_solar/(rho*c*L)
  - closed form: T(t) = T_air + q_solar/h + (T0 - T_air - q_solar/h) * exp(-t/tau)

Assumptions/limitations are stored with every run. The tool never says
"approved to pave"; supplier/agency/project-specific thresholds override
planning defaults.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.config import get as cfg_get  # noqa: E402
from common.errors import MissingSourceError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402

MODEL_VERSION = "ADI-THM-v1.0"
MODEL_DESCRIPTION = (
    "Lumped-lift (Newton) cooling of a single HMA lift; top-surface convection only; "
    "solar gain optional. Planning estimate, not engineering design."
)

RHO_C_PCF_BTU = 145.0 * 0.23  # BTU/ft3-F


def add_extra_args(parser):
    parser.add_argument("--location", help="project location (label, e.g. zip/city)")
    parser.add_argument("--date", help="paving date YYYY-MM-DD")
    parser.add_argument("--air-temp", dest="air_temp", type=float, help="air temperature (F); required unless --weather-json is given")
    parser.add_argument("--wind", type=float, default=5.0, help="wind speed (mph)")
    parser.add_argument("--surface-temp", dest="surface_temp", type=float, help="surface/base temperature (F)")
    parser.add_argument("--lift-in", dest="lift_in", type=float, default=3.0, help="lift thickness (in)")
    parser.add_argument("--mix", default="HMA", help="mix type label")
    parser.add_argument("--delivery-temp", dest="delivery_temp", type=float, default=300.0, help="placement/delivery temperature (F)")
    parser.add_argument("--start-roll", dest="start_roll", type=float, default=220.0, help="start-rolling temperature (F)")
    parser.add_argument("--stop-roll", dest="stop_roll", type=float, default=175.0, help="stop-rolling temperature (F)")
    parser.add_argument("--solar", type=float, default=0.0, help="solar irradiance (W/m2), 0 = none")
    parser.add_argument("--weather-json", help="weather snapshot JSON (alternative to manual flags)")


def solve_window(
    air_temp: float,
    wind_mph: float,
    surface_temp: float | None,
    lift_in: float,
    delivery_temp: float,
    start_roll: float,
    stop_roll: float,
    solar_wm2: float,
) -> dict:
    v_ms = wind_mph * 0.44704
    h = (5.7 + 3.8 * v_ms) * 0.17611  # BTU/hr-ft2-F
    q_solar = solar_wm2 * 0.3170  # W/m2 -> BTU/hr-ft2
    lift_ft = lift_in / 12.0
    tau_hr = RHO_C_PCF_BTU * lift_ft / h
    ambient = surface_temp if surface_temp is not None else air_temp
    # effective ambient used for cooling (top convection dominates)
    t_amb = air_temp

    def time_to(temp: float) -> float | None:
        if temp >= delivery_temp:
            return 0.0
        if temp <= t_amb:
            return None
        numerator = delivery_temp - t_amb - q_solar / h
        denominator = temp - t_amb - q_solar / h
        if denominator <= 0:
            return None
        if numerator <= 0:
            return 0.0
        minutes = -tau_hr * math.log(denominator / numerator) * 60.0
        return max(0.0, minutes)

    t_start = time_to(start_roll)
    t_stop = time_to(stop_roll)
    window = (t_stop - t_start) if (t_start is not None and t_stop is not None) else None

    # cooling curve: every 10 minutes from 0 to stop+30 (bounded)
    curve: list[dict] = []
    horizon = (t_stop + 30.0) if t_stop is not None else 180.0
    t = 0.0
    while t <= horizon + 1e-9:
        temp = t_amb + q_solar / h + (delivery_temp - t_amb - q_solar / h) * math.exp(-(t / 60.0) / tau_hr)
        curve.append({"minutes": round(t, 1), "temp_f": round(temp, 1)})
        t += 10.0
        if len(curve) > 500:
            break

    return {
        "model_version": MODEL_VERSION,
        "model_description": MODEL_DESCRIPTION,
        "inputs": {
            "air_temp_f": air_temp,
            "wind_mph": wind_mph,
            "surface_temp_f": surface_temp,
            "lift_in": lift_in,
            "mix": None,
            "delivery_temp_f": delivery_temp,
            "start_roll_temp_f": start_roll,
            "stop_roll_temp_f": stop_roll,
            "solar_wm2": solar_wm2,
        },
        "parameters": {
            "h_btu_hr_ft2_f": round(h, 4),
            "rho_c_btu_ft3_f": RHO_C_PCF_BTU,
            "tau_hr": round(tau_hr, 4),
        },
        "estimated_window_minutes": round(window, 1) if window is not None else None,
        "start_rolling_time": f"{t_start:.0f} min after placement" if t_start is not None else None,
        "stop_rolling_time": f"{t_stop:.0f} min after placement" if t_stop is not None else None,
        "temperature_curve": curve,
        "assumptions": [
            "top-surface convection only; bottom heat exchange with base/surface is neglected",
            "h from ASHRAE exterior-surface correlation (5.7 + 3.8*v[m/s]) in BTU/hr-ft2-F",
            "uniform mat temperature (lumped capacitance); thin single lift",
            "placement temperature taken as delivery temperature",
            "planning estimate only — not engineering design, and never an approval to pave",
        ],
        "limitations": [
            "thick lifts (>4 in) lose lumped accuracy; use a finite-element model for design",
            "cold base/surface slows top-side cooling assumptions — actual behavior depends on base temperature",
            "sky emissivity / night cooling not modeled",
            "mix-specific volumetric heat capacity may differ from the 0.23 BTU/lb-F default",
        ],
        "risk_factors": [],
        "status": "PLANNING ESTIMATE",
    }


def add_risks(result: dict) -> None:
    inputs = result["inputs"]
    if inputs["air_temp_f"] <= 50:
        result["risk_factors"].append(
            {"label": "cold-weather placement risk", "detail": "air temperature at/below ~50F; industry practice generally stops HMA placement near 50F air", "label_kind": "OBSERVED"}
        )
    if result["estimated_window_minutes"] is not None and result["estimated_window_minutes"] < 30:
        result["risk_factors"].append(
            {"label": "short compaction window", "detail": "estimated window under 30 minutes; coordinate rollers", "label_kind": "POSSIBLE"}
        )
    if inputs["wind_mph"] > 15:
        result["risk_factors"].append(
            {"label": "high wind cooling", "detail": "wind above ~15 mph materially shortens the window", "label_kind": "POSSIBLE"}
        )


def pipeline(args, config, audit):
    audit.set_engine(MODEL_VERSION)

    if args.weather_json and Path(args.weather_json).exists():
        with open(args.weather_json, "r", encoding="utf-8") as fh:
            weather = json.load(fh)
        air_temp = float(weather.get("air_temp_f", args.air_temp))
        wind = float(weather.get("wind_mph", args.wind))
        surface = float(weather["surface_temp_f"]) if weather.get("surface_temp_f") is not None else args.surface_temp
        lift = float(weather.get("lift_in", args.lift_in))
        delivery = float(weather.get("delivery_temp_f", args.delivery_temp))
        start_roll = float(weather.get("start_roll_temp_f", args.start_roll))
        stop_roll = float(weather.get("stop_roll_temp_f", args.stop_roll))
        solar = float(weather.get("solar_wm2", args.solar))
    elif args.air_temp is not None:
        air_temp, wind, surface, lift, delivery = args.air_temp, args.wind, args.surface_temp, args.lift_in, args.delivery_temp
        start_roll, stop_roll, solar = args.start_roll, args.stop_roll, args.solar
    else:
        raise MissingSourceError("--air-temp is required (or pass --weather-json with air_temp_f).")

    result = solve_window(air_temp, wind, surface, lift, delivery, start_roll, stop_roll, solar)
    result["inputs"]["mix"] = args.mix
    result["project"] = {
        "location": args.location,
        "date": args.date,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }
    add_risks(result)

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["thermal_run"] = (str(project_out / "thermal_run.json"), "json", result)
    outputs["summary"] = (str(project_out / "thermal_summary.md"), "md", _summary(result))
    return outputs


def _summary(result: dict) -> list[tuple[str, str]]:
    inputs = result["inputs"]
    rows = [
        {"metric": "estimated window", "value": f"{result['estimated_window_minutes']} min" if result["estimated_window_minutes"] is not None else "n/a"},
        {"metric": "start rolling", "value": result["start_rolling_time"] or "n/a"},
        {"metric": "stop rolling", "value": result["stop_rolling_time"] or "n/a"},
        {"metric": "model", "value": result["model_version"]},
        {"metric": "air / wind / solar", "value": f"{inputs['air_temp_f']} F / {inputs['wind_mph']} mph / {inputs['solar_wm2']} W/m2"},
        {"metric": "lift / delivery / roll range", "value": f"{inputs['lift_in']} in / {inputs['delivery_temp_f']} F / {inputs['start_roll_temp_f']}-{inputs['stop_roll_temp_f']} F"},
    ]
    sections = [
        ("Thermal Compaction Window", f"- model: {MODEL_VERSION}\n- status: {result['status']} (planning only, not 'approved to pave')"),
        ("Result", _table_to_markdown(rows)),
    ]
    if result["risk_factors"]:
        sections.append(
            ("Risk Factors",
             "\n".join(f"- [{r['label_kind']}] {r['label']}: {r['detail']}" for r in result["risk_factors"]))
        )
    if result["assumptions"]:
        sections.append(("Assumptions", "\n".join(f"- {a}" for a in result["assumptions"])))
    if result["limitations"]:
        sections.append(("Limitations", "\n".join(f"- {l}" for l in result["limitations"])))
    return sections


def main() -> int:
    parser = build_parser("s08_weather_compaction_planner", "Asphalt weather & thermal compaction planner (S08)", add_extra_args)
    return run_lifecycle(parser, "s08_weather_compaction_planner", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
