#!/usr/bin/env python3
"""
Micro/full loop runner for Code_Improver.

Micro loop  — runs only evals scoped to the active task (fast).
Full loop   — runs all eval_commands (regression check).

Mode selection (in priority order):
  1. --full flag           → full loop
  2. loop_mode: "full" in config → full loop
  3. prior_runs % full_loop_every == 0 → full loop  (0, 5, 10 …)
  4. default              → micro loop

Usage:
  python Code_Improver/run_loop.py [--task 007] [--full]
  npm run improver:loop [-- --task 007] [-- --full]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "Code_Improver" / "config.json"
TASKS_DIR = ROOT / "Code_Improver" / "tasks"
RESULTS_PATH = ROOT / "Code_Improver" / "results.tsv"


def load_config() -> dict:
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))


def count_prior_runs() -> int:
    if not RESULTS_PATH.exists():
        return 0
    lines = [l for l in RESULTS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    return max(0, len(lines) - 1)  # subtract header row


def find_task(task_id: str | None) -> dict | None:
    for path in sorted(TASKS_DIR.glob("*.json")):
        if path.name.startswith("000"):
            continue
        try:
            task = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if task_id:
            if task.get("id") == task_id:
                return task
        else:
            if task.get("status") == "in_progress":
                return task
    return None


def scoped_evals(task: dict, all_commands: list[str]) -> list[str] | None:
    """Return eval_commands filtered to task's evals array, or None to fall back to full."""
    evals = task.get("evals")
    if not evals:
        return None
    scripts = {e.split(":")[0].strip() for e in evals}
    filtered = [cmd for cmd in all_commands if any(s in cmd for s in scripts)]
    return filtered or None


def run(cmd: str) -> None:
    print(f"\n--- {cmd} ---\n", flush=True)
    r = subprocess.run(cmd, shell=True, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", metavar="ID", help="Task ID to scope micro loop (e.g. 007)")
    parser.add_argument("--full", action="store_true", help="Force full project loop")
    args = parser.parse_args()

    cfg = load_config()
    full_loop_every: int = cfg.get("full_loop_every", 5)
    all_evals: list[str] = cfg.get("eval_commands") or []
    prior_runs = count_prior_runs()

    # Runner commands always execute first
    for cmd in cfg.get("runner_commands") or []:
        run(cmd)

    # Determine loop mode
    force_full = args.full or cfg.get("loop_mode") == "full"
    is_full = force_full or (prior_runs % full_loop_every == 0)

    if is_full:
        print(f"\nRUNNING FULL TEST LOOP ON ALL TASKS  (run #{prior_runs}, every {full_loop_every})\n", flush=True)
        for cmd in all_evals:
            run(cmd)
    else:
        task = find_task(args.task)
        if task is None:
            label = f"task {args.task}" if args.task else "any in_progress task"
            print(f"\nNo {label} found — falling back to FULL TEST LOOP ON ALL TASKS\n", flush=True)
            for cmd in all_evals:
                run(cmd)
        else:
            evals = scoped_evals(task, all_evals)
            if evals is None:
                print(f"\nTask {task['id']} has no evals — falling back to FULL TEST LOOP ON ALL TASKS\n", flush=True)
                for cmd in all_evals:
                    run(cmd)
            else:
                print(f"\nRUNNING MICRO TASK LOOP — task {task['id']}: {task.get('title', '')}\n", flush=True)
                for cmd in evals:
                    run(cmd)

    print("\n--- improver:loop OK (all gates passed) ---\n", flush=True)


if __name__ == "__main__":
    main()
