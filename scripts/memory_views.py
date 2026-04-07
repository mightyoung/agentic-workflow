#!/usr/bin/env python3
"""
Memory Views - MAGMA Multi-View Memory Retrieval

Implements the four memory views described in MAGMA (arXiv 2601.03236):
- Semantic View: topic/keyword-based clustering
- Temporal View: time-organized recall with decay
- Causal View: Signal → Fix chains (from memory_graph_index)
- Entity View: file/module → history (from memory_graph_index)

Usage:
    from memory_views import (
        search_views,
        SemanticView,
        TemporalView,
    )

    # Unified multi-view search
    results = search_views("implement auth", intent="plan", limit=5)
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────
MEMORY_INDEX_FILE = ".memory_index.jsonl"
CAUSAL_INDEX_FILE = ".memory_causal_index.json"
ENTITY_INDEX_FILE = ".memory_entity_index.json"
SEMANTIC_INDEX_FILE = ".memory_semantic_index.json"
TEMPORAL_INDEX_FILE = ".memory_temporal_index.json"

# MAGMA temporal decay λ=0.95/day
TEMPORAL_DECAY_LAMBDA: float = 0.95


# ── Semantic View ────────────────────────────────────────────────────────────

def _extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract top keywords from text using frequency analysis.

    Filters out stopwords and short tokens.
    """
    stopwords = {
        "the", "a", "an", "of", "and", "in", "on", "for", "to", "is", "this",
        "that", "with", "as", "at", "by", "from", "or", "be", "are", "was",
        "were", "been", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "shall", "can",
        "的", "了", "和", "是", "在", "我", "有", "个", "等", "以", "对", "为",
        "与", "或", "及", "包括", "什么", "如何", "怎么", "哪些", "一个",
    }
    tokens = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    freq: dict[str, int] = defaultdict(int)
    for token in tokens:
        if token not in stopwords:
            freq[token] += 1
    sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in sorted_tokens[:top_n]]


