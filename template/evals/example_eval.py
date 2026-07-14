#!/usr/bin/env python3
"""
brand_eval.py — package.json displayName and activity bar / view titles: Crystal Context.

Run from repo root. Writes Code_Improver/summaries/latest_brand.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("IMPROVE_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SUMMARY_PATH = Path(os.environ.get(
    "IMPROVE_SUMMARY_PATH",
    ROOT / "Code_Improver" / "summaries" / "latest_brand.json",
))

EXPECTED = "Crystal Context"


def evaluate() -> dict:
    checks: list[dict] = []
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        checks.append({"id": name, "passed": ok, "detail": detail})
        if not ok:
            failures += 1

    pkg_path = ROOT / "package.json"
    if not pkg_path.is_file():
        check("brand_package_displayname_crystal_context", False, "missing package.json")
        check("brand_contributes_views_crystal_context", False, "missing package.json")
    else:
        try:
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            check("brand_package_displayname_crystal_context", False, str(e))
            check("brand_contributes_views_crystal_context", False, str(e))
        else:
            dn = data.get("displayName")
            check(
                "brand_package_displayname_crystal_context",
                dn == EXPECTED,
                f"displayName is {dn!r}, expected {EXPECTED!r}",
            )

            titles_ok = True
            parts: list[str] = []
            vc = (data.get("contributes") or {}).get("viewsContainers") or {}
            for _loc, groups in vc.items():
                if not isinstance(groups, list):
                    continue
                for g in groups:
                    if not isinstance(g, dict):
                        continue
                    t = g.get("title")
                    parts.append(f"viewsContainers[{g.get('id', '?')}].title={t!r}")
                    if t != EXPECTED:
                        titles_ok = False

            views = (data.get("contributes") or {}).get("views") or {}
            for cid, vlist in views.items():
                if not isinstance(vlist, list):
                    continue
                for v in vlist:
                    if not isinstance(v, dict):
                        continue
                    n = v.get("name")
                    parts.append(f"views[{cid}].{v.get('id', '?')}.name={n!r}")
                    if n != EXPECTED:
                        titles_ok = False

            detail = "; ".join(parts) if parts else "no viewsContainers/views entries"
            check(
                "brand_contributes_views_crystal_context",
                titles_ok and bool(parts),
                detail,
            )

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
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
