#!/usr/bin/env python3
"""
Memory Graph Index — 因果图与实体图轻量实现

MAGMA (arXiv 2601.03236) 代理实现:
- Causal Graph: 从 Reflexion 格式 experience 解析因果链，建倒排索引
- Entity Graph: 从 experience 文本提取文件/模块实体，建倒排索引

这两个索引对 .memory_index.jsonl 的结构化条目进行二次索引，
支持意图感知检索中的 debug/review 模式精准召回。

用法:
    from scripts.memory_graph_index import (
        build_causal_index, search_causal,
        build_entity_index, search_entity,
        rebuild_all_indexes,
    )
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

# ── 默认文件路径 ────────────────────────────────────────────────────────────
MEMORY_INDEX_FILE = ".memory_index.jsonl"
MEMORY_CAUSAL_FILE = ".memory_causal_index.json"
MEMORY_ENTITY_FILE = ".memory_entity_index.json"


# ── Reflexion 格式解析 (Causal Graph) ──────────────────────────────────────

def parse_reflexion_entry(text: str) -> dict[str, str]:
    """解析 Reflexion 格式 experience 的各字段。

    支持格式: Task:X Trigger:Y Mistake:Z Fix:W Signal:S
    字段顺序不限，大小写不限。

    Returns:
        dict 含 task/trigger/mistake/fix/signal 键（有值时），缺失字段不包含
    """
    fields: dict[str, str] = {}
    keys = ("task", "trigger", "mistake", "fix", "signal")
    # Build alternation for lookahead boundary
    boundary = "|".join(k + ":" for k in keys)
    for key in keys:
        pattern = rf'(?i){key}:(.+?)(?=\s+(?:{boundary})|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value:
                fields[key] = value
    return fields


def build_causal_index(
    index_file: str = MEMORY_INDEX_FILE,
    causal_file: str = MEMORY_CAUSAL_FILE,
) -> dict:
    """从 .memory_index.jsonl 全量重建因果索引。

    索引结构:
        {
          "version": 1,
          "signals":  {"modulenotfounderror": [{"id":..., "fix":...}, ...]},
          "triggers": {"import error":         [{"id":..., "fix":...}, ...]},
          "_built": "YYYY-MM-DD",
          "_total": N
        }

    Returns:
        构建的索引 dict（同时写入 causal_file）
    """
    signals: dict[str, list[dict]] = {}
    triggers: dict[str, list[dict]] = {}
    total = 0

    if os.path.exists(index_file):
        try:
            with open(index_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    text = entry.get("text", "")
                    fields = parse_reflexion_entry(text)
                    if not fields:
                        continue

                    entry_id = entry.get("id", "")
                    fix_snippet = fields.get("fix", "")[:120]
                    record = {"id": entry_id, "fix": fix_snippet, "text": text[:200]}

                    if fields.get("signal"):
                        key = fields["signal"].lower()[:80]
                        signals.setdefault(key, []).append(record)
                        total += 1

                    if fields.get("trigger"):
                        key = fields["trigger"].lower()[:80]
                        triggers.setdefault(key, []).append(record)
        except OSError:
            pass

    index = {
        "version": 1,
        "signals": signals,
        "triggers": triggers,
        "_built": datetime.now().strftime("%Y-%m-%d"),
        "_total": total,
    }

    try:
        with open(causal_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return index


def search_causal(
    query: str,
    causal_file: str = MEMORY_CAUSAL_FILE,
    limit: int = 5,
) -> list[dict]:
    """在因果索引中搜索：匹配 Signal 和 Trigger 字段。

    用于 DEBUGGING 阶段：给定错误信息 → 找到已知的修复方案。

    Returns:
        匹配的 record 列表（含 id/fix/text），按 Signal 精确匹配优先
    """
    if not os.path.exists(causal_file):
        return []

    try:
        with open(causal_file, encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    query_lower = query.lower()
    results: list[dict] = []
    seen_ids: set[str] = set()

    # Priority 1: Signal exact/substring match (error message → fix)
    for signal_key, records in index.get("signals", {}).items():
        if query_lower in signal_key or signal_key in query_lower:
            for r in records:
                if r["id"] not in seen_ids:
                    results.append({**r, "_match_field": "signal", "_matched_key": signal_key})
                    seen_ids.add(r["id"])

    # Priority 2: Trigger substring match
    for trigger_key, records in index.get("triggers", {}).items():
        if query_lower in trigger_key or trigger_key in query_lower:
            for r in records:
                if r["id"] not in seen_ids:
                    results.append({**r, "_match_field": "trigger", "_matched_key": trigger_key})
                    seen_ids.add(r["id"])

    return results[:limit]


# ── Entity 提取与实体索引 (Entity Graph) ───────────────────────────────────

_ENTITY_PATTERN = re.compile(
    r'\b([\w/.-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|cpp|c|h|sh|md))\b'
    r'|(?<!\w)((?:src|scripts|tests|lib|pkg|cmd|internal)/[\w/.-]+)\b',
    re.IGNORECASE,
)


def extract_entities(text: str) -> list[str]:
    """从 experience 文本提取文件/模块实体引用。

    匹配规则:
    - 文件名含扩展名: auth.py, memory_longterm.py, App.tsx
    - 目录前缀路径: src/auth, scripts/workflow_engine, tests/test_auth
    """
    entities: set[str] = set()
    for m in _ENTITY_PATTERN.finditer(text):
        # group(1): file with extension; group(2): path-prefixed module
        val = (m.group(1) or m.group(2) or "").lower().strip("/").strip(".")
        if val and len(val) > 2:
            entities.add(val)
    return list(entities)


def build_entity_index(
    index_file: str = MEMORY_INDEX_FILE,
    entity_file: str = MEMORY_ENTITY_FILE,
) -> dict:
    """从 .memory_index.jsonl 全量重建实体索引。

    索引结构:
        {
          "version": 1,
          "entities": {
            "auth.py": [{"id":..., "snippet":...}, ...],
            "src/auth": [...]
          },
          "_built": "YYYY-MM-DD",
          "_total": N
        }

    Returns:
        构建的索引 dict（同时写入 entity_file）
    """
    entities: dict[str, list[dict]] = {}
    total = 0

    if os.path.exists(index_file):
        try:
            with open(index_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    text = entry.get("text", "")
                    found = extract_entities(text)
                    if not found:
                        continue

                    entry_id = entry.get("id", "")
                    snippet = text[:150]
                    for ent in found:
                        record = {"id": entry_id, "snippet": snippet}
                        entities.setdefault(ent, []).append(record)
                    total += 1
        except OSError:
            pass

    index = {
        "version": 1,
        "entities": entities,
        "_built": datetime.now().strftime("%Y-%m-%d"),
        "_total": total,
    }

    try:
        with open(entity_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return index


def search_entity(
    entity: str,
    entity_file: str = MEMORY_ENTITY_FILE,
    limit: int = 5,
) -> list[dict]:
    """在实体索引中查找与某文件/模块相关的历史经验。

    用于 REVIEWING 阶段：给定文件名 → 找到该文件的历史问题记录。

    Returns:
        匹配的 record 列表（含 id/snippet），按精确匹配优先
    """
    if not os.path.exists(entity_file):
        return []

    try:
        with open(entity_file, encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    query_lower = entity.lower()
    results: list[dict] = []
    seen_ids: set[str] = set()

    # Exact key match first
    if query_lower in index.get("entities", {}):
        for r in index["entities"][query_lower]:
            if r["id"] not in seen_ids:
                results.append({**r, "_matched_entity": query_lower})
                seen_ids.add(r["id"])

    # Partial key match (e.g. "auth" matches "auth.py" and "src/auth")
    for ent_key, records in index.get("entities", {}).items():
        if query_lower != ent_key and (query_lower in ent_key or ent_key in query_lower):
            for r in records:
                if r["id"] not in seen_ids:
                    results.append({**r, "_matched_entity": ent_key})
                    seen_ids.add(r["id"])

    return results[:limit]


# ── Convenience ─────────────────────────────────────────────────────────────

def rebuild_all_indexes(
    index_file: str = MEMORY_INDEX_FILE,
    causal_file: str = MEMORY_CAUSAL_FILE,
    entity_file: str = MEMORY_ENTITY_FILE,
) -> tuple[int, int]:
    """重建因果索引和实体索引。

    Returns:
        (causal_total, entity_total)
    """
    ci = build_causal_index(index_file, causal_file)
    ei = build_entity_index(index_file, entity_file)
    return ci.get("_total", 0), ei.get("_total", 0)
