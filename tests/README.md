# Tests

This directory contains both formal regression tests and exploratory benchmark helpers.

## Formal regression tests

Files named `test_*.py` in the root of this directory are part of the pytest regression suite.
They should be deterministic, isolated, and suitable for CI.

## Benchmark and exploratory analysis

- `tests/bench/` contains exploratory benchmark helpers, fixtures, and generated reports.
- `tests/run_*.py` scripts are manual or semi-manual experiment runners.
- JSON/Markdown output under `tests/*_results/` or `tests/bench/ab_experiment_results/` is evidence, not regression input.

## Guidance

- Prefer regression tests for behavior that must stay stable.
- Prefer benchmark helpers for strategy comparison and hypothesis generation.
- Do not treat benchmark helpers as authoritative production gates.
