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

If the run is driven by benchmark evidence, include a `benchmark_evidence=<path-or-id>` prefix in `notes` or export `BENCHMARK_EVIDENCE=<path-or-id>` before calling `self_improve.sh`.

The runner will:
- generate a reviewable skill proposal artifact under `knowledge/skill_proposals/`
- verify the proposal via `scripts/proposal_verifier.py`
- record both proposal and verification artifact paths in the ledger
- append a structured JSONL record to `results_v2.jsonl` alongside the TSV ledger

Default gate policy:
- `reject`: abort run initialization and record `discard`
- `revise`: also abort by default; pass `--allow-revise` only when you intentionally accept manual override
- `approve`: continue run initialization

## Principles

- Establish baseline before mutating
- One hypothesis per run
- Prefer Zone B changes before Zone A
- Roll back immediately on hard gate failure
- Record every run in the ledger
e2e test record
