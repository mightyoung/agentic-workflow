---
name: cache
version: 1.0.0
description: |
  缓存策略 - 定义研究结果和审查结果的缓存机制
  避免重复搜索、重复审查，提升性能
tags: [core, optimization, cache]
---

# Cache Strategy

## Overview

缓存策略通过存储和复用计算结果来避免重复工作。

## 缓存类型

### 1. Research 缓存

**缓存内容**:
- 搜索查询和结果
- `.research/findings/findings_{session}.md` 内容
- 技术选型决策

**缓存键生成**:
```python
def research_cache_key(query: str, context: dict) -> str:
    """
    生成 research 缓存键

    格式: research:{hash(query + context)}
    """
    content = json.dumps({
        "query": query.lower().strip(),
        "context": sorted(context.items())
    }, sort_keys=True)
    return f"research:{hashlib.sha256(content).hexdigest()[:16]}"
```

**缓存结构**:
```markdown
## Research Cache Entry

- cache_key: research:{hash}
- query: 原始查询
- context: {项目类型, 技术栈, 约束条件}
- findings: `.research/findings/findings_{session}.md` 内容
- created_at: 时间戳
- expires_at: 过期时间 (TTL)
- hit_count: 命中次数
- source_urls: [来源链接列表]
```

### 2. Review 缓存

**缓存内容**:
- 文件审查结果
- 问题列表
- 建议列表

**缓存键生成**:
```python
def review_cache_key(file_path: str, file_hash: str) -> str:
    """
    生成 review 缓存键

    格式: review:{filepath}:{hash}
    """
    return f"review:{file_path}:{file_hash}"
```

**增量审查优化**:
```
# 完整审查 (首次)
File_A (hash_a1) → FULL REVIEW → Result_A

# 增量审查 (文件未变)
File_A (hash_a1) → CACHE HIT → Result_A (复用)

# 增量审查 (文件已变)
File_A (hash_a2) → INCREMENTAL → Result_A' (重新审查)
```

### 3. Planning 缓存

**缓存内容**:
- 任务分解结果
- 子任务结构
- 依赖关系图

**缓存键生成**:
```python
def planning_cache_key(requirements: str, constraints: dict) -> str:
    """
    生成 planning 缓存键

    格式: planning:{hash(requirements + constraints)}
    """
    content = json.dumps({
        "requirements": requirements,
        "constraints": sorted(constraints.items())
    }, sort_keys=True)
    return f"planning:{hashlib.sha256(content).hexdigest()[:16]}"
```

## 缓存接口

### CacheStore 接口

```python
class CacheStore:
    """缓存存储接口"""

    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        pass

    def set(self, key: str, entry: CacheEntry, ttl: int = 3600) -> None:
        """设置缓存条目 (TTL 单位: 秒)"""
        pass

    def invalidate(self, key: str) -> None:
        """使缓存失效"""
        pass

    def invalidate_pattern(self, pattern: str) -> None:
        """使匹配模式的缓存失效"""
        pass

    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        pass
```

### CacheEntry 结构

```python
@dataclass
class CacheEntry:
    key: str
    value: Any  # 缓存的值
    created_at: float  # Unix timestamp
    expires_at: float  # Unix timestamp
    hit_count: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> int:
        return max(0, int(self.expires_at - time.time()))
```

## TTL 管理

### TTL 配置

| 缓存类型 | 默认 TTL | 最大 TTL | 说明 |
|----------|----------|----------|------|
| Research | 24h | 168h (7天) | 技术方案相对稳定 |
| Review | 1h | 24h | 代码频繁变化 |
| Planning | 30min | 4h | 需求可能快速变化 |
| Thinking | 2h | 24h | 推理结果较稳定 |

### TTL 续期策略

```python
def refresh_ttl(cache_key: str, additional_ttl: int = None) -> bool:
    """
    续期缓存 TTL

    规则:
    - 如果 original_ttl < 1h: 续期 2x
    - 如果 original_ttl >= 1h: 续期 +30min
    - 最大不超过 max_ttl
    """
    pass
```

## 失效策略

### 失效触发条件

| 条件 | 影响范围 | 处理方式 |
|------|----------|----------|
| 文件修改 | 该文件的 review 缓存 | invalidate |
| 依赖变更 | 相关 research + planning | invalidate_pattern |
| 用户请求 | 显式指定 | invalidate |
| TTL 过期 | 单条记录 | 自动清理 |
| 存储满 | LRU淘汰 | 清理最旧条目 |

### 主动失效

```bash
# 失效特定缓存
/agentic-workflow --cache-invalidate research:{key}

/# 失效所有 research 缓存
/agentic-workflow --cache-invalidate "research:*"

/# 清除所有缓存
/agentic-workflow --cache-clear
```

## 缓存存储

### 存储位置

```
~/.gstack/cache/
├── research/          # Research 缓存
│   ├── {key}.json
│   └── index.json     # 缓存索引
├── review/           # Review 缓存
│   ├── {key}.json
│   └── index.json
├── planning/         # Planning 缓存
│   ├── {key}.json
│   └── index.json
└── metadata.json     # 全局缓存元数据
```

### 索引结构

```json
{
  "version": "1.0",
  "last_cleanup": "2026-03-21T10:00:00Z",
  "total_size_mb": 50,
  "entries": {
    "research:abc123": {
      "file": "research/abc123.json",
      "size_kb": 25,
      "created_at": "2026-03-21T09:00:00Z",
      "expires_at": "2026-03-22T09:00:00Z",
      "hit_count": 5
    }
  }
}
```

## 缓存命中率

### 统计指标

| 指标 | 说明 |
|------|------|
| hit_rate | 命中率 = hits / (hits + misses) |
| avg_ttl_remaining | 平均剩余 TTL |
| total_size | 缓存总大小 |
| entry_count | 缓存条目数 |

### 命中率报告

```bash
# 查看缓存统计
/agentic-workflow --cache-stats

# 输出示例:
# Research Cache:
#   - Entries: 42
#   - Hit Rate: 73.5%
#   - Avg TTL: 18.2h
#   - Size: 2.3MB
#
# Review Cache:
#   - Entries: 156
#   - Hit Rate: 84.2%
#   - Avg TTL: 45min
#   - Size: 1.1MB
```

## 用户可配置

```bash
# 启用缓存 (默认开启)
/agentic-workflow --cache

# 禁用缓存
/agentic-workflow --no-cache

# 设置 custom TTL
/agentic-workflow --cache-ttl research=48h

# 查看缓存状态
/agentic-workflow --cache-status
```

## 兼容性保证

### 向后兼容

- 默认启用缓存
- 缓存失效不影响正确性 (会重新计算)
- 缓存存储在独立目录，不污染项目目录

### 降级策略

如果缓存系统不可用:

1. **内存缓存**: 使用内存中的 LRU cache
2. **无缓存模式**: 直接计算，禁用缓存写入
3. **降级警告**: 提示用户缓存不可用

```python
def get_cache_backend() -> CacheStore:
    """获取可用的缓存后端"""
    if os.path.exists(CACHE_DIR):
        return FileCacheBackend(CACHE_DIR)
    elif IN_MEMORY_CACHE_AVAILABLE:
        return LRUCacheBackend(max_size=100)
    else:
        return NoOpCacheBackend()  # 降级
```
