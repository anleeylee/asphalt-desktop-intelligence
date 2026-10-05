"""S01 — project workspace manager tests (acceptance from spec)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script
from scripts import s01_project_workspace as s01


def _make_mixed_files(project: Path, n: int = 20) -> None:
    for i in range(n):
        (project / "input" / "plans" / f"civil-{i:03d}.pdf").write_text(f"plan {i} content")
    for i in range(5):
        (project / "input" / "specs" / f"spec-{i}.pdf").write_text(f"spec {i}")
    for i in range(3):
        (project / "input" / "photos" / f"IMG_{i:03d}.jpg").write_text(f"img {i}")


class TestS01:
    def test_import_and_reread_no_duplicates(self, empty_project):
        _make_mixed_files(empty_project, n=20)
        rc = run_script(s01, ["--project", str(empty_project), "--input", str(empty_project / "input"), "--name", "ABC Parking Lot"])
        assert rc == 0
        pj = json.loads((empty_project / "project.json").read_text(encoding="utf-8"))
        assert len(pj["documents"]) == 28
        # re-run -> zero new documents
        rc2 = run_script(s01, ["--project", str(empty_project), "--input", str(empty_project / "input")])
        assert rc2 == 0
        pj2 = json.loads((empty_project / "project.json").read_text(encoding="utf-8"))
        assert len(pj2["documents"]) == 28

    def test_manifest_traceable(self, empty_project):
        _make_mixed_files(empty_project, n=5)
        run_script(s01, ["--project", str(empty_project), "--input", str(empty_project / "input")])
        manifest = json.loads((empty_project / "output" / "file_manifest.json").read_text(encoding="utf-8"))
        for doc in manifest["documents"]:
            assert doc["doc_id"] and doc["path"] and doc["sha256"]
            assert doc["category"] in ("plans", "specs", "photos", "other")

    def test_revised_file_retained(self, empty_project):
        f = empty_project / "input" / "plans" / "civil-set.pdf"
        f.write_text("version 1")
        run_script(s01, ["--project", str(empty_project), "--input", str(empty_project / "input")])
        f.write_text("version 2 revised")
        run_script(s01, ["--project", str(empty_project), "--input", str(empty_project / "input")])
        pj = json.loads((empty_project / "project.json").read_text(encoding="utf-8"))
        docs = [d for d in pj["documents"] if "civil-set" in d["filename"]]
        assert len(docs) == 2  # old source retained, new version added

    def test_dry_run_writes_nothing(self, empty_project):
        _make_mixed_files(empty_project, n=3)
        rc = run_script(s01, ["--project", str(empty_project), "--input", str(empty_project / "input"), "--dry-run"])
        assert rc == 0
        assert not (empty_project / "project.json").exists()
