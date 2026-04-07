#!/usr/bin/env python3
"""Helpers for locating research findings artifacts."""

from __future__ import annotations

from pathlib import Path

FINDINGS_DIR = Path(".research") / "findings"
FINDINGS_LATEST_NAME = "findings_latest.md"


def findings_dir(workdir: str | Path) -> Path:
    return Path(workdir) / FINDINGS_DIR


def ensure_findings_dir(workdir: str | Path) -> Path:
    path = findings_dir(workdir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def findings_session_path(workdir: str | Path, session_id: str) -> Path:
    return findings_dir(workdir) / f"findings_{session_id}.md"


def findings_latest_path(workdir: str | Path) -> Path:
    return findings_dir(workdir) / FINDINGS_LATEST_NAME


def legacy_findings_paths(workdir: str | Path) -> list[Path]:
    path = Path(workdir)
    return sorted(path.glob("findings*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
