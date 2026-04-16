#!/usr/bin/env python3
"""
browser_eval.py — playwright-cli browser checks for tasks 1 & 2.

Requires a local HTTP server at http://localhost:8765/
Requires: npx playwright-cli available on PATH.

All checks should FAIL before the help drawer is implemented.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get("IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_browser.json"))

SERVER_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8765/")
NPX = r"C:\tools\nvm4w\nodejs\npx.cmd"
PLAYWRIGHT_ARGS = ["--no-install", "playwright-cli"]


def run(args: list[str]) -> tuple[int, str]:
    cmd = [NPX] + PLAYWRIGHT_ARGS + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return result.returncode, (result.stdout + result.stderr).strip()


def js(expr: str) -> tuple[int, str]:
    """Evaluate a JS expression in page context. Returns (rc, output)."""
    code = f"async page => {{ return await page.evaluate(() => {{ {expr} }}); }}"
    return run(["run-code", code])


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, passed: bool, detail: str) -> None:
        nonlocal failures
        if not passed:
            failures += 1
        checks.append({"name": name, "passed": passed, "detail": detail})

    # ── open browser ─────────────────────────────────────────────────────────
    rc, out = run(["open", SERVER_URL])
    if rc != 0:
        check("browser_opens", False, out[:300])
        return _summary(checks, failures, 0, 1)
    check("browser_opens", True, "ok")

    # ── structural DOM checks (fail before implementation) ───────────────────
    rc, out = js("return !!document.querySelector('.drawer');")
    check("drawer_element_in_dom", "true" in out.lower(),
          "looking for .drawer element in live DOM")

    rc, out = js("return !!document.querySelector('.overlay');")
    check("overlay_element_in_dom", "true" in out.lower(),
          "looking for .overlay element in live DOM")

    rc, out = js("return !!document.getElementById('help-search');")
    check("drawer_has_search_input", "true" in out.lower(),
          "looking for #help-search input in DOM")

    rc, out = js("return !!document.querySelector('.drawer .close-btn');")
    check("drawer_has_close_button", "true" in out.lower(),
          "looking for .close-btn inside .drawer")

    rc, out = js("return !!document.querySelector('.drawer-list');")
    check("drawer_has_topic_list", "true" in out.lower(),
          "looking for .drawer-list in DOM")

    # ── no console errors on load ─────────────────────────────────────────────
    rc, out = run(["console"])
    errors_on_load = _extract_errors(out)
    check("no_console_errors_on_load", not errors_on_load,
          f"errors: {errors_on_load[:3]}" if errors_on_load else "clean")

    # ── clicking ? opens drawer ───────────────────────────────────────────────
    # Use JS .click() — playwright-cli pierces shadow DOM on sl-icon-button,
    # missing the host element's onclick. JS .click() matches real browser behavior.
    js("document.getElementById('help-btn').click();")
    time.sleep(1)

    rc, out = js("const d = document.querySelector('.drawer'); return d ? d.classList.contains('open') : false;")
    check("drawer_opens_on_help_btn_click", "true" in out.lower(), out[:200])

    rc, out = js("const o = document.querySelector('.overlay'); return o ? o.classList.contains('open') : false;")
    check("overlay_visible_when_drawer_open", "true" in out.lower(), out[:200])

    # ── search input is focused after open ────────────────────────────────────
    rc, out = js("return document.activeElement && document.activeElement.id === 'help-search';")
    check("search_input_focused_after_open", "true" in out.lower(), out[:200])

    # ── no errors after clicking help btn ────────────────────────────────────
    rc, out = run(["console"])
    errors_after_open = _extract_errors(out)
    check("no_console_errors_after_open", not errors_after_open,
          f"errors: {errors_after_open[:3]}" if errors_after_open else "clean")

    # ── Escape key closes drawer ──────────────────────────────────────────────
    run(["press", "Escape"])
    time.sleep(0.5)

    rc, out = js("const d = document.querySelector('.drawer'); return d ? !d.classList.contains('open') : false;")
    check("escape_key_closes_drawer", "true" in out.lower(), out[:200])

    # ── clicking ? again reopens, then overlay click closes ──────────────────
    js("document.getElementById('help-btn').click();")
    time.sleep(1)

    js("document.getElementById('help-overlay').click();")
    time.sleep(0.5)

    rc, out = js("const d = document.querySelector('.drawer'); return d ? !d.classList.contains('open') : false;")
    check("overlay_click_closes_drawer", "true" in out.lower(), out[:200])

    # ── close browser ─────────────────────────────────────────────────────────
    run(["close"])

    passed = sum(1 for c in checks if c["passed"])
    total  = len(checks)
    return _summary(checks, failures, passed, total)


def _extract_errors(log: str) -> list[str]:
    return [
        line.strip()
        for line in log.splitlines()
        if line.strip().startswith("[ERROR]")
    ]


def _summary(checks, failures, passed, total) -> dict:
    score = passed / total if total else 0.0
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
