#!/usr/bin/env python3
"""Generate golden photo fixtures for S09 (Pillow).

Creates: a bright clear photo, a dark low-light photo, and a blurred photo.
Reference areas are only used by tests to verify routing rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed; run: pip install Pillow", file=sys.stderr)
        return 1

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    # 1) clear bright photo: gray pavement with a dark patch (pothole-like)
    img = Image.new("RGB", (640, 480), (150, 150, 150))
    for x in range(200, 300):
        for y in range(150, 250):
            img.putpixel((x, y), (40, 40, 40))
    img.save(FIXTURE_DIR / "photo_clear.png")

    # 2) dark low-light photo
    dark = Image.new("RGB", (640, 480), (18, 18, 22))
    dark.save(FIXTURE_DIR / "photo_dark.png")

    # 3) blurred photo
    blur = img.filter(ImageFilter.GaussianBlur(radius=12))
    blur.save(FIXTURE_DIR / "photo_blurred.png")

    print(f"wrote 3 photo fixtures to {FIXTURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
