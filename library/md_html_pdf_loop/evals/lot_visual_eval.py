#!/usr/bin/env python3
"""lot_visual_eval.py — task 002: pixel-level verification of tables_list.pdf.

Renders the PDF to images via pymupdf (no poppler required) and measures:
  - Left and right content margins
  - Dot leaders extend across most of the row width
  - Page numbers appear in the right-hand column
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import fitz  # pymupdf

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get(
    "IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_lot_visual.json",
))
LOT_PDF = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "tables_list.pdf"

DPI = 150
WHITE = 245  # pixel value threshold for "white/blank"
LEFT_MARGIN_TOLERANCE_IN  = 0.10  # wider: font rendering adds slight bearing
RIGHT_MARGIN_TOLERANCE_IN = 0.10


def _pdf_to_gray_pixels(pdf_path: Path, page_index: int = 0):
    """Return (pixel_matrix, width_px, height_px, dpi) for one PDF page."""
    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    mat = fitz.Matrix(DPI / 72, DPI / 72)  # 72 is PDF points-per-inch
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    w, h = pix.width, pix.height
    samples = pix.samples  # bytes, one byte per pixel (grayscale)
    rows = [[samples[y * w + x] for x in range(w)] for y in range(h)]
    doc.close()
    return rows, w, h


def measure_margins(rows, width_px, height_px):
    """Find left/right content margins by scanning for first non-white column."""
    # skip top/bottom 10% to avoid header/footer artifacts
    y_start = height_px // 10
    y_end = height_px - height_px // 10

    left_px = 0
    for x in range(width_px):
        if any(rows[y][x] < WHITE for y in range(y_start, y_end)):
            left_px = x
            break

    right_px = width_px
    for x in range(width_px):
        col = width_px - 1 - x
        if any(rows[y][col] < WHITE for y in range(y_start, y_end)):
            right_px = col
            break

    left_in  = left_px  / DPI
    right_in = (width_px - right_px) / DPI
    return left_in, right_in


def check_dots_extend(rows, width_px, height_px):
    """Return fraction of content rows that have dots extending into the mid-content zone.

    Checks for non-white pixels in the 35–75% of page width band — this zone is
    after short labels but before the page-number column, so dots should appear there
    on most rows regardless of label length.
    """
    y_start = height_px // 10
    y_end = height_px - height_px // 10
    zone_start = int(width_px * 0.35)
    zone_end   = int(width_px * 0.75)

    content_rows = 0
    dot_rows = 0
    for y in range(y_start, y_end):
        row = rows[y]
        if any(row[x] < WHITE for x in range(width_px // 6)):
            content_rows += 1
            if any(row[x] < WHITE for x in range(zone_start, zone_end)):
                dot_rows += 1

    return dot_rows / content_rows if content_rows else 0.0


def check_page_numbers_right(rows, width_px, height_px):
    """Check that non-white pixels appear in the rightmost 15% of content rows."""
    y_start = height_px // 10
    y_end = height_px - height_px // 10
    right_zone_start = int(width_px * 0.85)

    content_rows = 0
    num_rows = 0
    for y in range(y_start, y_end):
        row = rows[y]
        if any(row[x] < WHITE for x in range(width_px // 4)):
            content_rows += 1
            if any(row[x] < WHITE for x in range(right_zone_start, width_px)):
                num_rows += 1

    return num_rows / content_rows if content_rows else 0.0


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        checks.append({"id": name, "passed": ok, "detail": detail})
        if not ok:
            failures += 1

    pdf_exists = LOT_PDF.is_file()
    check("lot_pdf_exists", pdf_exists, str(LOT_PDF))

    if not pdf_exists:
        for name in ["lot_left_margin_pixel", "lot_right_margin_pixel",
                     "lot_dots_extend_pixel", "lot_page_numbers_right_pixel"]:
            check(name, False, "PDF not found")
    else:
        rows, w, h = _pdf_to_gray_pixels(LOT_PDF, page_index=0)
        left_in, right_in = measure_margins(rows, w, h)

        left_ok = abs(left_in - 0.75) < LEFT_MARGIN_TOLERANCE_IN
        check("lot_left_margin_pixel", left_ok,
              f"left={left_in:.3f}in (expected 0.75±{LEFT_MARGIN_TOLERANCE_IN}in)")

        right_ok = abs(right_in - 0.75) < RIGHT_MARGIN_TOLERANCE_IN
        check("lot_right_margin_pixel", right_ok,
              f"right={right_in:.3f}in (expected 0.75±{RIGHT_MARGIN_TOLERANCE_IN}in)")

        dot_fraction = check_dots_extend(rows, w, h)
        check("lot_dots_extend_pixel", dot_fraction > 0.5,
              f"{dot_fraction:.0%} of content rows have dots spanning mid→right zone")

        num_fraction = check_page_numbers_right(rows, w, h)
        check("lot_page_numbers_right_pixel", num_fraction > 0.5,
              f"{num_fraction:.0%} of content rows have pixels in right 15%")

    passed = sum(1 for c in checks if c["passed"])
    total  = len(checks)
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
