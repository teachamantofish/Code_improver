# Code Improvement Framework

Read <root>/codeimproverREADME.md. This project uses a universal improvement plan-"autoresearch-like" loop strategy to fix issues. The loop identifies the problem, fixes the problems one at a time, adds a binary eval, and loops until the eval passes. Then it moves to the next test. The goal is to create better code with each pass *without stopping* and continually add eval tests whenever a problem is found and fixed. 

Project details: 

- Title: .
- Description: . 
- Workflow: 
  - Create a task category for each task type
  - Create success criteria for each task
  - Create matching evals for each success criteria
  - 
  - 
  - Use playwright-cli to verify the eval passes for each change 
  - Continue looping through evals until all tests pass. 
  - Proceed to the next task loop. 
- Output: 

## Artifacts

Place the following in /artifacts/: 

- logs
- debug files
- playwright screenshots
- all throw away files

## Loop command — REQUIRED for all agents

**Always run the loop with an explicit task ID**. For example: 

```bash
python Code_Improver/run_loop.py --task 007
# or
npm run improver:loop -- --task 007
```

Do NOT run without `--task` unless you intend a full project loop. Without it, the runner auto-detects an `in_progress` task — if none is found it falls back to a full loop, which is slow and defeats the micro-loop strategy.

The runner enforces the micro/full schedule automatically:
- Runs `N % full_loop_every == 0` (default: every 5 runs) → **FULL TEST LOOP ON ALL TASKS**
- All other runs → **MICRO TASK LOOP** (only evals listed in the task's `evals` array)
- `--full` flag forces a full loop immediately

Agents given a prompt must follow this rule. Never bypass it by calling eval scripts directly.

## Getting started

This directory contains a generic, project-local framework for iterative code improvement. Before starting, read and understand the following: 

- **/tasks/000_task_template_no_edit.json**: Create a new task for each category type; for example, adding a feature, processing file, adding a button. Create task files before eval.py scripts. 
- **<name>_eval.py**: `/evals/*_eval.py` scripts run pass/fail checks on project—static inspection of sources, browser automation, etc., so each improvement task has repeatable acceptance criteria and emits summary JSON. 
  - The name should match the associated task.
  - In general, for each success criteria line, there will be an eval. 
  - `eval_commands` references project-specific pass/fail (binary) evals used for testing and defining each loop scope.
  - Output summaries should write to a `/summaries/summary.json` file of the same name. 
- **config.json**: Update with the project name, runner commands script, and eval commands script. Tests must ALWAYS pass. 
- **sumaries.json**: Do nothing: Produced by running the eval scripts; each run writes a JSON report (pass/fail, score, and per-check details). They are the machine-readable record for the improvement loop; Override the output path with IMPROVE_SUMMARY_PATH as needed.

**Note**: After you understand the process and the example files, respond that you are ready to start. If you have questions, ask.    

## Framework Goal

This generic, reusable framework is designed to improve any codebase one task at a time. The framework is process-first rather than domain-first, so it can be reused for web apps, parsers, data pipelines, and so on. The project-specific such as tasks and evals but be updated per project.

## Core Idea

Follow a best-practices model-training implementation:

- fixed baseline
- small, bounded changes
- explicit evals
- structured experiment logging
- keep/discard/crash decisions
- repeatable iteration

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

Each task's `evals` array lists the checks that belong to it, using the format `script_name.py: check_name`. The runner extracts the unique script names and runs only those scripts in micro task loop mode. Example:

```json
"evals": [
  "extension_eval.py: npm_test_webview_regression",
  "extension_eval.py: npm_run_build"
]
```

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

Each task is a small file with:

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

Evals should be pluggable. The framework cannot assume what “good” means.

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

**PDF / print layout (HTML → PDF)** — lessons from the TOC task (task 001):

- **What went wrong (short):** Horizontal inset was applied **twice** (Playwright `page.pdf` margins **and** CSS margins on the same content), so the TOC sat too far from the page edges. **Leader lines** used `flex` plus a long `::after` dot string, which **does not rasterize reliably** in Chromium print/PDF, so dots often did not reach the page-number column. Render evals used geometry tuned to the old stack and drifted from reality until retuned.

- **Guidelines for future tests:**
  1. **One owner per axis** — If CSS defines page inset/margins, PDF engine margins on that axis should be **zero** (or the eval must explicitly model **both** layers). Layout evals should document or derive the real content box (e.g. from a one-page reference PDF), not copy magic coordinates from an obsolete pipeline.
  2. **Do not assert print output via fragile CSS** — `::after` text leaders and clever `flex` tricks often pass in the browser but **fail in print/PDF**. Prefer primitives that print predictably (e.g. **CSS grid** plus **`border-bottom: dotted`** on the stretch column).
  3. **Evals track the pipeline, not the wish** — When build steps or margins change, **update measurement-based checks** (or automate calibration) so “pass” still means “matches the agreed layout,” not “matches stale constants.”
  4. **Destructive preconditions** (e.g. delete output before rebuild) prove the file was **rewritten**, not that it is **correct**. Always pair them with geometry/pixel checks tied to the same layout model as in (1).

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

The framework should read this file. Scrape arbitrary console output only the purpose of discovering errors and creating new evals.

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

### 6. Visual / rendered-output evals (PDF)

CSS-text inspection is insufficient for PDF output. Browser rendering engines (Playwright/Chromium) can ignore CSS in ways that static checks miss — for example, `width: 100%` on a flex child escapes the CSS margin box, so a CSS rule setting `margin: 0 0.75in` has no effect on the rendered page margin.

**Pattern: pixel-level PDF verification with pymupdf**

1. Generate the PDF normally (Playwright `page.pdf()`).
2. Open the PDF with `fitz` (pymupdf — no poppler needed):
   ```python
   import fitz
   doc = fitz.open("output.pdf")
   page = doc[0]
   mat = fitz.Matrix(150/72, 150/72)  # 150 DPI
   pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
   w, h = pix.width, pix.height
   samples = pix.samples  # one byte per grayscale pixel
   rows = [[samples[y * w + x] for x in range(w)] for y in range(h)]
   ```
3. Scan pixel rows to measure what you care about:
   - **Margins**: scan columns left-to-right / right-to-left for first non-white pixel; convert px → inches via `px / DPI`.
   - **Content presence**: check a horizontal band (e.g., 35–75% of page width) for non-white pixels to verify dot leaders render.
   - **Column alignment**: check the rightmost 15% of rows to verify page numbers appear there.
4. Compare against expected values with a tolerance (±0.10in is reasonable for font rendering uncertainty).
5. Emit pass/fail JSON in the standard eval format.

**Why tolerances differ per side**: font rendering adds sub-pixel bearing on the left edge; right-aligned narrow digits (page numbers) don't reach the column's right edge, making measured right margin slightly larger than the CSS page margin. Use the same ±0.10in tolerance for both sides.

**Key lesson from task 002**: A CSS eval that reads `tablelist.css` for `margin: 0.75in` will pass even when the rendered PDF shows 1.5in margins (double-counted) or 0in margins (flex width override). Always pair CSS evals with a pixel-level visual eval that measures the actual rendered output.

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

- load config and task files
- run project commands
- run eval commands
- read a summary JSON
- decide keep/discard/crash
- log results consistently
- save artifacts per run
- report current status