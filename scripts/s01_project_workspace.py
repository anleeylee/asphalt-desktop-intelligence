#!/usr/bin/env python3
"""S01 — Asphalt Project Workspace Manager.

Create and maintain one normalized local workspace for a paving project.
This is infrastructure, not an AI mega-agent.

Outputs: project.json, file_manifest.json, source_index.json, audit.log
Rules: never overwrite source files; never delete a source file automatically;
derived files live in working/ or output/.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.file_manifest import FileManifest, CATEGORIES  # noqa: E402
from common.hashing import sha256_text  # noqa: E402

PROJECT_JSON_CONTRACT = {
    "project_id": "PROJECT-001",
    "name": "ABC Parking Lot",
    "location": None,
    "units": "US",
    "documents": [],
    "takeoffs": [],
    "specifications": [],
    "quotes": [],
    "tickets": [],
    "supplier_prices": [],
    "photos": [],
    "weather_runs": [],
    "calculation_runs": [],
}

FOLDER_TREE = [
    "input/plans",
    "input/specs",
    "input/quotes",
    "input/tickets",
    "input/supplier_quotes",
    "input/photos",
    "input/weather",
    "working",
    "output",
    "audit",
]


def _project_path(args) -> Path:
    return Path(args.project).resolve()


def _load_project_json(project_dir: Path) -> dict:
    pj = project_dir / "project.json"
    if pj.exists():
        with open(pj, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return dict(PROJECT_JSON_CONTRACT)


def _save_project_json(project_dir: Path, data: dict) -> None:
    with open(project_dir / "project.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _create_tree(project_dir: Path, dry_run: bool) -> None:
    for folder in FOLDER_TREE:
        target = project_dir / folder
        if dry_run:
            continue
        target.mkdir(parents=True, exist_ok=True)


def add_extra_args(parser):
    parser.add_argument("--name", help="project name")
    parser.add_argument("--location", help="project location")
    parser.add_argument("--customer-id", dest="customer_id", help="customer/project ID (optional)")
    parser.add_argument("--units", choices=("US", "Metric"), default="US", help="unit system")
    parser.add_argument(
        "--category", choices=CATEGORIES, help="force classification category for all inputs"
    )


def pipeline(args, config, audit):
    project_dir = _project_path(args)
    if not args.dry_run:
        _create_tree(project_dir, dry_run=False)
    else:
        log(args, f"[S01] dry-run: folder tree preview under {project_dir}")

    manifest = FileManifest()
    if args.input:
        added = manifest.ingest(args.input, category_hint=args.category)
        log(args, f"[S01] ingested {added} new document(s)")
        for rec in manifest.documents:
            audit.add_input(rec["path"], rec["sha256"])

    # Merge into project.json without duplicating documents (keyed by doc_id).
    project = _load_project_json(project_dir)
    if args.name:
        project["name"] = args.name
    if args.location:
        project["location"] = args.location
    if args.customer_id:
        project["project_id"] = args.customer_id
    if args.units:
        project["units"] = args.units

    existing = {d["doc_id"] for d in project.get("documents", [])}
    for rec in manifest.documents:
        if rec["doc_id"] not in existing:
            project["documents"].append(rec)

    project.setdefault("project_id", "PROJECT-001")
    project.setdefault("name", "Unnamed Project")

    source_index = {
        "index_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "by_category": {},
        "superseded": [d for d in manifest.documents if d.get("superseded_by")],
        "duplicates": manifest.find_duplicates(),
    }
    for cat in CATEGORIES:
        source_index["by_category"][cat] = [
            {"doc_id": d["doc_id"], "path": d["path"], "category": cat}
            for d in manifest.documents
            if d["category"] == cat
        ]

    if not args.dry_run:
        _save_project_json(project_dir, project)
        manifest_path = project_dir / "output" / "file_manifest.json"
        index_path = project_dir / "output" / "source_index.json"
    else:
        manifest_path = project_dir / "output" / "file_manifest.json"
        index_path = project_dir / "output" / "source_index.json"

    # Human-readable manifest dashboard (md) for convenience.
    manifest_md = project_dir / "output" / "file_manifest.md"

    outputs = {}
    outputs["project_json"] = (str(project_dir / "project.json"), "json", project)
    outputs["file_manifest"] = (str(manifest_path), "json", manifest.to_dict())
    outputs["source_index"] = (str(index_path), "json", source_index)
    outputs["manifest_dashboard"] = (str(manifest_md), "md", _manifest_sections(manifest, source_index))
    return outputs


def _manifest_sections(manifest: FileManifest, source_index: dict) -> list[tuple[str, str]]:
    from common.outputs import _table_to_markdown

    rows = [
        {
            "doc_id": d["doc_id"],
            "file": d["filename"],
            "category": d["category"],
            "size_bytes": d["size_bytes"],
            "sha256": d["sha256"][:12],
            "superseded_by": d.get("superseded_by") or "",
        }
        for d in manifest.documents
    ]
    sections = [
        ("Project Document Manifest", f"- documents indexed: {len(rows)}\n- duplicates: {len(source_index['duplicates'])}"),
        ("Documents", _table_to_markdown(rows)),
    ]
    return sections


def main() -> int:
    parser = build_parser("s01_project_workspace", "Asphalt project workspace manager (S01)", add_extra_args)
    return run_lifecycle(parser, "s01_project_workspace", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
