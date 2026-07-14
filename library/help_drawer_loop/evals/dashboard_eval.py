#!/usr/bin/env python3
"""
dashboard_eval.py — binary evals for vani_dashboard help-drawer integration.

Runs from the repo root (docs/ directory).
Writes summary JSON to Code_Improver/summaries/latest.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get("IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest.json"))

INDEX_HTML   = ROOT / "index.html"
HELP_JS      = ROOT / "assets" / "js" / "help-drawer.js"
STYLE_CSS    = ROOT / "assets" / "css" / "style.css"
CHARTS_JS    = ROOT / "assets" / "js" / "charts.js"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, passed: bool, detail: str) -> None:
        nonlocal failures
        if not passed:
            failures += 1
        checks.append({"name": name, "passed": passed, "detail": detail})

    index    = read(INDEX_HTML)
    help_js  = read(HELP_JS)
    charts_js = read(CHARTS_JS)
    css     = read(STYLE_CSS)

    # ── File existence ────────────────────────────────────────────────────────
    check(
        "help_drawer_js_exists",
        HELP_JS.exists() and HELP_JS.stat().st_size > 0,
        f"path: {HELP_JS}",
    )

    # ── index.html references ─────────────────────────────────────────────────
    check(
        "index_references_help_drawer_js",
        "help-drawer.js" in index,
        "looking for 'help-drawer.js' script tag in index.html",
    )

    check(
        "index_has_drawer_element",
        bool(re.search(r'class=["\'][^"\']*\bdrawer\b', index)),
        "looking for element with class 'drawer' in index.html",
    )

    check(
        "index_has_overlay_element",
        bool(re.search(r'class=["\'][^"\']*\boverlay\b', index)),
        "looking for element with class 'overlay' in index.html",
    )

    check(
        "index_has_help_btn",
        'id="help-btn"' in index,
        "looking for id=\"help-btn\" in index.html",
    )

    # ── help-drawer.js content ────────────────────────────────────────────────
    check(
        "help_js_defines_openHelp",
        "function openHelp" in help_js or "openHelp" in help_js,
        "looking for openHelp in help-drawer.js",
    )

    check(
        "help_js_defines_closeHelp",
        "function closeHelp" in help_js or "closeHelp" in help_js,
        "looking for closeHelp in help-drawer.js",
    )

    check(
        "help_btn_wired_to_open_help",
        "HelpDrawer.open" in index or bool(re.search(r"getElementById\(['\"]help-btn", help_js)),
        "looking for HelpDrawer.open onclick in index.html or addEventListener in help-drawer.js",
    )

    check(
        "help_js_handles_escape_key",
        "Escape" in help_js,
        "looking for Escape keydown handler in help-drawer.js",
    )

    check(
        "help_js_implements_focus_trap",
        "Tab" in help_js and "focus" in help_js,
        "looking for Tab focus trap in help-drawer.js",
    )

    # ── CSS ───────────────────────────────────────────────────────────────────
    check(
        "style_css_has_drawer_rule",
        ".drawer" in css,
        "looking for .drawer rule in assets/css/style.css",
    )

    # ── Task 003: pie chart sync (static checks) ──────────────────────────────
    check(
        "charts_js_stores_current_data",
        "_currentData = data" in charts_js,
        "looking for _currentData = data assignment in charts.js (buildCharts)",
    )

    check(
        "charts_js_has_sync_function",
        "syncNonActiveCharts" in charts_js,
        "looking for syncNonActiveCharts function in charts.js",
    )

    check(
        "charts_js_calls_sync_after_refresh",
        bool(re.search(r"refreshDt\(\)[\s\S]{0,80}syncNonActiveCharts", charts_js)),
        "looking for syncNonActiveCharts called after refreshDt in applySliceFilter",
    )

    check(
        "charts_js_exposes_getLastBuiltData",
        "getLastBuiltData" in charts_js,
        "looking for getLastBuiltData export in charts.js",
    )

    check(
        "charts_js_exposes_applyFilter",
        bool(re.search(r"applyFilter\s*:", charts_js)),
        "looking for applyFilter in Charts public API",
    )

    passed = sum(1 for c in checks if c["passed"])
    total  = len(checks)
    score  = passed / total if total else 0.0

    return {
        "all_passed": failures == 0,
        "score": score,
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
