# Benchmark Helpers

This directory contains exploratory benchmark helpers and their generated reports.

## What belongs here

- `run_ab_comparison.py` and similar scripts used for manual or semi-manual A/B analysis
- JSON/Markdown outputs produced by those scripts
- curated benchmark fixtures and task packs

## What does not belong here

- normal pytest regression tests
- runtime source code
- production decision logic

## Guidance

- Use the benchmark outputs as evidence for strategy decisions.
- Do not treat benchmark helpers as authoritative CI gates.
- When a benchmark result drives a self-improvement run, attach the report path to the run notes.
