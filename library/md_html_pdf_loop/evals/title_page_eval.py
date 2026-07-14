#!/usr/bin/env python3
"""title_page_eval.py — task 000: cover page CSS and config checks."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get(
    "IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_title_page.json",
))

sys.path.insert(0, str(ROOT / "python"))
from config import BANNER_IMAGE, COPYRIGHT, PDF_DIR, SUBTITLE, TITLE, VERSION

CSS_PATH = PDF_DIR / "css" / "pdf_body.css"


def _block(css: str, selector: str) -> str:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css, re.DOTALL)
    return m.group(1) if m else ""


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        checks.append({"id": name, "passed": ok, "detail": detail})
        if not ok:
            failures += 1

    # --- config values present ---
    check("title_page_title_exists", bool(TITLE), TITLE)
    check("title_page_subtitle_exists", bool(SUBTITLE), SUBTITLE)
    check("title_page_version_exists", bool(VERSION), VERSION)
    check("title_page_copyright_exists", bool(COPYRIGHT), COPYRIGHT)

    # --- banner image on disk ---
    banner_path = PDF_DIR / BANNER_IMAGE
    check("title_page_banner_image_exists", banner_path.is_file(), str(banner_path))

    css_exists = CSS_PATH.is_file()
    if not css_exists:
        for name in [
            "title_page_title_subtitle_alignment",
            "title_page_title_subtitle_font",
            "title_page_title_subtitle_color",
            "title_page_version_bold",
            "title_page_copyright_centered",
            "title_page_copyright_font",
            "title_page_copyright_color",
            "title_page_copyright_size",
            "title_page_copyright_position",
            "title_page_copyright_alignment",
            "title_page_copyright_padding",
            "title_page_copyright_margin",
            "title_page_copyright_border",
        ]:
            check(name, False, f"{CSS_PATH} missing")
    else:
        css = CSS_PATH.read_text(encoding="utf-8")

        title_block    = _block(css, ".pdf-cover-title")
        h1_block       = _block(css, ".pdf-cover-title h1")
        subtitle_block = _block(css, ".pdf-cover-subtitle")
        version_block  = _block(css, ".pdf-cover-version")
        copy_block     = _block(css, ".pdf-cover-copyright")

        # alignment: both title and subtitle right-aligned
        title_right    = "right" in title_block or "right" in h1_block
        subtitle_right = "right" in subtitle_block
        check("title_page_title_subtitle_alignment", title_right and subtitle_right,
              "need text-align:right in .pdf-cover-title and .pdf-cover-subtitle")

        # font: -apple-system must be explicit on cover elements
        has_font = (
            "-apple-system" in title_block
            or "-apple-system" in h1_block
            or "-apple-system" in subtitle_block
        )
        check("title_page_title_subtitle_font", has_font,
              "need font-family:-apple-system in .pdf-cover-title or h1 or subtitle")

        # color: #666666 (accept #666 shorthand) on title and subtitle
        color_ok = (
            ("#666" in h1_block or "#666" in title_block)
            and "#666" in subtitle_block
        )
        check("title_page_title_subtitle_color", color_ok,
              f"h1_block={h1_block.strip()!r}  subtitle_block={subtitle_block.strip()!r}")

        # version bold
        check("title_page_version_bold",
              "bold" in version_block,
              version_block.strip() if "bold" not in version_block else "ok")

        # copyright centered
        check("title_page_copyright_centered",
              "center" in copy_block,
              copy_block.strip() if "center" not in copy_block else "ok")

        # copyright alignment (same check, explicit name from task)
        check("title_page_copyright_alignment",
              "center" in copy_block,
              "need text-align:center in .pdf-cover-copyright")

        # copyright font
        check("title_page_copyright_font",
              "-apple-system" in copy_block,
              copy_block.strip() if "-apple-system" not in copy_block else "ok")

        # copyright color
        check("title_page_copyright_color",
              "#666" in copy_block,
              copy_block.strip() if "#666" not in copy_block else "ok")

        # copyright font-size present
        check("title_page_copyright_size",
              "font-size" in copy_block,
              copy_block.strip() if "font-size" not in copy_block else "ok")

        # copyright position absolute + bottom
        pos_ok = "absolute" in copy_block and "bottom" in copy_block
        check("title_page_copyright_position", pos_ok,
              copy_block.strip() if not pos_ok else "ok")

        # copyright padding (should be 0)
        check("title_page_copyright_padding",
              "padding" in copy_block,
              copy_block.strip() if "padding" not in copy_block else "ok")

        # copyright margin (should not add unexpected margin)
        margin_val = re.search(r"margin\s*:\s*([^;]+)", copy_block)
        margin_ok = margin_val is None or "0" in margin_val.group(1)
        check("title_page_copyright_margin", margin_ok,
              margin_val.group(0) if margin_val else "no margin (ok)")

        # copyright border (should have no border)
        check("title_page_copyright_border",
              "border" not in copy_block,
              copy_block.strip() if "border" in copy_block else "ok")

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    return {
        "all_passed": failures == 0,
        "score": passed / total if total else 0.0,
        "metric_name": "score",
        "metric_direction": "higher",
        "passed": passed,
        "failed": failures,
        "total": total,
        "details": checks,
    }


def main() -> None:
    payload = evaluate()
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    sys.exit(0 if payload["all_passed"] else 1)


if __name__ == "__main__":
    main()
