"""S07 — supplier quote normalizer tests."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s07_supplier_quote_normalizer as s07


class TestS07:
    def test_multi_mix_kept_separate(self, empty_project, fixtures: Path):
        rc = run_script(s07, ["--project", str(empty_project), "--input", str(fixtures / "suppliers" / "supplier_city_rock.txt")])
        assert rc == 0
        data = json.loads((empty_project / "output" / "supplier_prices.json").read_text(encoding="utf-8"))
        items = data["prices"]
        mixes = {i["mix"] for i in items if i["mix"]}
        assert "PG 64-22" in mixes and "PG 76-22" in mixes

    def test_delivery_not_merged_into_material(self, empty_project, fixtures: Path):
        run_script(s07, ["--project", str(empty_project), "--input", str(fixtures / "suppliers" / "supplier_city_rock.txt")])
        data = json.loads((empty_project / "output" / "supplier_prices.json").read_text(encoding="utf-8"))
        items = data["prices"]
        # first two HMA items are 'delivered'; aggregate at plant is 'material_only'
        bases = {i["price_basis"] for i in items}
        assert "delivered" in bases and "material_only" in bases
        hma_delivered = [i for i in items if i["mix"] == "PG 64-22" and i["price_basis"] == "delivered"]
        assert hma_delivered and hma_delivered[0]["unit_price"] == 52.0
        agg_at_plant = [i for i in items if i["material"] == "AGG_BASE" and i["price_basis"] == "material_only"]
        assert agg_at_plant and agg_at_plant[0]["unit_price"] == 18.5

    def test_expiration_preserved(self, empty_project, fixtures: Path):
        run_script(s07, ["--project", str(empty_project), "--input", str(fixtures / "suppliers" / "supplier_city_rock.txt")])
        data = json.loads((empty_project / "output" / "supplier_prices.json").read_text(encoding="utf-8"))
        for item in data["prices"]:
            assert item["expiration_date"] == "11/15/2026"

    def test_surcharge_and_minimum_load(self, empty_project, fixtures: Path):
        run_script(s07, ["--project", str(empty_project), "--input", str(fixtures / "suppliers" / "supplier_city_rock.txt")])
        data = json.loads((empty_project / "output" / "supplier_prices.json").read_text(encoding="utf-8"))
        hma = [i for i in data["prices"] if i["material"] == "HMA"]
        assert all(i["minimum_load"] == 20.0 for i in hma)
        assert any(i["surcharge"] == "fuel" for i in hma)
