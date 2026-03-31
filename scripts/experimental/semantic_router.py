#!/usr/bin/env python3
"""
Semantic Router - 语义路由

使用语义相似度进行路由决策:
1. 将用户输入编码为向量
2. 与 phase 描述向量计算相似度
3. 选择相似度最高的 phase
4. 可配置使用本地 Ollama 或降级到关键词匹配

用法:
    from semantic_router import SemanticRouter, route_semantic

    router = SemanticRouter()
    result = router.route("帮我搜索最佳实践")

    # 或者直接调用
    result = route_semantic("帮我搜索最佳实践")
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Optional: numpy can be used for vector operations if available
HAS_NUMPY = False


# ============================================================================
# Phase Definitions with Descriptions
# ============================================================================

@dataclass
class PhaseInfo:
    """Phase 详细信息"""
    name: str
    description: str
    keywords: List[str]  # 降级用关键词
    examples: List[str]  # 示例输入
    triggers_workflow: bool = True  # 是否触发完整工作流


PHASES: Dict[str, PhaseInfo] = {
    "ROUTER": PhaseInfo(
        name="ROUTER",
        description="路由决策 - 分析用户意图并选择合适的执行路径",
        keywords=["路由", "选择"],
        examples=["帮我选择", "应该怎么做"],
    ),
    "OFFICE-HOURS": PhaseInfo(
        name="OFFICE-HOURS",
        description="产品咨询 - 帮助用户梳理和重构产品想法，明确需求",
        keywords=["产品想法", "需求不明确", "不确定", "怎么开始", "创业", "app想法", "做个", "做一个", "想法", "构思", "主意"],
        examples=["我想做一个产品", "有个app想法", "不确定需求", "想做个"],
    ),
    "EXPLORING": PhaseInfo(
        name="EXPLORING",
        description="深度探索 - 苏格拉底式追问，探索问题本质",
        keywords=["实验", "想法", "深层", "本质", "为什么", "追问", "探索"],
        examples=["我想探索一下", "这件事的本质是什么", "为什么是这样"],
    ),
    "RESEARCH": PhaseInfo(
        name="RESEARCH",
        description="技术调研 - 搜索和分析最佳实践，收集信息",
        keywords=["搜索", "调研", "查找", "最佳实践", "参考", "案例", "选型", "部署", "数据库优化"],
        examples=["帮我搜索最佳实践", "调研一下微服务", "有什么方案"],
    ),
    "THINKING": PhaseInfo(
        name="THINKING",
        description="专家分析 - 模拟顶级专家视角进行深度分析",
        keywords=["分析", "理解", "专家", "谁最懂", "顶级", "思路", "建议", "看法", "优化"],
        examples=["分析一下", "顶级专家怎么看", "给点意见"],
    ),
    "PLANNING": PhaseInfo(
        name="PLANNING",
        description="任务规划 - 分解任务，确定步骤和优先级",
        keywords=["计划", "规划", "拆分", "设计", "安排", "步骤", "先后顺序"],
        examples=["计划一下", "如何开始", "从哪里入手"],
    ),
    "EXECUTING": PhaseInfo(
        name="EXECUTING",
        description="代码实现 - TDD驱动，执行任务",
        keywords=["写", "实现", "开发", "创建", "编写", "开发"],
        examples=["帮我写一个函数", "实现这个功能", "开发一个模块"],
    ),
    "REVIEWING": PhaseInfo(
        name="REVIEWING",
        description="代码审查 - 检查代码质量、安全、性能",
        keywords=["审查", "review", "审计", "检查", "代码审查"],
        examples=["帮我review代码", "审查一下这段代码", "代码审查"],
    ),
    "DEBUGGING": PhaseInfo(
        name="DEBUGGING",
        description="调试修复 - 定位和修复问题",
        keywords=["调试", "修复", "bug", "错误", "报错", "崩溃", "失败", "问题", "修复"],
        examples=["帮我调试", "程序崩溃了", "运行报错", "修复这个bug"],
    ),
    "REFINING": PhaseInfo(
        name="REFINING",
        description="迭代精炼 - 基于反馈进行优化",
        keywords=["迭代", "优化", "精炼", "改进", "反馈", "完善"],
        examples=["优化一下", "需要改进", "迭代这个功能"],
    ),
    "COMPLETE": PhaseInfo(
        name="COMPLETE",
        description="完成阶段 - 验证和总结",
        keywords=["完成", "总结", "结束"],
        examples=["完成了", "总结一下"],
    ),
}


# ============================================================================
# Embedding Provider (支持多种后端)
# ============================================================================

class EmbeddingProvider(Enum):
    """嵌入向量提供者"""
    OLLAMA = "ollama"        # 本地 Ollama
    OPENAI = "openai"        # OpenAI API
    SIMPLE = "simple"       # 简单词向量 (无需外部服务)


EmbedBackend = EmbeddingProvider  # Alias for backward compatibility


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    embedding: List[float]
    provider: EmbeddingProvider
    model: str
    tokens: int = 0


class EmbeddingGenerator:
    """
    嵌入向量生成器

    支持多种后端，按优先级尝试:
    1. Ollama (本地)
    2. OpenAI API
    3. 简单词向量 (降级)
    """

    def __init__(self, provider: str = "auto"):
        self.provider_name = provider
        self._client = None
        self._init_provider()

    def _init_provider(self):
        """初始化提供者"""
        if self.provider_name == "ollama" or self.provider_name == "auto":
            if self._check_ollama():
                self.provider = EmbedBackend.OLLAMA
                return

        if self.provider_name == "openai" or self.provider_name == "auto":
            if os.getenv("OPENAI_API_KEY"):
                self.provider = EmbedBackend.OPENAI
                return

        # 默认降级到简单实现
        self.provider = EmbedBackend.SIMPLE

    def _check_ollama(self) -> bool:
        """检查 Ollama 是否可用"""
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def embed(self, text: str, model: str = "nomic-embed-text") -> EmbeddingResult:
        """
        生成文本嵌入向量

        Args:
            text: 输入文本
            model: 模型名称

        Returns:
            EmbeddingResult
        """
        if self.provider == EmbedBackend.OLLAMA:
            return self._embed_ollama(text, model)
        elif self.provider == EmbedBackend.OPENAI:
            return self._embed_openai(text, model)
        else:
            return self._embed_simple(text)

    def _embed_ollama(self, text: str, model: str) -> EmbeddingResult:
        """使用 Ollama 生成嵌入"""
        import urllib.request
        import urllib.error

        payload = {"model": model, "prompt": text}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            "http://localhost:11434/api/embeddings",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return EmbeddingResult(
                    embedding=result["embedding"],
                    provider=EmbedBackend.OLLAMA,
                    model=model,
                    tokens=result.get("tokens", 0),
                )
        except urllib.error.URLError as e:
            print(f"Ollama error: {e}, falling back to simple")
            return self._embed_simple(text)

    def _embed_openai(self, text: str, model: str) -> EmbeddingResult:
        """使用 OpenAI API 生成嵌入"""
        import urllib.request
        import urllib.error

        api_key = os.getenv("OPENAI_API_KEY")
        payload = {"input": text, "model": model}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return EmbeddingResult(
                    embedding=result["data"][0]["embedding"],
                    provider=EmbedBackend.OPENAI,
                    model=model,
                    tokens=result.get("usage", {}).get("total_tokens", 0),
                )
        except urllib.error.URLError as e:
            print(f"OpenAI error: {e}, falling back to simple")
            return self._embed_simple(text)

    def _embed_simple(self, text: str) -> EmbeddingResult:
        """
        简单词向量实现 (TF-IDF 风格)

        无需外部服务，使用词频统计
        """
        # 停用词
        stop_words = {
            "的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "什么"
        }

        # 分词 (简单按字符)
        words = [w for w in text if len(w) > 1 and w not in stop_words]

        # 统计词频
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        # TF-IDF 风格向量 (取前 100 个词)
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:100]

        # 构建向量 (使用词汇表索引)
        vocab = {w: i for i, (w, _) in enumerate(sorted_words)}
        dim = 128
        vec = [0.0] * dim

        for w, count in sorted_words:
            if w in vocab:
                idx = vocab[w] % dim
                vec[idx] = count / len(words)  # TF

        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return EmbeddingResult(
            embedding=vec,
            provider=EmbedBackend.SIMPLE,
            model="simple-tf",
        )


# ============================================================================
# Semantic Similarity
# ============================================================================

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def euclidean_distance(a: List[float], b: List[float]) -> float:
    """计算欧氏距离"""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ============================================================================
# Semantic Router
# ============================================================================

@dataclass
class RouteResult:
    """路由结果"""
    trigger_type: str  # FULL_WORKFLOW, STAGE, DIRECT_ANSWER
    phase: str
    confidence: float  # 0.0 - 1.0
    all_scores: Dict[str, float] = field(default_factory=dict)  # 所有 phase 得分
    provider: str = "unknown"
    method: str = "semantic"  # semantic 或 keyword


class SemanticRouter:
    """
    语义路由器

    功能:
    - 语义嵌入相似度匹配
    - 关键词降级匹配
    - 置信度计算
    - 缓存 phase 嵌入
    """

    # 负面触发关键词
    NEGATIVE_TRIGGERS = [
        "天气", "笑话", "你好", "谢谢", "嗨", "嘿", "干嘛呢", "最近怎样",
        "hi", "hello", "bye", "ok", "yes", "no", "maybe"
    ]

    # 直接回答模式
    DIRECT_ANSWER_PATTERNS = [
        r"^给个?\s*?(笑话|故事|谜语)",
        r"^(今天|明天|昨天)\s*?(天气|怎么样)",
        r"^你是\s*?(谁|什么)",
        r"^(hi|hello|hey|嗨|你好)",
    ]

    # 强制触发词
    FORCE_TRIGGERS = [
        "/agentic-workflow", "继续", "继续下一步", "继续任务",
        "下一步", "继续进行", "继续执行", "接着来", "继续做"
    ]

    def __init__(
        self,
        embedding_provider: str = "auto",
        cache_dir: str = ".semantic_cache",
        confidence_threshold: float = 0.3,
    ):
        self.embedding_provider = EmbeddingGenerator(embedding_provider)
        self.cache_dir = Path(cache_dir)
        self.confidence_threshold = confidence_threshold
        self._phase_embeddings: Dict[str, EmbeddingResult] = {}
        self._keyword_scores: Dict[str, int] = {}

        # 预计算 phase 嵌入
        self._init_phase_embeddings()

    def _init_phase_embeddings(self):
        """初始化 phase 嵌入向量"""
        # 构建 phase 描述文本
        for name, phase in PHASES.items():
            # 组合描述 + 关键词 + 示例
            combined_text = f"{phase.description}。关键词: {', '.join(phase.keywords)}。示例: {', '.join(phase.examples)}"

            # 尝试从缓存加载
            cache_file = self.cache_dir / f"{name}.json"
            if cache_file.exists():
                try:
                    data = json.loads(cache_file.read_text())
                    self._phase_embeddings[name] = EmbeddingResult(
                        embedding=data["embedding"],
                        provider=data["provider"],
                        model=data["model"],
                    )
                    continue
                except Exception:
                    pass

            # 生成嵌入
            result = self.embedding_provider.embed(combined_text)
            self._phase_embeddings[name] = result

            # 保存到缓存
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps({
                    "embedding": result.embedding,
                    "provider": result.provider.value,
                    "model": result.model,
                }))
            except Exception:
                pass

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 去除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        return text.strip()

    def _check_negative(self, text: str) -> bool:
        """检查负面触发"""
        text_lower = text.lower()

        # 检查负面关键词
        for neg in self.NEGATIVE_TRIGGERS:
            if neg in text_lower:
                return True

        # 检查模式
        for pattern in self.DIRECT_ANSWER_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        return False

    def _check_force(self, text: str) -> Optional[str]:
        """检查强制触发"""
        for trigger in self.FORCE_TRIGGERS:
            if trigger in text:
                return "FULL_WORKFLOW"
        return None

    def _compute_keyword_scores(self, text: str) -> Dict[str, float]:
        """计算关键词匹配分数"""
        text_lower = text.lower()
        scores = {}

        for name, phase in PHASES.items():
            score = 0.0
            matched_keywords = []

            for keyword in phase.keywords:
                if keyword in text_lower:
                    score += len(keyword)  # 更长的关键词权重更高
                    matched_keywords.append(keyword)

            for example in phase.examples:
                if example in text_lower:
                    score += len(example) * 0.8
                    matched_keywords.append(example)

            # 归一化分数
            scores[name] = score / max(len(text_lower), 1)

        return scores

    def _semantic_route(self, text: str) -> RouteResult:
        """
        语义路由

        Returns:
            RouteResult with confidence scores
        """
        preprocessed = self._preprocess_text(text)

        # 生成用户输入嵌入
        user_embedding = self.embedding_provider.embed(preprocessed)

        # 计算与所有 phase 的相似度
        scores = {}
        for name, phase_emb in self._phase_embeddings.items():
            sim = cosine_similarity(user_embedding.embedding, phase_emb.embedding)
            scores[name] = sim

        # 归一化分数
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}

        # 找出最高分
        best_phase = max(scores.items(), key=lambda x: x[1])
        best_name = best_phase[0]
        best_conf = best_phase[1]

        # 降级到关键词匹配如果语义置信度太低
        keyword_scores = self._compute_keyword_scores(text)
        max_keyword = max(keyword_scores.items(), key=lambda x: x[1]) if keyword_scores else ("", 0)

        # 如果关键词匹配更好，使用关键词结果
        if max_keyword[1] > best_conf * 0.5 and max_keyword[1] > 0.1:
            return RouteResult(
                trigger_type="STAGE",
                phase=max_keyword[0] or "EXECUTING",
                confidence=max_keyword[1],
                all_scores={**scores, **keyword_scores},
                provider=user_embedding.provider.value,
                method="keyword",
            )

        return RouteResult(
            trigger_type="STAGE",
            phase=best_name,
            confidence=best_conf,
            all_scores=scores,
            provider=user_embedding.provider.value,
            method="semantic",
        )

    def _keyword_route(self, text: str) -> RouteResult:
        """关键词路由 (降级方案)"""
        scores = self._compute_keyword_scores(text)

        if not scores or max(scores.values()) < 0.01:
            return RouteResult(
                trigger_type="STAGE",
                phase="EXECUTING",  # 默认
                confidence=0.1,
                all_scores=scores,
                provider="none",
                method="keyword",
            )

        best = max(scores.items(), key=lambda x: x[1])
        return RouteResult(
            trigger_type="STAGE",
            phase=best[0],
            confidence=min(best[1] * 10, 1.0),  # 放大但不超过1
            all_scores=scores,
            provider="none",
            method="keyword",
        )

    def route(self, text: str) -> RouteResult:
        """
        执行路由决策

        Args:
            text: 用户输入

        Returns:
            RouteResult
        """
        # Step 1: 负面触发检查
        if self._check_negative(text):
            return RouteResult(
                trigger_type="DIRECT_ANSWER",
                phase="闲聊",
                confidence=1.0,
                all_scores={},
                provider="none",
                method="keyword",
            )

        # Step 2: 强制触发检查
        force = self._check_force(text)
        if force:
            return RouteResult(
                trigger_type="FULL_WORKFLOW",
                phase="完整流程",
                confidence=1.0,
                all_scores={},
                provider="none",
                method="keyword",
            )

        # Step 3: 尝试语义路由
        if self.embedding_provider.provider != EmbedBackend.SIMPLE:
            try:
                result = self._semantic_route(text)
                if result.confidence >= self.confidence_threshold:
                    return result
                # 置信度不够，尝试关键词
            except Exception as e:
                print(f"Semantic routing failed: {e}, falling back to keyword")

        # Step 4: 降级到关键词路由
        return self._keyword_route(text)

    def get_all_scores(self, text: str) -> Dict[str, float]:
        """获取所有 phase 的得分"""
        result = self.route(text)
        return result.all_scores


# ============================================================================
# Convenience Functions
# ============================================================================

# 全局路由器实例
_global_router: Optional[SemanticRouter] = None


def get_router() -> SemanticRouter:
    """获取全局路由器实例"""
    global _global_router
    if _global_router is None:
        _global_router = SemanticRouter()
    return _global_router


def route_semantic(text: str) -> Tuple[str, str]:
    """
    语义路由便捷函数

    Returns:
        (trigger_type, phase)
    """
    router = get_router()
    result = router.route(text)
    return (result.trigger_type, result.phase)


def route_with_confidence(text: str) -> RouteResult:
    """带置信度的路由结果"""
    router = get_router()
    return router.route(text)


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Semantic Router - 语义路由")
    parser.add_argument("--text", help="要路由的文本")
    parser.add_argument("--provider", choices=["auto", "ollama", "openai", "simple"], default="auto")
    parser.add_argument("--threshold", type=float, default=0.3, help="置信度阈值")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--scores", action="store_true", help="显示所有 phase 得分")
    args = parser.parse_args()

    router = SemanticRouter(embedding_provider=args.provider, confidence_threshold=args.threshold)

    if args.text:
        text = args.text
    else:
        print("输入要路由的文本 (Ctrl+C 退出):")
        text = input("\n> ")

    result = router.route(text)

    if args.verbose or args.scores:
        print("\n路由结果:")
        print(f"  触发类型: {result.trigger_type}")
        print(f"  Phase: {result.phase}")
        print(f"  置信度: {result.confidence:.3f}")
        print(f"  方法: {result.method}")
        print(f"  Provider: {result.provider}")

        if args.scores:
            print("\n所有 Phase 得分:")
            sorted_scores = sorted(result.all_scores.items(), key=lambda x: x[1], reverse=True)
            for phase, score in sorted_scores[:10]:
                bar = "█" * int(score * 20)
                print(f"  {phase:15s}: {score:.3f} {bar}")

    else:
        if result.trigger_type == "DIRECT_ANSWER":
            print(f"DIRECT_ANSWER | {result.phase} | NO_WORKFLOW")
        elif result.trigger_type == "FULL_WORKFLOW":
            print(f"FULL_WORKFLOW | {result.phase} | WORKFLOW")
        else:
            print(f"STAGE | {result.phase} | WORKFLOW (confidence: {result.confidence:.2f})")


if __name__ == "__main__":
    raise SystemExit(main())
