"""Tests for the shared thin foundation."""

from __future__ import annotations

import json

import pytest

from common import units
from common.ai_adapter import AIAdapter, HeuristicExtractor
from common.asphaltcosts_client import AsphaltCostsClient
from common.config import load_config
from common.file_manifest import FileManifest, classify_file
from common.hashing import sha256_file, stable_id
from common.provenance import EvidenceTracker, SourceRegister
from common.schemas import NORMALIZED, VALIDATED, VERIFIED, ValueEnvelope
from common.validation import (
    close_to,
    validate_envelope,
    validate_takeoff_record,
    within_percent,
)


class TestUnits:
    def test_area_conversions(self):
        assert close_to(units.normalize_area(1, "acre"), 43560.0)
        assert close_to(units.normalize_area(1, "sq_m"), 10.7639104167)
        assert close_to(units.normalize_area(1000, "sf"), 1000.0)

    def test_thickness_and_mass(self):
        assert close_to(units.normalize_thickness(3, "in"), 3.0)
        assert close_to(units.normalize_thickness(1, "ft"), 12.0)
        assert close_to(units.normalize_mass(1, "ton"), 1.0)
        assert close_to(units.normalize_mass(2000, "lb"), 1.0)

    def test_parse_helpers(self):
        assert units.parse_area("32,450 SF") == (32450.0, "sq_ft")
        assert units.parse_thickness('3 in HMA') == (3.0, "in")
        assert units.parse_density("145 lb/ft3") == (145.0, "lb/ft3")
        assert units.parse_mass("18.13 tons") == (18.13, "us_ton")

    def test_ambiguous_unit_raises(self):
        with pytest.raises(Exception):
            units.normalize_area(1, "furlong")