def build_semantic_index(
    index_file: str = MEMORY_INDEX_FILE,
    semantic_file: str = SEMANTIC_INDEX_FILE,
) -> dict[str, Any]:
    """Build semantic index from memory entries.

    Groups entries by keyword clusters.
    """
    keyword_to_entries: dict[str, list[dict]] = defaultdict(list)
    entry_keywords: dict[str, list[str]] = {}

    if os.path.exists(index_file):
        with open(index_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_id = entry.get("id", "")
                text = entry.get("text", "")
                keywords = _extract_keywords(text)
                entry_keywords[entry_id] = keywords

                for kw in keywords[:5]:  # Top 5 keywords per entry
                    keyword_to_entries[kw].append({
                        "id": entry_id,
                        "snippet": text[:100],
                        "confidence": entry.get("confidence", 0.5),
                    })

    index = {
        "version": 1,
        "keywords": dict(keyword_to_entries),
        "entry_keywords": entry_keywords,
        "_built": datetime.now().strftime("%Y-%m-%d"),
    }

    try:
        with open(semantic_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return index


def search_semantic(
    query: str,
    semantic_file: str = SEMANTIC_INDEX_FILE,
    limit: int = 5,
) -> list[dict]:
    """Search semantic view by keyword match."""
    if not os.path.exists(semantic_file):
        return []

    try:
        with open(semantic_file, encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    query_keywords = set(_extract_keywords(query, top_n=8))
    results: list[tuple[int, dict]] = []

    for kw in query_keywords:
        if kw in index.get("keywords", {}):
            for entry_ref in index["keywords"][kw]:
                results.append((len(query_keywords & set([kw])), entry_ref))

    results.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    filtered = []
    for score, ref in results:
        if ref["id"] not in seen:
            seen.add(ref["id"])
            filtered.append({**ref, "_match_score": score, "_matched_keyword": kw})
        if len(filtered) >= limit:
            break

    return filtered


# ── Temporal View ─────────────────────────────────────────────────────────────

def build_temporal_index(
    index_file: str = MEMORY_INDEX_FILE,
    temporal_file: str = TEMPORAL_INDEX_FILE,
) -> dict[str, Any]:
    """Build temporal index from memory entries.

    Organizes entries by date with temporal decay weighting.
    """
    entries_by_date: dict[str, list[dict]] = defaultdict(list)

    if os.path.exists(index_file):
        with open(index_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                timestamp = entry.get("timestamp", "")
                if timestamp:
                    # Use month as bucket for broader temporal grouping
                    month_key = timestamp[:7]  # YYYY-MM
                    entries_by_date[month_key].append({
                        "id": entry.get("id", ""),
                        "text": entry.get("text", "")[:150],
                        "confidence": entry.get("confidence", 0.5),
                        "timestamp": timestamp,
                    })

    index = {
        "version": 1,
        "entries_by_month": dict(entries_by_date),
        "_built": datetime.now().strftime("%Y-%m-%d"),
    }

    try:
        with open(temporal_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return index


def search_temporal(
    query: str,
    temporal_file: str = TEMPORAL_INDEX_FILE,
    limit: int = 5,
    months_back: int = 6,
) -> list[dict]:
    """Search temporal view for recent entries matching query."""
    if not os.path.exists(temporal_file):
        return []

    try:
        with open(temporal_file, encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    query_lower = query.lower()
    now = datetime.now()
    results: list[tuple[float, dict]] = []

    for month_key, entries in index.get("entries_by_month", {}).items():
        try:
            month_date = datetime.strptime(month_key, "%Y-%m")
            days_old = max(0, (now - month_date).days)
            decay = TEMPORAL_DECAY_LAMBDA ** (days_old / 30.0)  # Monthly decay
        except ValueError:
            decay = 0.1

        for entry in entries:
            if query_lower in entry.get("text", "").lower():
                score = decay * entry.get("confidence", 0.5)
                results.append((score, {**entry, "_decay": decay, "_month": month_key}))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


# ── Unified Multi-View Search ────────────────────────────────────────────────

def search_views(
    query: str,
    intent: str = "auto",
    limit: int = 5,
    rebuild: bool = False,
) -> dict[str, list[dict]]:
    """Unified multi-view search across all four MAGMA memory views.

    Args:
        query: Search query string
        intent: "auto" | "debug" | "plan" | "review"
            - debug: causal + temporal优先
            - plan: semantic + entity优先
            - review: entity + causal优先
        limit: Max results per view
        rebuild: Whether to rebuild indexes first

    Returns:
        Dict with keys: semantic, temporal, causal, entity
        Each value is a list of matching entries with metadata.
    """
    # Rebuild indexes if requested
    if rebuild:
        try:
            build_semantic_index()
        except Exception:
            pass
        try:
            build_temporal_index()
        except Exception:
            pass
        try:
            from memory_graph_index import rebuild_all_indexes
            rebuild_all_indexes()
        except Exception:
            pass

    # Resolve intent
    resolved_intent = intent
    if intent == "auto":
        q = query.lower()
        if any(k in q for k in ("error", "fail", "bug", "fix", "trigger")):
            resolved_intent = "debug"
        elif any(k in q for k in ("pattern", "implement", "build", "create", "add")):
            resolved_intent = "plan"
        elif any(k in q for k in (".py", ".ts", ".js", "src/", "file")):
            resolved_intent = "review"

    results: dict[str, list[dict]] = {
        "semantic": [],
        "temporal": [],
        "causal": [],
        "entity": [],
    }

    # Semantic view (always search)
    semantic_hits = search_semantic(query, limit=limit)
    results["semantic"] = semantic_hits

    # Temporal view (always search)
    temporal_hits = search_temporal(query, limit=limit)
    results["temporal"] = temporal_hits

    # Causal view (debug intent + when available)
    if resolved_intent == "debug" or intent == "auto":
        try:
            from memory_graph_index import search_causal
            causal_hits = search_causal(query, limit=limit)
            results["causal"] = [
                {**h, "_view": "causal"} for h in causal_hits
            ]
        except Exception:
            pass

    # Entity view (review intent + when available)
    if resolved_intent == "review" or intent == "auto":
        try:
            from memory_graph_index import search_entity
            entity_hits = search_entity(query, limit=limit)
            results["entity"] = [
                {**h, "_view": "entity"} for h in entity_hits
            ]
        except Exception:
            pass

    return results


def get_view_summary() -> dict[str, Any]:
    """Get summary of what's indexed in each view."""
    summary: dict[str, Any] = {
        "semantic": {"available": False, "keywords": 0, "entries": 0},
        "temporal": {"available": False, "months": 0, "entries": 0},
        "causal": {"available": False, "signals": 0, "triggers": 0},
        "entity": {"available": False, "entities": 0},
    }

    # Semantic
    if os.path.exists(SEMANTIC_INDEX_FILE):
        try:
            with open(SEMANTIC_INDEX_FILE, encoding="utf-8") as f:
                idx = json.load(f)
            summary["semantic"] = {
                "available": True,
                "keywords": len(idx.get("keywords", {})),
                "entries": len(idx.get("entry_keywords", {})),
                "built": idx.get("_built", "unknown"),
            }
        except (OSError, json.JSONDecodeError):
            pass

    # Temporal
    if os.path.exists(TEMPORAL_INDEX_FILE):
        try:
            with open(TEMPORAL_INDEX_FILE, encoding="utf-8") as f:
                idx = json.load(f)
            by_month = idx.get("entries_by_month", {})
            total_entries = sum(len(v) for v in by_month.values())
            summary["temporal"] = {
                "available": True,
                "months": len(by_month),
                "entries": total_entries,
                "built": idx.get("_built", "unknown"),
            }
        except (OSError, json.JSONDecodeError):
            pass

    # Causal (from memory_graph_index)
    if os.path.exists(CAUSAL_INDEX_FILE):
        try:
            with open(CAUSAL_INDEX_FILE, encoding="utf-8") as f:
                idx = json.load(f)
            summary["causal"] = {
                "available": True,
                "signals": len(idx.get("signals", {})),
                "triggers": len(idx.get("triggers", {})),
                "total": idx.get("_total", 0),
                "built": idx.get("_built", "unknown"),
            }
        except (OSError, json.JSONDecodeError):
            pass

    # Entity (from memory_graph_index)
    if os.path.exists(ENTITY_INDEX_FILE):
        try:
            with open(ENTITY_INDEX_FILE, encoding="utf-8") as f:
                idx = json.load(f)
            summary["entity"] = {
                "available": True,
                "entities": len(idx.get("entities", {})),
                "total": idx.get("_total", 0),
                "built": idx.get("_built", "unknown"),
            }
        except (OSError, json.JSONDecodeError):
            pass

    return summary


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Memory Views - MAGMA Multi-View Memory")
    parser.add_argument("--op", choices=["search", "build", "summary"], required=True)
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--intent", default="auto", choices=["auto", "debug", "plan", "review"])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    if args.op == "search":
        results = search_views(args.query, intent=args.intent, limit=args.limit, rebuild=args.rebuild)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.op == "build":
        s = build_semantic_index()
        t = build_temporal_index()
        print(json.dumps({
            "semantic": {"keywords": len(s.get("keywords", {})), "entries": len(s.get("entry_keywords", {}))},
            "temporal": {"months": len(t.get("entries_by_month", {})), "entries": sum(len(v) for v in t.get("entries_by_month", {}).values())},
        }, ensure_ascii=False, indent=2))
    elif args.op == "summary":
        print(json.dumps(get_view_summary(), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
