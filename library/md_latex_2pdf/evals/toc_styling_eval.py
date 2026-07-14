#!/usr/bin/env python3
"""toc_styling_eval.py — task 001: toc.css styling checks."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get(
    "IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_toc_styling.json",
))

CSS_DIR = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "css"
TOC_CSS = CSS_DIR / "toc.css"
TOC_MD  = ROOT / "aps_embellisher" / "c_source_markdown" / "toc.md"
PDF_OUT = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "toc.pdf"


def _block(css: str, selector: str) -> str:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css, re.DOTALL)
    return m.group(1) if m else ""


def _h1_chapter_numbers_from_toc_md(text: str) -> tuple[bool, str]:
    """Each toc-depth-0 label must start with major chapter N and a space (N from first depth-1 N.M)."""
    pat = re.compile(
        r'<div class="toc-row toc-depth-(\d+)"[^>]*>.*?<span class="toc-label">([^<]*)</span>',
        re.DOTALL,
    )
    entries = pat.findall(text)
    prev_major = 0
    bad: list[tuple[str, int]] = []
    i = 0
    n = len(entries)
    while i < n:
        depth, label = entries[i]
        if depth != "0":
            i += 1
            continue
        label_s = label.strip()
        major: int | None = None
        j = i + 1
        while j < n:
            d2, lab2 = entries[j]
            if d2 == "0":
                break
            if d2 == "1":
                m = re.match(r"^(\d+)\.", lab2.strip())
                if m:
                    major = int(m.group(1))
                break
            j += 1
        if major is None:
            major = prev_major + 1 if prev_major else 1
        prev_major = major
        if not re.match(rf"^{major}\s+\S", label_s):
            bad.append((label_s, major))
        i += 1
    return (len(bad) == 0, repr(bad[:8]) if bad else "ok")


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        checks.append({"id": name, "passed": ok, "detail": detail})
        if not ok:
            failures += 1

    # 1. toc.css exists
    toc_exists = TOC_CSS.is_file()
    check("toc_css_file_exists", toc_exists, str(TOC_CSS))

    CSS_CHECKS_NEEDED = [
        "toc_font_family",
        "toc_page_shell_padding",
        "toc_title_aligned_left",
        "toc_title_font_size_2em",
        "toc_title_font_weight_400",
        "toc_title_border_bottom_gray",
        "toc_links_black_no_decoration",
        "toc_depth0_indent",
        "toc_grid_row_links",
        "toc_leader_dotted_middle_track",
        "toc_h1_font_18px",
        "toc_h2_font_16px",
        "toc_h3_font_14px",
        "toc_h4_font_14px",
        "toc_h1_bold",
        "toc_dots_terminate_1in_from_right",
        "toc_page_numbers_font",
    ]

    if not toc_exists:
        for name in CSS_CHECKS_NEEDED:
            check(name, False, "toc.css missing")
    else:
        css = TOC_CSS.read_text(encoding="utf-8")

        check(
            "toc_font_family",
            "-apple-system" in css,
            "system font stack not found" if "-apple-system" not in css else "ok",
        )

        page_block = _block(css, ".page")
        check(
            "toc_page_shell_padding",
            bool(re.search(r"padding\s*:\s*0\.75in", page_block)),
            page_block.strip() if "0.75in" not in page_block else "ok",
        )

        h1_block = _block(css, ".page-header h1")
        check(
            "toc_title_aligned_left",
            "text-align: left" in h1_block,
            h1_block.strip() if "text-align: left" not in h1_block else "ok",
        )

        check(
            "toc_title_font_size_2em",
            "font-size: 2em" in h1_block,
            h1_block.strip() if "font-size: 2em" not in h1_block else "ok",
        )

        check(
            "toc_title_font_weight_400",
            "font-weight: 400" in h1_block,
            h1_block.strip() if "font-weight: 400" not in h1_block else "ok",
        )

        has_border = bool(re.search(r"border-bottom\s*:", h1_block))
        not_none = not bool(re.search(r"border-bottom\s*:\s*(none|0[^.])", h1_block))
        check(
            "toc_title_border_bottom_gray",
            has_border and not_none,
            h1_block.strip() if not (has_border and not_none) else "ok",
        )

        a_block = _block(css, "nav.toc li a")
        links_ok = "text-decoration: none" in a_block and (
            "color: inherit" in a_block
            or "color: #000" in a_block
            or "color: black" in a_block
        )
        check(
            "toc_links_black_no_decoration",
            links_ok,
            a_block.strip() if not links_ok else "ok",
        )

        d0_label = _block(css, ".toc-depth-0 .toc-label")
        depth0_flush = bool(re.search(r"padding-left\s*:\s*0", d0_label))
        check(
            "toc_depth0_indent",
            depth0_flush,
            d0_label.strip() if not depth0_flush else "ok",
        )

        layout_ok = (
            ("display: grid" in a_block and "grid-template-columns" in a_block and "1fr" in a_block and "1in" in a_block)
            or ("display: table" in a_block and "table-layout: fixed" in a_block and "width: 100%" in a_block)
            or (
                "display: flex" in a_block
                and "align-items: baseline" in a_block
                and "width: 100%" in a_block
            )
        )
        check(
            "toc_grid_row_links",
            layout_ok,
            a_block.strip() if not layout_ok else "ok",
        )

        dots_block = _block(css, ".toc-dots")
        leader_ok = "border-bottom" in dots_block and "dotted" in dots_block
        check(
            "toc_leader_dotted_middle_track",
            leader_ok,
            dots_block.strip() if not leader_ok else "ok",
        )

        for selector, size, name in [
            (".toc-depth-0", "18px", "toc_h1_font_18px"),
            (".toc-depth-1", "16px", "toc_h2_font_16px"),
            (".toc-depth-2", "14px", "toc_h3_font_14px"),
            (".toc-depth-3", "14px", "toc_h4_font_14px"),
        ]:
            blk = _block(css, selector)
            ok = f"font-size: {size}" in blk
            check(name, ok, blk.strip() if not ok else "ok")

        d0_block = _block(css, ".toc-depth-0")
        check(
            "toc_h1_bold",
            "font-weight: bold" in d0_block,
            d0_block.strip() if "font-weight: bold" not in d0_block else "ok",
        )

        pg_block = _block(css, ".toc-page")
        dots_col_ok = (
            "width: 1in" in pg_block
            or "flex: 0 0 1in" in pg_block
            or "min-width: 1.5em" in pg_block
        )
        check(
            "toc_dots_terminate_1in_from_right",
            dots_col_ok,
            pg_block.strip() if not dots_col_ok else "ok",
        )

        pn_size_ok = "font-size: 16px" in pg_block or "font-size: 12pt" in pg_block
        pn_weight_ok = "font-weight: 300" in pg_block or "tabular-nums" in pg_block
        check(
            "toc_page_numbers_font",
            pn_size_ok and pn_weight_ok,
            pg_block.strip() if not (pn_size_ok and pn_weight_ok) else "ok",
        )

    # 3. Title text is "Contents" (check toc.md source)
    if not TOC_MD.is_file():
        check("toc_title_is_contents", False, "toc.md missing")
    else:
        first_line = TOC_MD.read_text(encoding="utf-8").splitlines()[0].strip()
        check("toc_title_is_contents",
              first_line == "# Contents",
              f"first line: {first_line!r}" if first_line != "# Contents" else "ok")

    # 12. Chapter numbers in TOC labels match numbered headings
    if not TOC_MD.is_file():
        check("toc_numbering_matches_markdown", False, "toc.md missing")
    else:
        text = TOC_MD.read_text(encoding="utf-8")
        rows = re.findall(
            r'class="toc-row\s+toc-depth-(\d+)"[^>]*>.*?<span class="toc-label">([^<]*)</span>',
            text, re.DOTALL,
        )
        bad = [
            (int(d), lbl.strip())
            for d, lbl in rows
            if int(d) > 0 and not re.match(r"^\d+[\d.]*\s+\S", lbl.strip())
        ]
        check("toc_numbering_matches_markdown", len(bad) == 0,
              f"non-numeric labels: {bad[:5]}" if bad else "ok")

    # 21. Depth-0 labels show chapter number (N Title) matching first depth-1 N.x
    if not TOC_MD.is_file():
        check("toc_h1_display_chapter_number", False, "toc.md missing")
    else:
        ok, detail = _h1_chapter_numbers_from_toc_md(TOC_MD.read_text(encoding="utf-8"))
        check("toc_h1_display_chapter_number", ok, detail)

    # 20. toc.pdf exists AND was produced in the current build run
    # Both toc.pdf and the merged PDF are written by the same md2pdf.py invocation,
    # so toc.pdf must be no older than the merged PDF.
    MERGED_PDF = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "EmbellisherDeveloperGuide1.1.pdf"
    toc_exists = PDF_OUT.is_file()
    merged_exists = MERGED_PDF.is_file()
    if toc_exists and merged_exists:
        toc_mtime    = PDF_OUT.stat().st_mtime
        merged_mtime = MERGED_PDF.stat().st_mtime
        fresh = toc_mtime >= merged_mtime - 5  # allow 5-second skew
        check("toc_pdf_output_exists", fresh,
              f"toc.pdf is stale (toc={toc_mtime:.0f}, merged={merged_mtime:.0f})" if not fresh else str(PDF_OUT))
    else:
        check("toc_pdf_output_exists", False,
              "toc.pdf missing" if not toc_exists else "merged PDF missing")

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
