#!/usr/bin/env python3
"""S04 — Asphalt Specification Reader & Conflict Checker.

Read paving specifications and convert requirements into structured project
constraints; compare them with plans and bids.

Every extracted field includes: value, unit, source page, quoted context,
confidence, state, classification (REQUIRED / RECOMMENDED / OPTIONAL /
EXAMPLE / REFERENCE ONLY). Conflicting requirements are surfaced, never
resolved by AI guesswork, and the tool cites source pages.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.ai_adapter import AIAdapter  # noqa: E402
from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.config import get as cfg_get  # noqa: E402
from common.errors import UnsupportedFileError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402
from common.pdftext import PDFText  # noqa: E402
from common.schemas import ReviewQueue  # noqa: E402

PG_RE = re.compile(r"\bPG\s*\d{2,3}-\d{2,3}\b", re.I)
MIX_RE = re.compile(r"\b(?:type|mix)\s*[A-Z0-9][A-Z0-9.\-]*\b", re.I)
SUPERPAVE_RE = re.compile(r"\b(superpave|sp)\s*\d+(?:\.\d+)?\b", re.I)
THICKNESS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(in|inch|inches|\"|mm)\s*(?:of|for)?\s*(?:hma|asphalt|ac|pavement|overlays?|surface)\b", re.I
)
DENSITY_RE = re.compile(r"(\d{2,3})\s*(?:%|percent)\s*(?:of\s*)?(?:maximum|theoretical|density|compaction)", re.I)
COMPACTION_RE = re.compile(r"(\d{2,3})\s*(?:%|percent)\s*compaction", re.I)
TACK_RE = re.compile(r"\b(SS-?[A-Za-z0-9\-]{1,6})\b", re.I)
BASE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:in|inch|inches|\")\s*(?:of\s*)?(?:aggregate|base)", re.I)
TEMP_RE = re.compile(r"(\d{2,3})\s*(?:°|\^|degrees)\s*F\b", re.I)
TESTING_KEYWORDS = ["tensile strength ratio", "nuclear gauge", "density gauge", "coring", "core sample", "compaction test", "smoothness", "friction"]
ACCEPTANCE_KEYWORDS = ["acceptance", "reject", "pay adjustment", "lot"]

FIELD_LABELS = {
    "thickness": "thickness",
    "density": "density/compaction",
    "mix": "mix designation",
    "pg": "PG/binder",
    "tack": "tack coat",
    "base": "base material",
    "temperature": "temperature",
    "testing": "testing requirement",
    "acceptance": "acceptance criteria",
}


def add_extra_args(parser):
    parser.add_argument("--takeoff", help="optional takeoff.json (plan vs spec check)")
    parser.add_argument("--quotes", help="optional quote_comparison.json (spec vs bid check)")
    parser.add_argument("--no-addenda-versioning", action="store_true", help="treat addenda as plain documents")


def sentence_split(text: str) -> list[str]:
    """Split into sentences; first join wrapped lines so '3 inches of\\nHMA'
    stays one statement."""
    joined = re.sub(r"\n(?=[A-Za-z0-9])", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", joined) if len(s.strip()) > 8]


def extract_requirements(page_text: str, page_idx: int, source_file: str, ai: AIAdapter) -> list[dict]:
    reqs: list[dict] = []
    for sentence in sentence_split(page_text):
        lowered = sentence.lower()
        tone = ai.heuristic.classify_requirement(sentence)

        def make(field: str, value, unit: str | None, context: str, confidence: float) -> dict:
            return {
                "field": field,
                "label": FIELD_LABELS.get(field, field),
                "value": value,
                "unit": unit,
                "classification": tone["classification"],
                "source_file": source_file,
                "source_page": page_idx,
                "quoted_context": context[:200],
                "confidence": round(min(0.99, tone["confidence"] * confidence), 3),
                "state": "EXTRACTED",
                "verified": False,
            }

        m = THICKNESS_RE.search(sentence)
        if m:
            reqs.append(make("thickness", float(m.group(1)), "mm" if m.group(2).lower() == "mm" else "in", m.group(0), 0.95))

        m = DENSITY_RE.search(sentence)
        if m:
            reqs.append(make("density", float(m.group(1)), "percent", m.group(0), 0.92))

        m = PG_RE.search(sentence)
        if m:
            reqs.append(make("pg", m.group(0).upper(), None, m.group(0), 0.97))

        m = TACK_RE.search(sentence)
        if m:
            reqs.append(make("tack", m.group(1).upper(), None, m.group(0), 0.88))

        m = BASE_RE.search(sentence)
        if m:
            reqs.append(make("base", float(m.group(1)), "in", m.group(0), 0.9))

        m = TEMP_RE.search(sentence)
        if m:
            reqs.append(make("temperature", float(m.group(1)), "deg_f", m.group(0), 0.93))

        for kw in TESTING_KEYWORDS:
            if kw in lowered:
                reqs.append(make("testing", kw.title(), None, sentence, 0.85))
                break

        for kw in ACCEPTANCE_KEYWORDS:
            if kw in lowered:
                reqs.append(make("acceptance", kw.title(), None, sentence, 0.85))
                break

        if "superpave" in lowered:
            m = SUPERPAVE_RE.search(sentence)
            reqs.append(make("mix", (m.group(0) if m else "Superpave").upper(), None, m.group(0) if m else sentence, 0.95))
        elif "hot mix" in lowered or "hma" in lowered:
            reqs.append(make("mix", "HMA", None, sentence, 0.8))

    return reqs


def dedupe(reqs: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for r in reqs:
        key = (r["field"], str(r["value"]), r["source_page"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def load_json(path: str | None) -> dict | None:
    if not path or not Path(path).exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def field_value(recs: list[dict], field: str, classification_filter: tuple = ()) -> list[tuple]:
    out = []
    for r in recs:
        if r.get("field") == field:
            if classification_filter and r.get("classification") not in classification_filter:
                continue
            try:
                out.append((float(r["value"]), r["source_file"], r["source_page"], r.get("classification")))
            except (TypeError, ValueError):
                out.append((r["value"], r["source_file"], r["source_page"], r.get("classification")))
    return out


def detect_conflicts(reqs: list[dict], takeoff: dict | None, quotes: dict | None) -> list[dict]:
    conflicts: list[dict] = []
    seq = [0]

    def add(mode: str, field: str, a: tuple, b: tuple, source_a: str, source_b: str) -> None:
        seq[0] += 1
        conflicts.append(
            {
                "conflict_id": f"CF-{seq[0]:03d}",
                "mode": mode,
                "field": field,
                "value_a": a[0] if a else None,
                "source_a": source_a,
                "value_b": b[0] if b else None,
                "source_b": source_b,
                "unit": "in",
                "status": "REVIEW REQUIRED",
            }
        )

    thicknesses = field_value(reqs, "thickness", classification_filter=("REQUIRED", "RECOMMENDED"))
    densities = field_value(reqs, "density")

    # SPEC vs ADDENDUM
    files = sorted({r["source_file"] for r in reqs})
    if len(files) > 1:
        for field in ("thickness", "density"):
            by_file: dict[str, list] = {}
            for r in reqs:
                if r["field"] == field:
                    by_file.setdefault(r["source_file"], []).append(r)
            base_vals = field_value(reqs, field)
            if len(by_file) > 1 and len(base_vals) > 1:
                base = base_vals[0]
                for other in base_vals[1:]:
                    try:
                        if abs(float(base[0]) - float(other[0])) > 1e-9:
                            add("SPEC vs ADDENDUM", field, base, other, base[1], other[1])
                    except (TypeError, ValueError):
                        pass

    # PLAN vs SPEC
    if takeoff:
        plan_thickness = None
        for rec in takeoff.get("takeoff", takeoff if isinstance(takeoff, list) else []):
            if isinstance(rec, dict) and rec.get("thickness"):
                plan_thickness = float(rec["thickness"])
                break
        if plan_thickness is not None and thicknesses:
            spec_thick = thicknesses[0]
            if abs(plan_thickness - float(spec_thick[0])) > 1e-9:
                add("PLAN vs SPEC", "thickness", (plan_thickness, "plan", None, None), spec_thick, "takeoff.json", spec_thick[1])

    # SPEC vs BID
    if quotes:
        for quote in quotes.get("quotes", []):
            bid_thickness = quote.get("thickness")
            if bid_thickness and thicknesses:
                spec_thick = thicknesses[0]
                if abs(float(bid_thickness) - float(spec_thick[0])) > 1e-9:
                    add("SPEC vs BID", "thickness", (bid_thickness, quote.get("quote_id"), None, None), spec_thick, quote.get("source_file", "quote"), spec_thick[1])
    return conflicts


def pipeline(args, config, audit):
    from common.hashing import sha256_file

    input_path = Path(args.input or ".")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*")) if input_path.is_dir() else []
    if not files:
        raise UnsupportedFileError(f"No specification files found under {input_path}")
    text_exts = {".pdf", ".txt", ".md"}
    files = [f for f in files if f.suffix.lower() in text_exts]
    if not files:
        raise UnsupportedFileError("No PDF/TXT specification files found (PDF or plain text only).")

    ai = AIAdapter(config)
    audit.set_model_provider(ai.provider, ai.model)
    threshold = cfg_get(config, "review.confidence_threshold", 0.90)
    review = ReviewQueue()

    all_reqs: list[dict] = []
    for f in files:
        digest = sha256_file(f)
        audit.add_input(str(f), digest)
        log(args, f"[S04] processing {f.name}")
        if f.suffix.lower() == ".pdf":
            pdf = PDFText(f)
            for page_idx, page_text in enumerate(pdf.page_texts, start=1):
                all_reqs.extend(extract_requirements(page_text, page_idx, str(f), ai))
        else:
            text = f.read_text(encoding="utf-8", errors="replace")
            all_reqs.extend(extract_requirements(text, 1, str(f), ai))

    all_reqs = dedupe(all_reqs)
    for r in all_reqs:
        if r["confidence"] < threshold:
            review.add(
                "low-confidence extraction",
                f"{r['field']} = {r['value']} (p{r['source_page']}) confidence {r['confidence']:.2f}",
                r["confidence"],
                r,
            )

    takeoff = load_json(args.takeoff)
    quotes = load_json(args.quotes)
    conflicts = detect_conflicts(all_reqs, takeoff, quotes)
    for c in conflicts:
        review.add("conflict", f"{c['mode']} {c['field']}: {c['value_a']} vs {c['value_b']}", 0.99, c)

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["spec_requirements"] = (str(project_out / "spec_requirements.json"), "json", {"requirements": all_reqs, "count": len(all_reqs)})
    outputs["conflicts"] = (str(project_out / "conflicts.json"), "json", {"conflicts": conflicts})
    outputs["review_queue"] = (str(project_out / "review_queue.json"), "json", review.to_dict())
    outputs["summary"] = (str(project_out / "spec_summary.md"), "md", _summary(all_reqs, conflicts, review))
    return outputs


def _summary(reqs, conflicts, review) -> list[tuple[str, str]]:
    rows = [
        {
            "field": r["label"],
            "value": r["value"],
            "unit": r.get("unit") or "",
            "classification": r["classification"],
            "source": Path(r["source_file"]).name,
            "page": r["source_page"],
            "confidence": f"{r['confidence']:.2f}",
        }
        for r in reqs
    ]
    sections = [
        ("Specification Summary", f"- requirements extracted: {len(reqs)}\n- conflicts: {len(conflicts)}"),
        ("Requirements", _table_to_markdown(rows)),
    ]
    if conflicts:
        sections.append(("Conflicts", _table_to_markdown([
            {"mode": c["mode"], "field": c["field"], "a": c["value_a"], "b": c["value_b"], "status": c["status"]}
            for c in conflicts
        ])))
    if review.items:
        sections.append(
            ("Human Review", "\n".join(f"- {line} — see review_queue.json" for line in review.summary_lines()))
        )
    return sections


def main() -> int:
    parser = build_parser("s04_specification_checker", "Asphalt specification reader & conflict checker (S04)", add_extra_args)
    return run_lifecycle(parser, "s04_specification_checker", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
