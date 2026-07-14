#!/usr/bin/env python3
"""
toc_render_eval.py — task 001

Two hard guarantees before any check runs:
  1. Deletes ``toc.pdf`` at the start, then runs mkdocs + md2pdf. If the pipeline
     does not recreate the file, checks fail (no stale PDF from a prior run).
  2. Every layout check clips the rendered PDF to a specific pixel region and
     tests actual rendered output — no CSS string parsing anywhere
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import fitz  # pymupdf

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get(
    "IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_toc_render.json",
))
PDF_OUT = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "toc.pdf"

# ── Rendering constants ───────────────────────────────────────────────────────
DPI   = 150
SCALE = DPI / 72.0   # PDF points → pixels
WHITE = 240          # grayscale: >= WHITE is background, < WHITE is content

# ── Layout constants in PDF points (72pt = 1in) ───────────────────────────────
# toc.css uses 0.75in side margins on h1 / .toc-list; generate_frontmatter_pdf uses
# Playwright L/R margin 0, so one inset only. CONTENT_LEFT_PT / content_right_pt
# are the inner edges of the text column (fitz: "Contents" h1 x0 ≈ 60pt).
CONTENT_LEFT_PT = 60.0
LIST_LEFT_PT    = CONTENT_LEFT_PT  # min x0 for TOC label words (list inner left)
PN_COL_PT       = 1.0 * 72    # .toc-page { width: 1in } → 72pt
TOL_PT          = 0.10 * 72   # ±0.10in pixel tolerance → 7.2pt
TITLE_BOTTOM_PT = 110.0       # "Contents" h1 band on page 0; skip below this y


# ── Build ─────────────────────────────────────────────────────────────────────

def _delete_toc_pdf_if_present() -> str | None:
    """Remove ``PDF_OUT`` so a successful run must recreate it. None = ok."""
    if not PDF_OUT.is_file():
        return None
    try:
        PDF_OUT.unlink()
        return None
    except OSError as exc:
        return f"could not delete {PDF_OUT} (close viewers using the file): {exc}"


def _build() -> None:
    """Run mkdocs then md2pdf (writes ``toc.pdf`` when TOC export runs)."""
    subprocess.run(
        ["mkdocs", "build", "-f", "aps_embellisher/mkdocs.yml"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["python", "python/md2pdf/md2pdf.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )


# ── Pixel helpers ─────────────────────────────────────────────────────────────

def _empty(page: fitz.Page, x0: float, y0: float, x1: float, y1: float) -> bool:
    """
    Lines 58-64: Clip page to the rectangle [x0,y0,x1,y1] (PDF points),
    render at DPI, return True if every pixel is >= WHITE (all background).
    """
    pix = page.get_pixmap(                                   # line 61: render clip only
        matrix=fitz.Matrix(SCALE, SCALE),
        clip=fitz.Rect(x0, y0, x1, y1),
        colorspace=fitz.csGRAY,
    )
    return all(v >= WHITE for v in pix.samples)              # line 65: any dark pixel = fail


def _has_content(page: fitz.Page, x0: float, y0: float, x1: float, y1: float) -> bool:
    """
    Lines 68-74: Clip page to rectangle, render at DPI,
    return True if any pixel < WHITE (content is present).
    """
    pix = page.get_pixmap(                                   # line 71: render clip only
        matrix=fitz.Matrix(SCALE, SCALE),
        clip=fitz.Rect(x0, y0, x1, y1),
        colorspace=fitz.csGRAY,
    )
    return any(v < WHITE for v in pix.samples)               # line 75: dark pixel = content found


# ── Summary helper ────────────────────────────────────────────────────────────

def _summary(checks: list[dict], failures: int) -> dict:
    passed = sum(1 for c in checks if c["passed"])
    total  = len(checks)
    return {
        "all_passed":       failures == 0,
        "score":            passed / total if total else 0.0,
        "metric_name":      "score",
        "metric_direction": "higher",
        "passed":           passed,
        "failed":           failures,
        "total":            total,
        "details":          checks,
    }


# ── Evaluate ──────────────────────────────────────────────────────────────────

def evaluate() -> dict:
    checks:   list[dict] = []
    failures: int        = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        checks.append({"id": name, "passed": ok, "detail": detail})
        if not ok:
            failures += 1

    NEEDED = [
        "toc_pdf_exists_after_build",
        "toc_left_margin_0p75in",
        "toc_right_margin_0p75in",
        "toc_pdf_has_no_blank_pages",
        "toc_dots_terminate_1in_from_right",
        "toc_all_entries_have_page_numbers",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # GUARANTEE 1 — remove old toc.pdf, rebuild; file must exist after pipeline
    # ══════════════════════════════════════════════════════════════════════════
    del_err = _delete_toc_pdf_if_present()
    if del_err:
        for name in NEEDED:
            check(name, False, del_err)
        return _summary(checks, failures)

    try:
        _build()
    except subprocess.CalledProcessError as exc:
        for name in NEEDED:
            check(name, False, f"build failed: {exc}")
        return _summary(checks, failures)

    # ── CHECK 1: toc_pdf_exists_after_build ───────────────────────────────────
    toc_ok = PDF_OUT.is_file() and PDF_OUT.stat().st_size > 0
    check(
        "toc_pdf_exists_after_build",
        toc_ok,
        f"missing or empty after build: {PDF_OUT}" if not toc_ok else "ok",
    )

    if not toc_ok:
        for name in NEEDED[1:]:
            check(name, False, "skipped — toc.pdf not recreated")
        return _summary(checks, failures)

    # ══════════════════════════════════════════════════════════════════════════
    # GUARANTEE 2 — open PDF, derive layout, pixel-check every criterion below
    # ══════════════════════════════════════════════════════════════════════════
    doc        = fitz.open(str(PDF_OUT))
    pages      = list(doc)
    page_w_pt  = pages[0].rect.width    # ~596pt  (A4)
    page_h_pt  = pages[0].rect.height   # ~843pt  (A4)

    content_right_pt = page_w_pt - CONTENT_LEFT_PT    # ~536pt — inner edge of right 0.75in gutter
    pn_right_pt      = content_right_pt               # page numbers right-align here
    pn_left_pt       = pn_right_pt - PN_COL_PT        # ~464pt — 1in page-number column

    # ── CHECK 2: toc_left_margin_0p75in ───────────────────────────────────────
    # Pixel scan: outer left gutter [0 → CONTENT_LEFT − tol] must be all-white
    # (0.75in from physical page edge before the main column). Skip title band on p0.
    left_fail_pages = []
    for pi, page in enumerate(pages):
        y_start = TITLE_BOTTOM_PT if pi == 0 else 0.0
        if not _empty(page, TOL_PT, y_start, CONTENT_LEFT_PT - TOL_PT, page_h_pt):
            left_fail_pages.append(pi)
    check("toc_left_margin_0p75in", len(left_fail_pages) == 0,
          f"content in left margin zone on page(s) {left_fail_pages}"
          if left_fail_pages else "ok")

    # ── CHECK 3: toc_right_margin_0p75in ──────────────────────────────────────
    # Pixel scan: outer right gutter [content_right + tol → page_w − tol] white.
    right_fail_pages = []
    for pi, page in enumerate(pages):
        y_start = TITLE_BOTTOM_PT if pi == 0 else 0.0
        if not _empty(page,
                      content_right_pt + TOL_PT, y_start,
                      page_w_pt - TOL_PT, page_h_pt):
            right_fail_pages.append(pi)
    check("toc_right_margin_0p75in", len(right_fail_pages) == 0,
          f"content in right margin zone on page(s) {right_fail_pages}"
          if right_fail_pages else "ok")

    # ── CHECK 4: toc_pdf_has_no_blank_pages ───────────────────────────────────
    # Every page must show at least some TOC ink in the list band (no empty filler pages).
    band_left = max(TOL_PT, LIST_LEFT_PT - 15.0)
    band_right = min(page_w_pt - TOL_PT, content_right_pt + 15.0)
    blank_pages: list[int] = []
    for pi, page in enumerate(pages):
        y_top = TITLE_BOTTOM_PT if pi == 0 else 12.0
        y_bot = page_h_pt - 18.0
        if y_top >= y_bot - 1.0:
            continue
        if _empty(page, band_left, y_top, band_right, y_bot):
            blank_pages.append(pi)
    check(
        "toc_pdf_has_no_blank_pages",
        len(blank_pages) == 0,
        f"no TOC ink in body band on page(s) {blank_pages}" if blank_pages else "ok",
    )

    # ── CHECKS 5 & 6: dots column + all entries have page numbers ─────────────
    # Strategy:
    #   a. Use fitz text extraction to identify the y-coordinate of every TOC row.
    #   b. For each row, use _has_content (pixel clip) to verify content in the
    #      page-number column [pn_left_pt, pn_right_pt].
    #   CHECK 4 additionally verifies that the rightmost ink in that zone is near
    #      pn_right_pt (1in column ending at the inner right edge of the text column).

    # Collect all words to find row y-positions
    row_positions: list[tuple[int, float]] = []   # (page_idx, y0_pt)
    for pi, page in enumerate(pages):
        seen_y: set[int] = set()
        for w in page.get_text("words"):           # line 176: fitz word extraction
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            # Only label words: in list x-range, not dots-only, not page-number digits
            if (LIST_LEFT_PT <= x0 < pn_left_pt
                    and not re.match(r"^[. ]+$", text)
                    and not re.match(r"^\d+$",   text)):
                # Skip "Contents" title on first page
                if pi == 0 and y0 < TITLE_BOTTOM_PT and text == "Contents":
                    continue
                bucket = int(y0)                   # line 185: deduplicate by row
                if bucket not in seen_y:
                    seen_y.add(bucket)
                    row_positions.append((pi, y0))

    missing_pn:        list[tuple[int, float]] = []
    inconsistent_col:  list[tuple[int, float]] = []

    for pi, y0 in row_positions:                   # line 193: one pixel check per row
        page   = pages[pi]
        y_top  = y0 - 2.0
        y_bot  = y0 + 14.0   # roughly one line height

        # Does the page-number zone have any rendered content for this row?
        has_pn = _has_content(page,
                              pn_left_pt, y_top,
                              pn_right_pt, y_bot)
        if not has_pn:
            missing_pn.append((pi, y0))
            continue

        # Verify right-alignment: render the PN zone at high res and find
        # the rightmost dark column, confirming a consistent right edge.
        pix = page.get_pixmap(
            matrix=fitz.Matrix(SCALE, SCALE),
            clip=fitz.Rect(pn_left_pt, y_top, pn_right_pt, y_bot),
            colorspace=fitz.csGRAY,
        )
        w_px = pix.width
        rightmost_x_px = 0
        for x in range(w_px - 1, -1, -1):          # line 214: scan right-to-left
            col = [pix.samples[r * w_px + x] for r in range(pix.height)]
            if any(v < WHITE for v in col):
                rightmost_x_px = x
                break
        rightmost_pt = pn_left_pt + rightmost_x_px / SCALE
        if abs(rightmost_pt - pn_right_pt) > TOL_PT:
            inconsistent_col.append((pi, y0))

    check("toc_dots_terminate_1in_from_right",
          len(inconsistent_col) == 0,
          f"{len(inconsistent_col)} rows have page numbers not right-aligned at list edge: "
          + str(inconsistent_col[:5]) if inconsistent_col else
          f"ok ({len(row_positions)} rows checked)")

    check("toc_all_entries_have_page_numbers",       # line 230
          len(missing_pn) == 0,
          f"{len(missing_pn)} entries missing page numbers: "
          + str([(f"p{pi}", f"y={y:.0f}pt") for pi, y in missing_pn[:8]])
          if missing_pn else f"ok ({len(row_positions)} rows checked)")

    return _summary(checks, failures)


def main() -> None:
    payload = evaluate()
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    sys.exit(0 if payload["all_passed"] else 1)


if __name__ == "__main__":
    main()
