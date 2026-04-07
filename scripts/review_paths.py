#!/usr/bin/env python3
"""Helpers for locating review artifacts."""

from __future__ import annotations

from pathlib import Path

REVIEW_DIR = Path(".reviews") / "review"
REVIEW_LATEST_NAME = "review_latest.md"


def review_dir(workdir: str | Path) -> Path:
    return Path(workdir) / REVIEW_DIR


def ensure_review_dir(workdir: str | Path) -> Path:
    path = review_dir(workdir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def review_session_path(workdir: str | Path, session_id: str) -> Path:
    return review_dir(workdir) / f"review_{session_id}.md"


def review_latest_path(workdir: str | Path) -> Path:
    return review_dir(workdir) / REVIEW_LATEST_NAME


def legacy_review_paths(workdir: str | Path) -> list[Path]:
    path = Path(workdir)
    return sorted(path.glob("review*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
