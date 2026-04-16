#!/usr/bin/env python3
"""
charts_sync_eval.py — browser checks for task 003 (pie chart cross-chart sync).

Verifies that clicking a pie slice rebuilds the other two charts with filtered data.
All checks FAIL before the fix and PASS after.

Requires: server at http://localhost:8765/, npx playwright-cli available.
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
    ROOT / "Code_Improver" / "summaries" / "latest_charts_sync.json"))

SERVER_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8765/")
NPX = r"C:\tools\nvm4w\nodejs\npx.cmd"
PLAYWRIGHT_ARGS = ["--no-install", "playwright-cli"]

# JS that initialises charts and waits for them to render (runs inside page.evaluate)
INIT_AND_WAIT_JS = """
async () => {
  if (!window.Charts || typeof window.Charts.init !== 'function') return {ok: false, reason: 'Charts not found'};
  await window.Charts.init();
  await new Promise(r => setTimeout(r, 2500));
  return {ok: true};
}
"""

# JS template: apply filter then check that two non-clicked charts have totals
# matching the filtered table row count
SYNC_CHECK_JS = """
async () => {
  var getTotal = function(divId) {
    var info = Charts.getLastBuiltData(divId);
    if (!info || !info.data) return -1;
    return info.data.reduce(function(s, d) { return s + d.value; }, 0);
  };

  var getTableCount = function() {
    if (typeof jQuery === 'undefined') return -1;
    var $tbl = jQuery('#tab1-fragment #tab1-table');
    if (!$tbl.length || !jQuery.fn.dataTable || !jQuery.fn.dataTable.isDataTable($tbl[0])) return -1;
    return $tbl.DataTable().rows({filter: 'applied'}).count();
  };

  // Returns true if all category labels look like valid priority labels (not URLs, not raw numbers).
  // Regression guard: if the wrong column is used, categories appear as URLs or raw CSV numbers.
  var priorityCatsValid = function(divId) {
    var info = Charts.getLastBuiltData(divId);
    if (!info || !info.data) return false;
    return info.data.every(function(d) {
      var cat = String(d.category || '');
      var isUrl = (cat.slice(0, 4) === 'http');
      var isNum = (cat.length > 0 && !isNaN(Number(cat)));
      return !isUrl && !isNum;
    });
  };

  // Returns true if all action category labels are non-numeric strings.
  // Regression guard: a column-index bug produces pure numeric action categories.
  var actionCatsValid = function(divId) {
    var info = Charts.getLastBuiltData(divId);
    if (!info || !info.data) return false;
    return info.data.every(function(d) {
      var cat = String(d.category || '');
      return isNaN(Number(cat)) || cat.trim() === '';
    });
  };

  // ── Test 1: click an AUTHOR slice, check priority + action rebuild ─────
  var authorInfo = Charts.getLastBuiltData('tab2-chart-author');
  var fullPriorityTotal = getTotal('tab2-chart-priority');
  var fullActionTotal   = getTotal('tab2-chart-action');

  if (!authorInfo || !authorInfo.data || !authorInfo.data.length)
    return {ok: false, reason: 'no author chart data after init'};
  if (fullPriorityTotal <= 0)
    return {ok: false, reason: 'no priority chart data: ' + fullPriorityTotal};

  // pick first author that has fewer rows than total (so filter is meaningful)
  var testSlice = null;
  for (var i = 0; i < authorInfo.data.length; i++) {
    var s = authorInfo.data[i];
    if (s.rawValues && s.rawValues.length && s.value > 0 && s.value < fullPriorityTotal) {
      testSlice = s;
      break;
    }
  }
  if (!testSlice) return {ok: false, reason: 'no suitable author slice (all rows same author?)'};

  Charts.applyFilter(authorInfo.colHeader, testSlice.rawValues, testSlice.category, 'tab2-chart-author');
  await new Promise(r => setTimeout(r, 1500));

  var tableCountAfterAuthor = getTableCount();
  var priorityAfterAuthor   = getTotal('tab2-chart-priority');
  var actionAfterAuthor     = getTotal('tab2-chart-action');
  var priorityCats1Ok       = priorityCatsValid('tab2-chart-priority');
  var actionCats1Ok         = actionCatsValid('tab2-chart-action');

  var test1Ok = (priorityAfterAuthor === tableCountAfterAuthor) &&
                (actionAfterAuthor   === tableCountAfterAuthor) &&
                (priorityAfterAuthor  < fullPriorityTotal) &&
                priorityCats1Ok && actionCats1Ok;

  // ── Test 2: click an ACTION slice, check priority + author rebuild ─────
  // First clear by rebuilding everything fresh
  await window.Charts.init();
  await new Promise(r => setTimeout(r, 2000));

  var actionInfo = Charts.getLastBuiltData('tab2-chart-action');
  var fullPriorityTotal2 = getTotal('tab2-chart-priority');

  if (!actionInfo || !actionInfo.data || !actionInfo.data.length)
    return {ok: false, reason: 'no action chart data on second init'};

  var testActionSlice = null;
  for (var j = 0; j < actionInfo.data.length; j++) {
    var as = actionInfo.data[j];
    if (as.rawValues && as.rawValues.length && as.value > 0 && as.value < fullPriorityTotal2) {
      testActionSlice = as;
      break;
    }
  }
  if (!testActionSlice)
    return {ok: false, reason: 'no suitable action slice'};

  Charts.applyFilter(actionInfo.colHeader, testActionSlice.rawValues, testActionSlice.category, 'tab2-chart-action');
  await new Promise(r => setTimeout(r, 1500));

  var tableCountAfterAction = getTableCount();
  var priorityAfterAction   = getTotal('tab2-chart-priority');
  var authorAfterAction     = getTotal('tab2-chart-author');
  var priorityCats2Ok       = priorityCatsValid('tab2-chart-priority');

  var test2Ok = (priorityAfterAction === tableCountAfterAction) &&
                (authorAfterAction   === tableCountAfterAction) &&
                (priorityAfterAction  < fullPriorityTotal2) &&
                priorityCats2Ok;

  return {
    ok: test1Ok && test2Ok,
    test1: {
      fullPriorityTotal: fullPriorityTotal,
      tableCountAfterAuthorFilter: tableCountAfterAuthor,
      priorityTotalAfterAuthorFilter: priorityAfterAuthor,
      actionTotalAfterAuthorFilter: actionAfterAuthor,
      priorityCategoriesValid: priorityCats1Ok,
      actionCategoriesValid: actionCats1Ok,
      passed: test1Ok
    },
    test2: {
      fullPriorityTotal: fullPriorityTotal2,
      tableCountAfterActionFilter: tableCountAfterAction,
      priorityTotalAfterActionFilter: priorityAfterAction,
      authorTotalAfterActionFilter: authorAfterAction,
      priorityCategoriesValid: priorityCats2Ok,
      passed: test2Ok
    }
  };
}
"""


def run(args: list[str]) -> tuple[int, str]:
    cmd = [NPX] + PLAYWRIGHT_ARGS + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return result.returncode, (result.stdout + result.stderr).strip()


def compress_js(js_str: str) -> str:
    """Strip // line comments, collapse whitespace, join to single line.
    Required: playwright-cli run-code breaks on multi-line args on Windows."""
    parts = []
    for line in js_str.split('\n'):
        idx = line.find('//')
        if idx >= 0:
            line = line[:idx]
        line = line.strip()
        if line:
            parts.append(line)
    return ' '.join(parts)


def js(expr: str) -> tuple[int, str]:
    code = f"async page => {{ return await page.evaluate({compress_js(expr)}); }}"
    return run(["run-code", code])


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, passed: bool, detail: str) -> None:
        nonlocal failures
        if not passed:
            failures += 1
        checks.append({"name": name, "passed": passed, "detail": detail})

    # ── open browser ──────────────────────────────────────────────────────────
    rc, out = run(["open", SERVER_URL])
    if rc != 0:
        check("browser_opens", False, out[:300])
        return _summary(checks, failures, 0, 1)
    check("browser_opens", True, "ok")

    # ── Charts API exists ─────────────────────────────────────────────────────
    rc, out = js('() => typeof window.Charts')
    charts_present = '"object"' in out or "'object'" in out or "object" in out
    check("charts_api_present", charts_present, out[:100])

    rc, out = js('() => typeof (window.Charts && window.Charts.getLastBuiltData)')
    check("charts_exposes_getLastBuiltData",
          "function" in out, out[:100])

    rc, out = js('() => typeof (window.Charts && window.Charts.applyFilter)')
    check("charts_exposes_applyFilter",
          "function" in out, out[:100])

    if not charts_present:
        run(["close"])
        return _summary(checks, failures,
                        sum(1 for c in checks if c["passed"]), len(checks))

    # ── Charts.init() succeeds ────────────────────────────────────────────────
    rc, out = js(INIT_AND_WAIT_JS)
    init_ok = '"ok":true' in out.replace(' ', '') or "'ok':true" in out
    check("charts_init_succeeds", init_ok, out[:300])

    if not init_ok:
        run(["close"])
        return _summary(checks, failures,
                        sum(1 for c in checks if c["passed"]), len(checks))

    # ── chart data loaded after init ──────────────────────────────────────────
    rc, out = js('() => { var d = Charts.getLastBuiltData("tab2-chart-priority"); return d && d.data && d.data.length > 0; }')
    check("priority_chart_data_loaded", "true" in out.lower(), out[:100])

    rc, out = js('() => { var d = Charts.getLastBuiltData("tab2-chart-action"); return d && d.data && d.data.length > 0; }')
    check("action_chart_data_loaded", "true" in out.lower(), out[:100])

    rc, out = js('() => { var d = Charts.getLastBuiltData("tab2-chart-author"); return d && d.data && d.data.length > 0; }')
    check("author_chart_data_loaded", "true" in out.lower(), out[:100])

    # ── cross-chart sync ──────────────────────────────────────────────────────
    rc, out = js(SYNC_CHECK_JS)

    # parse result from output
    result_json = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('{') and '"ok"' in line:
            try:
                result_json = json.loads(line)
                break
            except Exception:
                pass
    # also try to find JSON block in markdown output
    if result_json is None:
        import re
        m = re.search(r'\{[^{}]*"ok"[^{}]*\}', out, re.DOTALL)
        if m:
            try:
                result_json = json.loads(m.group())
            except Exception:
                pass

    if result_json is None:
        check("priority_and_action_sync_after_author_filter", False,
              f"could not parse result: {out[:300]}")
        check("priority_and_author_sync_after_action_filter", False,
              "skipped — previous check failed to parse")
    else:
        t1 = result_json.get("test1", {})
        t2 = result_json.get("test2", {})
        check("priority_and_action_sync_after_author_filter",
              bool(t1.get("passed")),
              str(t1)[:300])
        check("priority_and_author_sync_after_action_filter",
              bool(t2.get("passed")),
              str(t2)[:300])

    # ── no console errors ─────────────────────────────────────────────────────
    rc, out = run(["console"])
    errors = [l.strip() for l in out.splitlines() if l.strip().startswith("[ERROR]")]
    check("no_console_errors_during_sync", not errors,
          f"errors: {errors[:3]}" if errors else "clean")

    run(["close"])
    passed = sum(1 for c in checks if c["passed"])
    total  = len(checks)
    return _summary(checks, failures, passed, total)


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