class TestHashing:
    def test_stable_ids(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("same content")
        b.write_text("same content")
        assert sha256_file(a) == sha256_file(b)
        # same physical path + same content -> identical doc id (re-ingest safe)
        assert stable_id("doc", str(a), sha256_file(a)) == stable_id("doc", str(a), sha256_file(a))
        # different path -> different id (revision-per-path semantics)
        assert stable_id("doc", str(a), sha256_file(a)) != stable_id("doc", str(b), sha256_file(b))
        # same path + changed content -> different id (revised file = new version)
        b.write_text("changed content")
        assert stable_id("doc", str(b), sha256_file(b)) != stable_id("doc", str(a), sha256_file(a))


class TestValidation:
    def test_envelope_states(self):
        ok = {
            "value": 84200,
            "unit": "sq_ft",
            "method": "ai_extraction",
            "confidence": 0.92,
            "state": "EXTRACTED",
            "verified": False,
        }
        assert validate_envelope(ok) == []
        bad = dict(ok, state="VERIFIED", verified=False)
        assert validate_envelope(bad)  # verified=False with VERIFIED state -> problem

    def test_verified_requires_verified(self):
        ok = dict(value=1, method="manual", confidence=0.9, state=VERIFIED, verified=True)
        assert validate_envelope(ok) == []

    def test_takeoff_record_schema(self):
        rec = {
            "area_id": "A-001",
            "sheet": "C3.1",
            "surface": "HMA",
            "quantity": 32450,
            "unit": "sq_ft",
            "method": "vector_geometry",
            "confidence": 0.99,
            "state": VALIDATED,
        }
        assert validate_takeoff_record(rec) == []

    def test_within_percent(self):
        assert within_percent(5000, 5000, 0.5)
        assert within_percent(5010, 5000, 0.5)
        assert not within_percent(5040, 5000, 0.5)


class TestProvenance:
    def test_state_machine(self):
        tracker = EvidenceTracker()
        rec = ValueEnvelope(value=1, method="x", confidence=0.5).to_dict()
        tracker.put("k", rec)
        tracker.transition("k", NORMALIZED)
        tracker.transition("k", VALIDATED)
        tracker.transition("k", VERIFIED, verified=True)
        assert tracker.get("k") if hasattr(tracker, "get") else True
        records = tracker.all()
        assert records[0]["state"] == VERIFIED and records[0]["verified"] is True

    def test_source_register(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_text("hello")
        reg = SourceRegister()
        ref = reg.register(str(f), page=3)
        assert ref.page == 3
        assert ref.sha256 == sha256_file(f)


class TestEngineMirror:
    """Golden numbers from the AsphaltCosts site: 1,000 sq ft @ 3 in, 145 pcf,
    5% allowance -> net 18.13 US tons, order 19.03 tons, 1 x 20-ton load."""

    def test_quantity_matches_site_example(self):
        client = AsphaltCostsClient(load_config())
        r = client.calculate_quantity(1000, 3, density_pcf=145, order_allowance=0.05, truck_capacity_tons=20)
        assert close_to(r["net_tons"], 18.125, rel_tol=1e-6)
        assert close_to(r["order_tons"], 19.03125, rel_tol=1e-6)
        assert r["truckloads"] == 1
        assert r["engine_version"].endswith("mirror")
        assert r["steps"]

    def test_metric_equivalent(self):
        client = AsphaltCostsClient(load_config())
        r = client.calculate_quantity(1000, 3)
        assert close_to(r["metric_tons"], r["net_tons"] * 0.90718474, rel_tol=1e-6)

    def test_cost_material_only(self):
        client = AsphaltCostsClient(load_config())
        r = client.calculate_quantity(1000, 3, order_allowance=0.05, price_per_ton=60)
        assert close_to(r["material_cost"], 19.03125 * 60, rel_tol=1e-4)

    def test_invalid_inputs_rejected(self):
        client = AsphaltCostsClient(load_config())
        with pytest.raises(Exception):
            client.calculate_quantity(0, 3)
        with pytest.raises(Exception):
            client.calculate_quantity(1000, 3, order_allowance=1.5)


class TestAIAdapter:
    def test_heuristic_extraction(self):
        ai = AIAdapter(load_config())
        candidates = ai.extract_candidates("The paving area is 32,450 SF at 3 inches thick, PG 64-22.")
        fields = {c["field"] for c in candidates}
        assert "area" in fields and "thickness" in fields
        for c in candidates:
            assert c["state"] == "EXTRACTED" and c["verified"] is False

    def test_material_synonyms(self):
        h = HeuristicExtractor()
        assert h.map_material("MILL & OVERLAY")["value"] == "MILL"
        assert h.map_material("hot mix asphalt")["value"] == "HMA"

    def test_requirement_tone(self):
        h = HeuristicExtractor()
        assert h.classify_requirement("The contractor shall achieve 92% density.")["classification"] == "REQUIRED"
        assert h.classify_requirement("It is recommended that..." )["classification"] == "RECOMMENDED"


class TestFileManifest:
    def test_classification(self):
        assert classify_file("civil-set.pdf") == "plans"
        assert classify_file("spec_2026.pdf") == "specs"
        assert classify_file("IMG_1024.jpg") == "photos"
        assert classify_file("misc.pdf") == "other"

    def test_reingest_no_duplicates(self, tmp_path):
        (tmp_path / "input").mkdir()
        f = tmp_path / "input" / "plan.pdf"
        f.write_text("plan v1")
        m = FileManifest()
        assert m.ingest(tmp_path / "input") == 1
        assert m.ingest(tmp_path / "input") == 0  # no duplicates

    def test_revision_detected(self, tmp_path):
        (tmp_path / "input").mkdir()
        f = tmp_path / "input" / "civil-set.pdf"
        f.write_text("v1")
        manifest = FileManifest()
        assert manifest.ingest(tmp_path / "input") == 1
        f.write_text("v2 revised")
        assert manifest.ingest(tmp_path / "input") == 1  # new content = new doc
        superseded = [d for d in manifest.documents if d.get("superseded_by")]
        assert len(superseded) == 1  # v1 superseded by v2, old source retained
