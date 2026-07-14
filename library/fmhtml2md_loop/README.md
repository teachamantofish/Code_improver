# Improvement Framework

This directory contains a generic, project-local framework for iterative code improvement.

The core entry point is:

```bash
uv run improve.py status
```

Common commands:

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

This framework is generic by design. To reuse it in another repo, keep `improve.py` and the directory structure, then replace:

- `runner_commands`
- `eval_commands`
- `tasks`
- acceptance policy

The current config is specialized for this HTML-to-Markdown project.
