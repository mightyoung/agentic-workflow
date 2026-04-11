#!/usr/bin/env python3
"""Proposal registry for benchmark-driven skill evolution.

This registry is event-sourced: each proposal transition is appended as a JSONL
event. That keeps the history auditable without mutating prior records.
"""

from __future__ import annotations

import argparse
import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INDEX_PATH = Path("knowledge/skill_proposals/index.jsonl")

VALID_STATUSES = {
    "generated",
    "verified",
    "approved",
    "revised",
    "blocked",
    "discarded",
    "applied",
    "rolled_back",
}

ALLOWED_TRANSITIONS = {
    None: {"generated"},
    "generated": {"verified", "revised", "blocked", "discarded"},
    "verified": {"approved", "revised", "blocked", "discarded"},
    "revised": {"verified", "approved", "blocked", "discarded", "applied"},
    "approved": {"applied", "rolled_back", "discarded"},
    "blocked": {"discarded"},
    "discarded": set(),
    "applied": {"rolled_back"},
    "rolled_back": set(),
}


def _now_stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None
    normalized = str(status).strip().lower()
    return normalized or None


def _load_events(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        with index_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return events


def _latest_event(events: list[dict[str, Any]], proposal_id: str) -> dict[str, Any] | None:
    for event in reversed(events):
        if str(event.get("proposal_id", "")).strip() == proposal_id:
            return event
    return None


def _ensure_parent(index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)


def _validate_transition(previous: str | None, current: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(previous)
    if allowed is None:
        raise ValueError(f"unsupported previous status: {previous!r}")
    if current not in allowed:
        raise ValueError(f"invalid proposal status transition: {previous!r} -> {current!r}")


def record_proposal_event(
    *,
    proposal_id: str,
    status: str,
    event_type: str,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    source_reference: str | None = None,
    benchmark_version: str | None = None,
    proposal_path: str | None = None,
    verification_path: str | None = None,
    decision: str | None = None,
    run_id: str | None = None,
    hypothesis: str | None = None,
    benchmark_evidence: str | None = None,
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a proposal lifecycle event and return the recorded payload."""
    normalized_status = _normalize_status(status)
    if normalized_status not in VALID_STATUSES:
        raise ValueError(f"invalid proposal status: {status!r}")

    index = Path(index_path)
    _ensure_parent(index)
    events = _load_events(index)
    latest = _latest_event(events, proposal_id)
    previous_status = _normalize_status(latest.get("status")) if latest else None
    _validate_transition(previous_status, normalized_status)

    record = {
        "schema_version": 1,
        "recorded_at": _now_stamp(),
        "proposal_id": proposal_id,
        "event_type": event_type,
        "status": normalized_status,
        "source_reference": source_reference,
        "benchmark_version": benchmark_version,
        "proposal_path": proposal_path,
        "verification_path": verification_path,
        "decision": decision,
        "run_id": run_id,
        "hypothesis": hypothesis,
        "benchmark_evidence": benchmark_evidence,
        "notes": notes,
        "metadata": metadata or {},
    }

    lock_path = str(index) + ".lock"
    with open(lock_path, "w", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            with index.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
    try:
        Path(lock_path).unlink(missing_ok=True)
    except OSError:
        pass

    return record


def get_latest_proposal_state(
    proposal_id: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> dict[str, Any] | None:
    events = _load_events(Path(index_path))
    return _latest_event(events, proposal_id)


def render_summary(event: dict[str, Any] | None) -> str:
    if not event:
        return "no proposal events found"
    pieces = [
        f"proposal_id={event.get('proposal_id')}",
        f"status={event.get('status')}",
        f"event_type={event.get('event_type')}",
    ]
    if event.get("decision"):
        pieces.append(f"decision={event.get('decision')}")
    if event.get("benchmark_version"):
        pieces.append(f"benchmark_version={event.get('benchmark_version')}")
    if event.get("run_id"):
        pieces.append(f"run_id={event.get('run_id')}")
    return " | ".join(pieces)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append or inspect proposal lifecycle events.")
    parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH), help="JSONL index path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="append a proposal event")
    record.add_argument("--proposal-id", required=True)
    record.add_argument("--status", required=True)
    record.add_argument("--event-type", required=True)
    record.add_argument("--source-reference")
    record.add_argument("--benchmark-version")
    record.add_argument("--proposal-path")
    record.add_argument("--verification-path")
    record.add_argument("--decision")
    record.add_argument("--run-id")
    record.add_argument("--hypothesis")
    record.add_argument("--benchmark-evidence")
    record.add_argument("--notes")
    record.add_argument("--metadata-json", default="{}")

    latest = subparsers.add_parser("latest", help="show latest event for a proposal")
    latest.add_argument("--proposal-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    index_path = Path(args.index_path)

    if args.command == "record":
        try:
            metadata = json.loads(args.metadata_json)
        except json.JSONDecodeError:
            metadata = {}
        event = record_proposal_event(
            proposal_id=args.proposal_id,
            status=args.status,
            event_type=args.event_type,
            index_path=index_path,
            source_reference=args.source_reference,
            benchmark_version=args.benchmark_version,
            proposal_path=args.proposal_path,
            verification_path=args.verification_path,
            decision=args.decision,
            run_id=args.run_id,
            hypothesis=args.hypothesis,
            benchmark_evidence=args.benchmark_evidence,
            notes=args.notes,
            metadata=metadata,
        )
        print(json.dumps(event, ensure_ascii=False))
        return 0

    if args.command == "latest":
        event = get_latest_proposal_state(args.proposal_id, index_path=index_path)
        print(json.dumps(event or {}, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
