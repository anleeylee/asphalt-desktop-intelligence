#!/usr/bin/env python3
"""S09 — Asphalt Field Photo Condition Analyzer.

Screen site photographs for visible pavement distress and field conditions.
This is visual screening, not structural pavement diagnosis — the tool never
infers layer strength, CBR, remaining life, exact repair depth, or the
engineering cause of cracking from a photo alone.

Deterministic parts: image decode, EXIF (timestamp/GPS/orientation), quality
metrics (brightness, blur, contrast). Distress classification runs only when a
vision-capable AI backend is configured; otherwise every photo goes to the
human-review queue. Approximate measurements require a known reference
dimension and are always marked APPROXIMATE until verified.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.ai_adapter import AIAdapter  # noqa: E402
from common.cli import build_parser, log, parse_args, resolve_output_path, run_lifecycle  # noqa: E402
from common.errors import UnsupportedFileError  # noqa: E402
from common.outputs import _table_to_markdown  # noqa: E402
from common.schemas import ReviewQueue  # noqa: E402

DETECTION_CLASSES = [
    "pothole",
    "longitudinal_cracking",
    "transverse_cracking",
    "alligator_cracking",
    "rutting",
    "edge_deterioration",
    "patching",
    "standing_water",
    "surface_segregation",
]


def add_extra_args(parser):
    parser.add_argument("--reference-dim", dest="reference_dim", type=float, help="known reference object dimension in inches")
    parser.add_argument("--reference-label", dest="reference_label", help="description of the reference object")


def quality_metrics(img) -> dict:
    from PIL import Image, ImageFilter

    gray = img.convert("L")
    width, height = gray.size
    hist = gray.histogram()
    total = width * height or 1
    mean = sum(i * c for i, c in enumerate(hist)) / total
    variance = sum(((i - mean) ** 2) * c for i, c in enumerate(hist)) / total
    edges = gray.filter(ImageFilter.FIND_EDGES)
    ehist = edges.histogram()
    e_total = width * height or 1
    e_mean = sum(i * c for i, c in enumerate(ehist)) / e_total
    blur_score = sum(((i - e_mean) ** 2) * c for i, c in enumerate(ehist)) / e_total  # Laplacian-like variance
    return {
        "brightness_mean": round(mean, 2),
        "brightness_variance": round(variance, 2),
        "blur_score": round(blur_score, 2),
        "width_px": width,
        "height_px": height,
    }


def exif_info(img) -> dict:
    from PIL import ExifTags

    info = {}
    try:
        exif = img.getexif()
        for tag, value in exif.items():
            name = ExifTags.TAGS.get(tag, str(tag))
            if name in ("DateTimeOriginal", "DateTime", "Orientation"):
                info[name] = str(value)
        gps = exif.get_ifd(0x8825)  # GPSInfo
        if gps:
            lat = gps.get(2)
            lon = gps.get(4)
            if lat and lon:
                info["gps_lat"] = _dms_to_decimal(lat, gps.get(1, "N"))
                info["gps_lon"] = _dms_to_decimal(lon, gps.get(3, "W"))
    except Exception:  # noqa: BLE001 - EXIF is best-effort
        pass
    return info


def _dms_to_decimal(value, ref) -> float:
    d, m, s = [float(v) for v in value]
    decimal = d + m / 60.0 + s / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return round(decimal, 6)


def screening(photo_id: str, path: Path, img, ai: AIAdapter, reference_dim: float | None, reference_label: str | None) -> dict:
    q = quality_metrics(img)
    exif = exif_info(img)
    observations: list[dict] = []
    notes: list[str] = []

    vision = ai.analyze_image(str(path)) if ai.available else None
    if vision and isinstance(vision, dict) and vision.get("observations"):
        observations = vision["observations"]
        for obs in observations:
            obs["class"] = obs.get("class")
            obs["confidence"] = min(0.99, float(obs.get("confidence", 0.5)))
            if obs["class"] not in DETECTION_CLASSES:
                notes.append(f"vision reported out-of-schema class {obs['class']!r} (kept as observed)")
    else:
        notes.append("vision classifier not configured or no observations; manual review required")

    # quality routing
    poor = q["brightness_mean"] < 40 or q["brightness_mean"] > 225 or q["blur_score"] < 1.0
    if poor:
        notes.append("poor image quality (low light / blurry / overexposed) — routed to review")

    measurements = []
    if reference_dim and reference_label and observations:
        measurements.append(
            {
                "class": observations[0]["class"],
                "approximate": True,
                "note": f"approximate sizing vs reference {reference_label!r} ({reference_dim} in); marked APPROXIMATE until verified",
                "status": "APPROXIMATE",
            }
        )

    return {
        "photo_id": photo_id,
        "source_file": str(path),
        "quality": q,
        "exif": exif,
        "observations": observations,
        "severity": "screening_only",
        "notes": notes,
        "measurements": measurements,
        "human_review_required": True,
    }


def pipeline(args, config, audit):
    from common.hashing import sha256_file

    input_path = Path(args.input or ".")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*")) if input_path.is_dir() else []
    if not files:
        raise UnsupportedFileError(f"No photo files found under {input_path}")
    supported = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
    files = [f for f in files if f.suffix.lower() in supported]
    if not files:
        raise UnsupportedFileError(f"No supported photos under {input_path} (JPG/PNG/HEIC)")

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise UnsupportedFileError("Photo analysis requires Pillow (pip install Pillow).") from exc

    ai = AIAdapter(config)
    audit.set_model_provider(ai.provider, ai.model)
    review = ReviewQueue()

    analyses: list[dict] = []
    for idx, f in enumerate(files, start=1):
        digest = sha256_file(f)
        audit.add_input(str(f), digest)
        photo_id = f"IMG-{idx:03d}"
        log(args, f"[S09] processing {f.name}")
        try:
            img = Image.open(f)
            img = ImageOps_auto_orient(img)
        except Exception as exc:  # noqa: BLE001
            review.add("unreadable image", f"{f.name}: {exc}", 0.0, {"source_file": str(f)})
            continue
        result = screening(photo_id, f, img, ai, args.reference_dim, args.reference_label)
        analyses.append(result)
        review.add(
            "photo requires human review",
            f"{photo_id}: visual screening only; distress classification pending review",
            0.5,
            result,
        )

    project_out = Path(args.project) / "output"
    project_out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    outputs["photo_analysis"] = (str(project_out / "photo_analysis.json"), "json", {"photos": analyses, "screening_only": True})
    outputs["summary"] = (str(project_out / "photo_summary.md"), "md", _summary(analyses))
    outputs["review_queue"] = (str(project_out / "review_queue.json"), "json", review.to_dict())
    return outputs


def ImageOps_auto_orient(img):
    try:
        from PIL import ImageOps

        return ImageOps.exif_transpose(img)
    except Exception:  # noqa: BLE001
        return img


def _summary(analyses) -> list[tuple[str, str]]:
    rows = [
        {
            "photo_id": a["photo_id"],
            "file": Path(a["source_file"]).name,
            "brightness": a["quality"]["brightness_mean"],
            "blur_score": a["quality"]["blur_score"],
            "observations": "; ".join(f"{o['class']}({o['confidence']:.2f})" for o in a["observations"]),
            "severity": a["severity"],
            "review_required": a["human_review_required"],
        }
        for a in analyses
    ]
    sections = [
        ("Field Photo Screening",
         f"- photos: {len(analyses)}\n- screening only; no structural diagnosis"),
        ("Photos", _table_to_markdown(rows)),
    ]
    return sections


def main() -> int:
    parser = build_parser("s09_field_photo_analyzer", "Asphalt field photo condition analyzer (S09)", add_extra_args)
    return run_lifecycle(parser, "s09_field_photo_analyzer", pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
