# Self-Improvement Artifacts

This directory contains the self-improvement program artifacts for the agentic-workflow harness.

## Files

- `results.tsv` - Ledger of improvement runs (hypothesis, files changed, outcome)
- `baseline_check.sh` - Pre-mutation baseline validation script
- `zones.md` - Protected core vs mutable surface definitions

## Usage

Before any self-improvement run:

```bash
.self-improvement/baseline_check.sh
```

After the run, record outcome:

```bash
# Append to results.tsv
run_id=<timestamp> hypothesis=<what> files_changed=<paths> checks_passed=<summary> status=<keep|discard|rollback> notes=<details>
```

## Principles

- Establish baseline before mutating
- One hypothesis per run
- Prefer Zone B changes before Zone A
- Roll back immediately on hard gate failure
- Record every run in the ledger
