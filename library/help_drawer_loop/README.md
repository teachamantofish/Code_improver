# Code Improvement Framework

Read <root>/readme.md. This project uses a universal improvement plan-"autoresearch-like" loop strategy to fix issues. The loop identifies the problem, fixes the problems one at a time, adds a binary eval, and loops until the eval passes. Then it moves to the next test. The goal is to create better code with each pass *without stopping* and continually add eval tests whenever a problem is found and fixed. 

We are developing an HTML dashboard. All dashboard code is under /docs/. You need only analyze and work in /Code_Improver/ and /docs/. We will primarily be using the console in Webview to find errors and create evals, but any other strategy is welcome. 

**Note**: After you understand the process and the example files, respond that you are ready to start. If you have questions, ask.    

This directory contains a generic, project-local framework for iterative code improvement. The current EXAMPLE config is specialized for a HTML-to-Markdown project. Before starting, do the following: 

- Delete the sample data in results.tsv (leave the header row)
- Read and understand the html_md_eval.py script, then replace it with a new script in which to create new evals for the current project. `eval_commands` is references project-specific binary evals used for testing and defining each loop scope.
- Read, understand, and then delete the example task in /tasks/001_example_task.json. Create a new task for each category. In general, for each success criteria, there will be an eval. 
- Read, understand, and then delete the /summaries/latest.json file. 
- Update config.json with the project name, runner commands script, and eval commands script
- The acceptance policy is always: 
  - All required checks pass
  - Targeted metric or issue count improves

## Framework Goal

This generic, reusable framework is designed to improve any codebase one task at a time. The framework is process-first rather than domain-first, so it can be reused for:

- parsers
- data pipelines
- document conversion
- CLI tools
- web apps
- refactors
- automation scripts
- model and prompt workflows

The project-specific parts are easy to swap out and can be deleted if not needed:

- target files or commands
- task definitions
- eval commands
- acceptance policy
- artifact selection

## Core Framework Idea

Generally follow a best-practices model-training implementation:

- fixed baseline
- small, bounded changes
- explicit evals
- structured experiment logging
- keep/discard/crash decisions
- repeatable iteration

The framework should always answer:

1. What are we trying to improve?
2. What task are we on right now?
3. What commands produce the candidate output?
4. What evals decide whether the change is good?
5. What changed compared with the previous baseline?
6. Do we keep, discard, or investigate?

## Universal Loop

Loop scope is `task` by default. Only evals scoped to the active task run. Full project loop triggers on task completion or explicit flag.

For every iteration:

1. Select one task.
2. Capture the current baseline.
3. Run the project commands that produce the candidate output.
4. Run evals scoped to the active task (micro loop) or all evals (full loop).
5. Collect a machine-readable summary.
6. Compare against the previous accepted result.
7. Mark the attempt as `keep`, `discard`, or `crash`.
8. Save artifacts and append a result row.
9. Move to the next task only after the current one is resolved.

This loop should work regardless of whether the target is code quality, conversion quality, runtime speed, correctness, or output fidelity.

## Loop Scope Modes

Two modes control which evals run on each iteration:

### Micro Task Loop (default)

- Runs only evals tagged to the active task via its `evals` array
- Fast iteration — skips unrelated eval scripts entirely
- Terminal output: `RUNNING MICRO TASK LOOP`
- Use during active fix/iteration on a single task

### Full Project Loop

- Runs all `eval_commands` from config — every eval script, every task
- Catches regressions across the whole project
- Terminal output: `RUNNING FULL TEST LOOP ON ALL TASKS`
- Triggers automatically every `full_loop_every` runs (default: 5)
- Force any time with `--full` flag or set `loop_mode: "full"` in config

### Trigger Logic

```
run N % full_loop_every == 0  →  FULL TEST LOOP ON ALL TASKS
run N % full_loop_every != 0  →  MICRO TASK LOOP
--full flag                   →  FULL TEST LOOP ON ALL TASKS (override)
loop_mode: "full" in config   →  always full
```

### Eval Scoping in Tasks

Each task's `evals` array lists the checks that belong to it, using the format `script_name.py: check_name`. The runner extracts the unique script names and runs only those scripts in micro task loop mode.

```json
"evals": [
  "dashboard_eval.py: help_drawer_js_exists",
  "dashboard_eval.py: index_has_help_btn"
]
```

Tasks with no `evals` array fall back to running all eval commands.

## Required Framework Pieces

