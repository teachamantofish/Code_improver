#!/usr/bin/env python3
"""improve.py — iterative code improvement runner.

Usage:
    uv run improve.py init
    uv run improve.py status
    uv run improve.py run --task 001 --description "first attempt"
    uv run improve.py run --task 001 --full          # force full project loop
    uv run improve.py add-task 004 "New Task" --description "What to improve"

Loop scope:
    Default is MICRO TASK LOOP — runs only evals scoped to the active task.
    Every `full_loop_every` runs (default 5) escalates to FULL TEST LOOP ON ALL TASKS.
    Override with --full flag or set loop_mode: "full" in config.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "Code_Improver" / "config.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_tasks(cfg: dict) -> list[dict]:
    task_dir = ROOT / cfg["task_dir"]
    tasks = []
    for f in sorted(task_dir.glob("*.json")):
        tasks.append(json.loads(f.read_text(encoding="utf-8")))
    return tasks


def count_runs(cfg: dict) -> int:
    results_path = ROOT / cfg["results_file"]
    if not results_path.exists():
        return 0
    with results_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return sum(1 for _ in reader)


def task_eval_commands(task: dict, cfg: dict) -> list[str]:
    """Return eval commands scoped to this task via its evals list.

    Task evals use the format: "script_name.py: check_name"
    We extract unique script names, then match against config eval_commands.
    Falls back to all eval_commands if no match found.
    """
    scoped_scripts: set[str] = set()
    for ref in task.get("evals", []):
        script = ref.split(":")[0].strip()
        scoped_scripts.add(script)

    matched = [
        cmd for cmd in cfg["eval_commands"]
        if any(cmd.endswith(s) or cmd.split("/")[-1] == s for s in scoped_scripts)
    ]
    return matched if matched else cfg["eval_commands"]


def run_commands(commands: list[str]) -> list[tuple[str, int]]:
    results = []
    for cmd in commands:
        print(f"  >> {cmd}")
        proc = subprocess.run(cmd.split(), cwd=ROOT)
        results.append((cmd, proc.returncode))
    return results


def append_result(cfg: dict, task: dict, decision: str, score: float,
                  passed: int, failed: int, description: str) -> None:
    results_path = ROOT / cfg["results_file"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    row = {
        "timestamp": ts,
        "task_id": task["id"],
        "task_title": task["title"],
        "attempt_status": "completed",
        "decision": decision,
        "metric_name": cfg["primary_metric"]["field"],
        "metric_value": score,
        "passed": passed,
        "failed": failed,
        "run_dir": "",
        "summary_path": "",
        "description": description,
    }
    with results_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()), delimiter="\t")
        writer.writerow(row)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(cfg: dict) -> None:
    print(f"Initialized: {cfg['project_name']}")
    print(f"Config: {CONFIG_PATH}")
    print(f"Loop mode: {cfg.get('loop_mode', 'task')} | Full every: {cfg.get('full_loop_every', 5)} runs")


def cmd_status(cfg: dict) -> None:
    tasks = load_tasks(cfg)
    runs = count_runs(cfg)
    full_every = cfg.get("full_loop_every", 5)
    next_full = full_every - (runs % full_every) if runs % full_every != 0 else full_every

    print(f"\nProject : {cfg['project_name']}")
    print(f"Runs    : {runs} total | Full loop every {full_every} | Next full in {next_full} run(s)")
    print(f"\nTasks ({len(tasks)}):")
    for t in tasks:
        print(f"  [{t['id']}] {t['status']:<12} {t['title']}")


def cmd_run(args: argparse.Namespace, cfg: dict) -> None:
    tasks = load_tasks(cfg)
    task = next((t for t in tasks if t["id"] == args.task), None)
    if not task:
        print(f"ERROR: task {args.task} not found.", file=sys.stderr)
        sys.exit(1)

    full_every = cfg.get("full_loop_every", 5)
    run_number = count_runs(cfg) + 1
    force_full = args.full or cfg.get("loop_mode") == "full"
    is_full_loop = force_full or (run_number % full_every == 0)

    print()
    if is_full_loop:
        print("=" * 50)
        print("RUNNING FULL TEST LOOP ON ALL TASKS")
        print("=" * 50)
        commands = cfg["eval_commands"]
    else:
        print("-" * 50)
        print("RUNNING MICRO TASK LOOP")
        print(f"Task: [{task['id']}] {task['title']}")
        print("-" * 50)
        commands = task_eval_commands(task, cfg)

    print(f"Evals ({len(commands)}):")
    results = run_commands(commands)

    passed = sum(1 for _, rc in results if rc == 0)
    failed = sum(1 for _, rc in results if rc != 0)
    all_passed = failed == 0
    score = passed / len(results) if results else 0.0
    decision = "keep" if all_passed else "discard"

    print()
    print(f"Result  : {decision.upper()} | {passed}/{len(results)} evals passed")

    append_result(cfg, task, decision, score, passed, failed,
                  args.description or ("full loop" if is_full_loop else "micro loop"))


def cmd_add_task(args: argparse.Namespace, cfg: dict) -> None:
    task_dir = ROOT / cfg["task_dir"]
    task_id = args.task_id.zfill(3)
    slug = args.title.lower().replace(" ", "_")
    path = task_dir / f"{task_id}_{slug}.json"
    task = {
        "id": task_id,
        "title": args.title,
        "status": "pending",
        "priority": "medium",
        "description": args.description or "",
        "success_criteria": [],
        "evals": [],
        "notes": "",
    }
    path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    print(f"Task {task_id} created: {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Code improvement runner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Show config and initialize workspace")
    sub.add_parser("status", help="Show task backlog and run stats")

    p_run = sub.add_parser("run", help="Run evals for a task")
    p_run.add_argument("--task", required=True, help="Task ID (e.g. 001)")
    p_run.add_argument("--description", default="", help="Short description of this attempt")
    p_run.add_argument("--full", action="store_true", help="Force full project loop")

    p_add = sub.add_parser("add-task", help="Create a new task file")
    p_add.add_argument("task_id", help="Numeric ID (e.g. 004)")
    p_add.add_argument("title", help="Task title")
    p_add.add_argument("--description", default="")

    args = parser.parse_args()
    cfg = load_config()

    dispatch = {
        "init": lambda: cmd_init(cfg),
        "status": lambda: cmd_status(cfg),
        "run": lambda: cmd_run(args, cfg),
        "add-task": lambda: cmd_add_task(args, cfg),
    }

    if args.command in dispatch:
        dispatch[args.command]()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
