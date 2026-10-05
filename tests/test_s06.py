"""S06 — delivery ticket reconciliation tests.

Acceptance: 100 tickets -> correct total within source precision; duplicates
caught; 2 intentionally damaged tickets moved to review; variance matches
reference.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from conftest import run_script
from scripts import s06_delivery_ticket_reconcile as s06


def make_100_ticket_csv(path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["plant", "supplier", "truck_id", "load_id", "date", "time", "mix", "net_tons", "gross", "tare"])
        for i in range(1, 101):
            writer.writerow(
                ["Austin Plant", "City Rock", f"TR-{i % 5}", f"LD-{1000 + i}", "10/03/2026", f"{6 + i % 12}:15", "PG 64-22", "20.0", "45.0", "25.0"]
            )
        # duplicate ticket id (same load_id as first)
        writer.writerow(["Austin Plant", "City Rock", "TR-1", "LD-1001", "10/03/2026", "07:30", "PG 64-22", "20.0", "45.0", "25.0"])
        # two damaged tickets
        writer.writerow(["Austin Plant", "City Rock", "TR-9", "LD-9999", "10/03/2026", "16:00", "PG 64-22", "", "45.0", "25.0"])
        writer.writerow(["Austin Plant", "City Rock", "TR-9", "LD-9998", "10/03/2026", "16:30", "PG 64-22", "22.5", "45.0", "25.0"])


class TestS06:
    def test_100_tickets_total(self, empty_project, tmp_path):
        csv_path = tmp_path / "tickets_100.csv"
        make_100_ticket_csv(csv_path)
        rc = run_script(
            s06,
            ["--project", str(empty_project), "--input", str(csv_path), "--estimate", "2000"],
        )
        assert rc == 0
        data = json.loads((empty_project / "output" / "delivery_reconciliation.json").read_text(encoding="utf-8"))
        # clean rows: 100 original tickets x 20.0 = 2000.0; duplicate (E006) and
        # the two damaged rows (E004/E010) are excluded from the clean total
        assert data["delivered_total_tons"] == 2000.0
        assert data["load_count"] == 103
        assert data["variance_tons"] == 0.0
        assert data["variance_percent"] == 0.0

    def test_duplicates_caught(self, empty_project, tmp_path):
        csv_path = tmp_path / "tickets_100.csv"
        make_100_ticket_csv(csv_path)
        run_script(s06, ["--project", str(empty_project), "--input", str(csv_path), "--estimate", "2000"])
        data = json.loads((empty_project / "output" / "delivery_reconciliation.json").read_text(encoding="utf-8"))
        codes = {e["code"] for e in data["exceptions"]}
        assert "E006" in codes  # duplicate ticket id

    def test_damaged_tickets_to_review(self, empty_project, tmp_path):
        csv_path = tmp_path / "tickets_100.csv"
        make_100_ticket_csv(csv_path)
        run_script(s06, ["--project", str(empty_project), "--input", str(csv_path), "--estimate", "2000"])
        data = json.loads((empty_project / "output" / "delivery_reconciliation.json").read_text(encoding="utf-8"))
        codes = {e["code"] for e in data["exceptions"]}
        assert "E004" in codes  # missing net weight / gross-tare mismatch
        assert "E010" in codes  # gross - tare != net

    def test_variance_matches_reference(self, empty_project, fixtures: Path):
        rc = run_script(
            s06,
            ["--project", str(empty_project), "--input", str(fixtures / "tickets" / "tickets_10.csv"), "--estimate", "198.5"],
        )
        assert rc == 0
        data = json.loads((empty_project / "output" / "delivery_reconciliation.json").read_text(encoding="utf-8"))
        # 10 tickets: 20+20+20+20+20+19.5+20+20+19.9+20 = 199.4
        assert abs(data["delivered_total_tons"] - 199.4) < 1e-9
        assert abs(data["variance_tons"] - 0.9) < 1e-9

    def test_mix_mismatch_flagged(self, empty_project, tmp_path):
        csv_path = tmp_path / "tickets_1.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("plant,supplier,truck_id,load_id,date,time,mix,net_tons,gross,tare\n")
            fh.write("Austin Plant,City Rock,TR-1,LD-1,10/03/2026,07:15,PG 76-22,20.0,45.0,25.0\n")
        run_script(s06, ["--project", str(empty_project), "--input", str(csv_path), "--mix-spec", "PG 64-22"])
        data = json.loads((empty_project / "output" / "delivery_reconciliation.json").read_text(encoding="utf-8"))
        codes = {e["code"] for e in data["exceptions"]}
        assert "E005" in codes
