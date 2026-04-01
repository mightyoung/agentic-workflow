#!/usr/bin/env python3
"""
Context Manager - 上下文重置与恢复

借鉴 Anthropic Harness Design 的上下文管理最佳实践:

1. Context Reset
   - 当上下文过长时重置
   - 保留关键决策和待办事项

2. Handoff Artifacts
   - 结构化的交接文档
   - 供后续 Agent 使用

用法:
    from context_manager import ContextManager, ContextCheckpoint

    cm = ContextManager(workdir)
    checkpoint = cm.create_checkpoint(phase, trajectory)
    cm.save_checkpoint(checkpoint)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# Context Checkpoint
# ============================================================================

@dataclass
class ContextCheckpoint:
    """上下文检查点"""
    checkpoint_id: str
    phase: str
    session_id: str
    accomplished: List[str]  # 已完成的工作
    pending_work: List[str]  # 待完成的工作
    key_decisions: List[str]  # 关键决策
    artifacts: Dict[str, str]  # 关键产物路径
    context_summary: str  # 上下文摘要
    token_estimate: int  # 估计的 token 数
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "phase": self.phase,
            "session_id": self.session_id,
            "accomplished": self.accomplished,
            "pending_work": self.pending_work,
            "key_decisions": self.key_decisions,
            "artifacts": self.artifacts,
            "context_summary": self.context_summary,
            "token_estimate": self.token_estimate,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextCheckpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            phase=data["phase"],
            session_id=data["session_id"],
            accomplished=data.get("accomplished", []),
            pending_work=data.get("pending_work", []),
            key_decisions=data.get("key_decisions", []),
            artifacts=data.get("artifacts", {}),
            context_summary=data.get("context_summary", ""),
            token_estimate=data.get("token_estimate", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


# ============================================================================
# Handoff Document
# ============================================================================

@dataclass
class HandoffDocument:
    """交接文档"""
    checkpoint_id: str
    for_phase: str  # 即将进入的 phase
    summary: str
    accomplished: List[str]
    pending_work: List[str]
    key_decisions: List[str]
    context_for_next_agent: str  # 给下一个 Agent 的上下文

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [
            f"# Handoff Document - {self.checkpoint_id}",
            "",
            f"**即将进入**: {self.for_phase}",
            f"**时间**: {datetime.now().isoformat()}",
            "",
            "## 摘要",
            self.summary,
            "",
            "## 已完成",
        ]
        for item in self.accomplished:
            lines.append(f"- [x] {item}")

        lines.extend(["", "## 待完成"])
        for item in self.pending_work:
            lines.append(f"- [ ] {item}")

        lines.extend(["", "## 关键决策"])
        for decision in self.key_decisions:
            lines.append(f"- {decision}")

        lines.extend(["", "## 上下文 (给下一个 Agent)", self.context_for_next_agent])

        return "\n".join(lines)


# ============================================================================
# Context Manager
# ============================================================================

class ContextManager:
    """
    上下文管理器

    功能:
    - 创建检查点
    - 重置上下文
    - 生成交接文档
    - 恢复上下文
    """

    # Token 估计 (中文字符约 2 tokens, 英文约 0.75 tokens)
    CHARS_PER_TOKEN = 2.5
    DEFAULT_MAX_TOKENS = 150000  # 150k tokens 上限

    def __init__(
        self,
        workdir: str = ".",
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        self.workdir = Path(workdir)
        self.max_tokens = max_tokens
        self.checkpoint_dir = self.workdir / ".checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)

    def estimate_tokens(self, text: str) -> int:
        """估计文本的 token 数"""
        return int(len(text) / self.CHARS_PER_TOKEN)

    def should_reset(self, trajectory: List[Dict[str, Any]], current_context: str) -> bool:
        """
        检查是否应该重置上下文

        Args:
            trajectory: 轨迹历史
            current_context: 当前上下文

        Returns:
            True if reset recommended
        """
        token_estimate = self.estimate_tokens(current_context)

        # 超过上限
        if token_estimate >= self.max_tokens:
            return True

        # 轨迹过长
        if len(trajectory) >= 100:
            return True

        # 每 50 步建议重置
        if len(trajectory) % 50 == 0 and len(trajectory) > 0:
            return True

        return False

    def create_checkpoint(
        self,
        phase: str,
        session_id: str,
        trajectory: List[Dict[str, Any]],
        current_context: str,
        accomplishments: Optional[List[str]] = None,
    ) -> ContextCheckpoint:
        """
        创建检查点

        Args:
            phase: 当前 phase
            session_id: 会话 ID
            trajectory: 轨迹历史
            current_context: 当前上下文
            accomplishments: 已完成的工作 (可选)

        Returns:
            ContextCheckpoint
        """
        # 从轨迹提取已完成的工作
        if accomplishments is None:
            accomplishments = self._extract_accomplishments(trajectory)

        # 提取待完成的工作
        pending = self._extract_pending_work(trajectory)

        # 提取关键决策
        decisions = self._extract_key_decisions(trajectory)

        # 提取关键产物
        artifacts = self._extract_artifacts(trajectory)

        # 生成摘要
        summary = self._generate_summary(phase, trajectory, current_context)

        checkpoint_id = f"cp_{len(trajectory)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return ContextCheckpoint(
            checkpoint_id=checkpoint_id,
            phase=phase,
            session_id=session_id,
            accomplished=accomplishments,
            pending_work=pending,
            key_decisions=decisions,
            artifacts=artifacts,
            context_summary=summary,
            token_estimate=self.estimate_tokens(current_context),
        )

    def save_checkpoint(self, checkpoint: ContextCheckpoint) -> Dict[str, Any]:
        """
        保存检查点

        Returns:
            {"success": bool, "path": str, "error": str | None}
        """
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            from safe_io import safe_write_json
        except ImportError:
            # Fallback if safe_io not available
            path = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            try:
                path.write_text(json.dumps(checkpoint.to_dict(), ensure_ascii=False, indent=2))
                return {"success": True, "path": str(path), "error": None}
            except Exception as e:
                return {"success": False, "path": "", "error": str(e)}

        path = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        try:
            safe_write_json(path, checkpoint.to_dict())
            return {"success": True, "path": str(path), "error": None}
        except Exception as e:
            return {"success": False, "path": "", "error": str(e)}

    def load_checkpoint(self, checkpoint_id: str) -> Optional[ContextCheckpoint]:
        """加载检查点"""
        path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return ContextCheckpoint.from_dict(data)

    def create_handoff(
        self,
        checkpoint: ContextCheckpoint,
        next_phase: str,
    ) -> HandoffDocument:
        """
        创建交接文档

        Args:
            checkpoint: 检查点
            next_phase: 下一个 phase

        Returns:
            HandoffDocument
        """
        context_for_next = self._build_agent_context(checkpoint, next_phase)

        return HandoffDocument(
            checkpoint_id=checkpoint.checkpoint_id,
            for_phase=next_phase,
            summary=checkpoint.context_summary,
            accomplished=checkpoint.accomplished,
            pending_work=checkpoint.pending_work,
            key_decisions=checkpoint.key_decisions,
            context_for_next_agent=context_for_next,
        )

    def reset_and_resume(
        self,
        checkpoint: ContextCheckpoint,
    ) -> Dict[str, Any]:
        """
        重置并恢复

        创建精简的上下文用于继续执行

        Returns:
            恢复所需的初始状态
        """
        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "phase": checkpoint.phase,
            "session_id": checkpoint.session_id,
            "pending_work": checkpoint.pending_work,
            "key_decisions": checkpoint.key_decisions,
            "artifacts": checkpoint.artifacts,
            "context_for_resume": self._build_agent_context(checkpoint, checkpoint.phase),
        }

    def _extract_accomplishments(self, trajectory: List[Dict[str, Any]]) -> List[str]:
        """从轨迹提取已完成的工作"""
        accomplishments = []
        for entry in trajectory:
            if entry.get("status") == "completed":
                phase = entry.get("phase", "unknown")
                accomplished = entry.get("accomplished", [])
                if accomplished:
                    accomplishments.extend(accomplished)
                else:
                    accomplishments.append(f"完成 {phase}")
        return accomplishments

    def _extract_pending_work(self, trajectory: List[Dict[str, Any]]) -> List[str]:
        """从轨迹提取待完成的工作"""
        pending = []
        for entry in trajectory:
            if entry.get("status") in ("pending", "in_progress"):
                phase = entry.get("phase", "unknown")
                pending.append(f"继续 {phase}")
        return pending

    def _extract_key_decisions(self, trajectory: List[Dict[str, Any]]) -> List[str]:
        """从轨迹提取关键决策"""
        decisions = []
        for entry in trajectory:
            decisions.extend(entry.get("decisions", []))
        return decisions[-10:]  # 只保留最近 10 个

    def _extract_artifacts(self, trajectory: List[Dict[str, Any]]) -> Dict[str, str]:
        """从轨迹提取关键产物"""
        artifacts = {}
        for entry in trajectory:
            artifacts.update(entry.get("artifacts", {}))
        return artifacts

    def _generate_summary(
        self,
        phase: str,
        trajectory: List[Dict[str, Any]],
        current_context: str,
    ) -> str:
        """生成上下文摘要"""
        phases_completed: List[str] = [e.get("phase", "") for e in trajectory if e.get("status") == "completed" and e.get("phase")]

        summary_parts = [
            f"当前 Phase: {phase}",
            f"已完成 Phases: {', '.join(phases_completed) if phases_completed else '无'}",
            f"轨迹步数: {len(trajectory)}",
            f"估计 Token: {self.estimate_tokens(current_context)}",
        ]

        return "\n".join(summary_parts)

    def _build_agent_context(
        self,
        checkpoint: ContextCheckpoint,
        next_phase: str,
    ) -> str:
        """为下一个 Agent 构建上下文"""
        context_parts = [
            f"# 继续工作 - Phase: {next_phase}",
            "",
            "## 背景",
            f"Session: {checkpoint.session_id}",
            f"Checkpoint: {checkpoint.checkpoint_id}",
            "",
            "## 已完成",
        ]

        for item in checkpoint.accomplished[-5:]:  # 最近 5 个
            context_parts.append(f"- {item}")

        context_parts.extend(["", "## 待完成"])
        for item in checkpoint.pending_work[:5]:  # 前 5 个
            context_parts.append(f"- {item}")

        if checkpoint.key_decisions:
            context_parts.extend(["", "## 关键决策"])
            for decision in checkpoint.key_decisions[-3:]:
                context_parts.append(f"- {decision}")

        context_parts.extend(["", "## 关键产物"])
        for artifact_path in list(checkpoint.artifacts.values())[:3]:
            context_parts.append(f"- {artifact_path}")

        return "\n".join(context_parts)


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Context Manager - 上下文管理")
    parser.add_argument("--workdir", default=".", help="工作目录")
    parser.add_argument("--op", choices=["check", "checkpoint", "list", "load", "reset"], required=True)
    parser.add_argument("--checkpoint-id", help="检查点 ID")
    parser.add_argument("--phase", help="当前 phase")
    parser.add_argument("--session-id", help="会话 ID")
    parser.add_argument("--trajectory", help="轨迹文件 (JSON)")
    parser.add_argument("--context", help="当前上下文文件")
    parser.add_argument("--next-phase", help="下一个 phase (用于生成 handoff)")
    args = parser.parse_args()

    cm = ContextManager(args.workdir)

    if args.op == "check":
        # 检查是否需要重置
        trajectory = json.loads(Path(args.trajectory).read_text()) if args.trajectory else []
        context = Path(args.context).read_text() if args.context else ""

        should = cm.should_reset(trajectory, context)
        token_estimate = cm.estimate_tokens(context)

        print(json.dumps({
            "should_reset": should,
            "token_estimate": token_estimate,
            "max_tokens": cm.max_tokens,
            "trajectory_length": len(trajectory),
        }, indent=2))

    elif args.op == "checkpoint":
        # 创建检查点
        trajectory = json.loads(Path(args.trajectory).read_text()) if args.trajectory else []
        context = Path(args.context).read_text() if args.context else ""

        checkpoint = cm.create_checkpoint(
            phase=args.phase or "UNKNOWN",
            session_id=args.session_id or "unknown",
            trajectory=trajectory,
            current_context=context,
        )

        result = cm.save_checkpoint(checkpoint)
        if result["success"]:
            print(f"检查点已保存: {result['path']}")
            print(json.dumps(checkpoint.to_dict(), indent=2))
        else:
            print(f"检查点保存失败: {result['error']}")
            return 1

    elif args.op == "list":
        # 列出所有检查点
        checkpoints = list(cm.checkpoint_dir.glob("*.json"))
        print(f"检查点数: {len(checkpoints)}")
        for cp in checkpoints:
            data = json.loads(cp.read_text())
            print(f"  - {data['checkpoint_id']} [{data['phase']}] @ {data['created_at']}")

    elif args.op == "load":
        # 加载检查点
        checkpoint = cm.load_checkpoint(args.checkpoint_id)
        if checkpoint:
            print(json.dumps(checkpoint.to_dict(), indent=2))
        else:
            print(f"检查点未找到: {args.checkpoint_id}")

    elif args.op == "reset":
        # 重置并恢复
        checkpoint = cm.load_checkpoint(args.checkpoint_id)
        if not checkpoint:
            print(f"检查点未找到: {args.checkpoint_id}")
            return 1

        result = cm.reset_and_resume(checkpoint)

        # 生成 handoff 文档
        handoff = cm.create_handoff(checkpoint, args.next_phase or checkpoint.phase)

        handoff_path = cm.workdir / f"handoff_{checkpoint.checkpoint_id}.md"
        handoff_path.write_text(handoff.to_markdown())

        print(f"重置完成: {handoff_path}")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
