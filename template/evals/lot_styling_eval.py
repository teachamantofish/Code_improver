#!/usr/bin/env python3
"""lot_styling_eval.py — task 002: tablelist.css styling and standalone PDF checks."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get(
    "IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_lot_styling.json",
))

CSS_DIR = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "css"
LOT_CSS = CSS_DIR / "tablelist.css"
LOT_PDF = ROOT / "aps_embellisher" / "e_pdfhtml_and_pdf" / "tables_list.pdf"


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

    lot_exists = LOT_CSS.is_file()
    check("lot_css_file_exists", lot_exists, str(LOT_CSS))

    if not lot_exists:
        for name in [
            "lot_entry_font_family",
            "lot_title_font_family",
            "lot_title_border_bottom",
            "lot_links_black",
            "lot_links_no_decoration",
            "lot_left_margin_0p75in",
            "lot_right_margin_0p75in",
            "lot_dots_present",
        ]:
            check(name, False, "tablelist.css missing")
    else:
        css = LOT_CSS.read_text(encoding="utf-8")

        entry_block = _block(css, "nav.lot")
        h1_block = _block(css, ".page-header h1")
        link_block = _block(css, "nav.lot li a")
        dots_block = _block(css, ".lot-dots")

        check("lot_entry_font_family",
              "-apple-system" in entry_block,
              entry_block.strip() if "-apple-system" not in entry_block else "ok")

        check("lot_entry_font_size_14px",
              "14px" in entry_block,
              entry_block.strip() if "14px" not in entry_block else "ok")

        check("lot_title_font_family",
              "-apple-system" in h1_block,
              h1_block.strip() if "-apple-system" not in h1_block else "ok")

        check("lot_title_border_bottom",
              "border-bottom" in h1_block,
              h1_block.strip() if "border-bottom" not in h1_block else "ok")

        links_dark = "black" in link_block or "#000" in link_block
        check("lot_links_black",
              links_dark,
              link_block.strip() if not links_dark else "ok")

        check("lot_links_no_decoration",
              "none" in link_block and "text-decoration" in link_block,
              link_block.strip() if "none" not in link_block else "ok")

        # margins verified by lot_visual_eval.py pixel measurements, not CSS text

        dots_ok = ("border-bottom" in dots_block and "dotted" in dots_block) or (
            "content" in dots_block and "." in dots_block
        )
        check(
            "lot_dots_present",
            dots_ok,
            dots_block.strip() if not dots_ok else "ok",
        )

    check("lot_pdf_exists", LOT_PDF.is_file(), str(LOT_PDF))

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