Every project using the framework should have these concepts:

### 1. Config

Defines:

- project name
- runner commands
- eval commands
- summary file path
- results log path
- artifacts directory
- acceptance policy
- primary metric
- `loop_mode` — `"task"` (default) or `"full"`
- `full_loop_every` — integer, how many runs between full project loops (default: `5`)

### 2. Tasks

Each task should be a small file or record with:

- stable task id
- title
- status
- priority
- description
- success criteria: usually maps 1:1 with evals/tests
- optional notes

### 3. Runner

A generic command runner should:

- execute the configured build or transformation commands
- capture stdout and stderr
- write run logs
- stop on failure
- pass paths and metadata to eval commands

### 4. Evals

Evals should be pluggable. The framework should not assume what “good” means.

Projects can define:

- unit or integration tests
- structural checks
- diff checks
- output validators
- benchmark commands
- schema checks
- snapshot checks
- binary pass/fail assertions
- numeric metrics

### 5. Summary

Evals should produce one machine-readable summary file with normalized fields such as:

- `all_passed`
- `score`
- `metric_name`
- `metric_direction`
- `passed`
- `failed`
- `warnings`
- `details`

The framework should read this file instead of scraping arbitrary console output.

### 6. Results Log

Every attempt should be recorded with:

- timestamp
- task id
- status
- decision
- primary metric
- run log path
- summary path
- short description

### 7. Artifacts

Each run should preserve enough material to debug regressions:

- command log
- summary JSON
- optional output snapshots
- optional diffs

## Acceptance Policy

The framework should support a generic acceptance policy:

- all required gates must pass
- the primary metric must improve in the configured direction, unless the user forces acceptance
- a crash is always logged as `crash`
- a non-improving but valid run is logged as `discard`
- a valid improving run is logged as `keep`

The policy must be configurable because different projects optimize different things:

- lower is better
- higher is better
- pass/fail only
- threshold based

## Project Specialization

To adapt the framework to a specific repo, we should only need to define:

- the task backlog
- the commands that generate output
- the eval commands
- the summary schema
- the acceptance policy

Everything else should remain generic.


## Common commands

```bash
uv run improve.py init
uv run improve.py status
uv run improve.py run --task 001 --description "first attempt"
uv run improve.py add-task 010 "New Task" --description "What to improve"
```
How it works:

- `improvement/config.json` defines runner commands, eval commands, and acceptance policy.
- `improvement/tasks/*.json` defines the backlog.
- `improvement/evals/` holds project-specific eval scripts.
- `improvement/results.tsv` logs every run as keep/discard/crash.
- `improvement/artifacts/` stores per-run logs and summaries.

## Recommended Eval Layers For Any Project

Most projects should use some mix of:

### 1. Build and execution evals

- commands complete successfully
- required outputs are produced

### 2. Correctness evals

- tests pass
- validation checks pass
- expected outputs match

### 3. Quality evals

- formatting is acceptable
- structure is preserved
- known bugs are absent

### 4. Performance evals

- runtime
- memory
- throughput
- output size

### 5. Regression evals

- previously fixed issues stay fixed
- known-good snapshots stay stable where expected

## Recommended Task Discipline

Tasks should stay narrow. Good tasks are:

- “preserve heading text in generated markdown”
- “flatten markdown output into one directory”
- “repair split JSON examples”
- “reduce anchor noise without breaking internal links”

Bad tasks are:

- “make everything better”
- “clean up conversion”
- “fix markdown quality”

The framework is strongest when tasks are small and evals are precise.

## Generic File Layout

A reusable layout should look like:

- `improve.py`
- `improvement/config.json`
- `improvement/tasks/`
- `improvement/artifacts/`
- `improvement/results.tsv`
- `improvement/summaries/`

Optional:

- `improvement/evals/`
- `improvement/baselines/`
- `improvement/snapshots/`

## Task Flow In Practice

For each task:

1. Mark the task `in_progress`.
2. Run the configured commands.
3. Run the eval commands.
4. Produce a summary JSON.
5. Compare against the latest accepted run.
6. Record a result row.
7. If accepted, mark task `done`.
8. If rejected, keep task `in_progress` or move to `blocked`.

## Definition Of Done For The Framework

The framework is complete when it can:

- initialize a project workspace
- load config and task files
- run project commands
- run eval commands
- read a summary JSON
- decide keep/discard/crash
- log results consistently
- save artifacts per run
- report current status
- work without being tied to one specific domain