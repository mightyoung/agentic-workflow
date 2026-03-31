#!/usr/bin/env python3
"""
DEPRECATED: Workflow state helpers.

This module is DEPRECATED. All functionality has been moved to unified_state.py.

The unified state system (.workflow_state.json) is now the single source of truth.
This file is kept for backward compatibility only and will be removed in a future version.

Current runtime uses: unified_state.py
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

RUNTIME_STATE_FILE = ".workflow_runtime.json"
PROGRESS_FILE = "progress.md"
ALLOWED_PHASES = {
    "IDLE",
    "DIRECT_ANSWER",
    "PLANNING",
    "RESEARCH",
    "THINKING",
    "EXECUTING",
    "REVIEWING",
    "DEBUGGING",
    "COMPLETE",
}


def runtime_state_path(workdir: str = ".") -> Path:
    return Path(workdir) / RUNTIME_STATE_FILE


def progress_file_path(workdir: str = ".") -> Path:
    return Path(workdir) / PROGRESS_FILE


def template_path(name: str, workdir: str = ".") -> Path:
    return Path(workdir) / "references" / "templates" / name


def ensure_progress_file(workdir: str = ".") -> Path:
    destination = progress_file_path(workdir)
    if destination.exists():
        return destination

    source = template_path("progress.md", workdir)
    if source.exists():
        shutil.copyfile(source, destination)
    else:
        destination.write_text(
            "# Progress\n\n## Current Phase\n\n- phase: initialization\n- status: pending\n",
            encoding="utf-8",
        )
    return destination


def update_progress_file(workdir: str, phase: str, status: str, next_step: str = "") -> Path:
    destination = ensure_progress_file(workdir)
    lines = [
        "# Progress",
        "",
        "## Current Phase",
        "",
        f"- phase: {phase}",
        f"- status: {status}",
        "",
        "## Completed",
        "",
        "- [ ]",
        "",
        "## In Progress",
        "",
        f"- {next_step or 'workflow runtime updated state'}",
        "",
        "## Next",
        "",
        f"- {next_step or 'continue current phase'}",
        "",
    ]
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def load_runtime_state(workdir: str = ".") -> Dict[str, Any]:
    path = runtime_state_path(workdir)
    if not path.exists():
        return default_runtime_state()
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def default_runtime_state() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "task_id": None,
        "prompt": None,
        "trigger_type": None,
        "current_phase": "IDLE",
        "phase_history": [],
        "artifacts": {},
    }


def validate_runtime_state(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    if data.get("current_phase") not in ALLOWED_PHASES:
        errors.append(f"invalid current_phase: {data.get('current_phase')}")

    if not isinstance(data.get("phase_history", []), list):
        errors.append("phase_history must be a list")

    if not isinstance(data.get("artifacts", {}), dict):
        errors.append("artifacts must be a dict")

    if data.get("task_id") is not None and not isinstance(data.get("task_id"), str):
        errors.append("task_id must be a string or null")

    if data.get("trigger_type") is not None and data.get("trigger_type") not in {
        "DIRECT_ANSWER",
        "FULL_WORKFLOW",
        "STAGE",
    }:
        errors.append(f"invalid trigger_type: {data.get('trigger_type')}")

    phase_history = data.get("phase_history", [])
    for index, item in enumerate(phase_history):
        if not isinstance(item, dict):
            errors.append(f"phase_history[{index}] must be a dict")
            continue
        if item.get("phase") not in ALLOWED_PHASES:
            errors.append(f"phase_history[{index}] has invalid phase: {item.get('phase')}")

    return errors


def save_runtime_state(workdir: str, data: Dict[str, Any]) -> Path:
    path = runtime_state_path(workdir)
    data["updated_at"] = datetime.now().isoformat()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def append_phase_history(data: Dict[str, Any], phase: str, reason: str = "") -> None:
    data.setdefault("phase_history", []).append(
        {
            "phase": phase,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
    )
