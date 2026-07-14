# Universal Improvement Framework Plan

Starter prompt:  This project uses a universal improvement plan outlined in trainingplan.md. I'm using an "autoresearch-like" loop strategy to fix issues. The loop identifies the problem, fixes the problems one at a time, adds a binary eval, and loops until the eval passes. Then it moves to the next test. The goal is to create better code with each pass and continually add eval tests whenever a problem is found and fixed.

After you understand the process, we will start.    

## Goal

Build a generic, reusable framework for improving any codebase one task at a time. The framework should be process-first rather than domain-first, so it can be reused for:

- parsers
- data pipelines
- document conversion
- CLI tools
- web apps
- refactors
- automation scripts
- model and prompt workflows

The project-specific parts should be easy to swap out:

- target files or commands
- task definitions
- eval commands
- acceptance policy
- artifact selection

## Core Idea

Reuse the best part of the `custom_training` mindset without copying its model-training implementation:

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

For every iteration:

1. Select one task.
2. Capture the current baseline.
3. Run the project commands that produce the candidate output.
4. Run all configured evals.
5. Collect a machine-readable summary.
6. Compare against the previous accepted result.
7. Mark the attempt as `keep`, `discard`, or `crash`.
8. Save artifacts and append a result row.
9. Move to the next task only after the current one is resolved.

This loop should work regardless of whether the target is code quality, conversion quality, runtime speed, correctness, or output fidelity.

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

### 2. Tasks

Each task should be a small file or record with:

- stable task id
- title
- status
- priority
- description
- success criteria
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

## Example Specialization For This Repo

For this HTML-to-Markdown repo, the specialization would be:

- runner commands:
  - `uv run clean_html.py`
  - `uv run html_to_md.py`
- outputs:
  - `cleaned_html/`
  - `markdown/`
- eval categories:
  - link conversion
  - heading preservation
  - numbering preservation
  - TOC preservation
  - list-of-tables preservation
  - list-of-figures preservation
  - code fence quality
  - JSON example reconstruction
- acceptance:
  - all required checks pass
  - targeted metric or issue count improves

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

## Immediate Next Step

Implement the generic framework locally in this repo, then configure it for the current HTML-to-Markdown project as the first real user of the framework.
