# Claude-MEM 集成

> 使用 claude-mem 进行长期记忆存储和检索

## 规划前检索

在开始任务前，检索是否有相关经验：

```python
# 使用 memory_search 工具
memory_search(query=当前任务描述, namespace=agentic-workflow)
```

### 检索示例

```
query: "用户认证系统设计"
namespace: "agentic-workflow"
```

## 完成后存储

任务完成后，存储经验以便后续复用：

```python
memory_store(
    key=任务名,
    value=经验总结,
    namespace=agentic-workflow,
    tags=["认证", "安全", "JWT"]
)
```

### 存储示例

```python
memory_store(
    key="电商支付流程优化",
    value="""
    1. 问题：支付回调并发导致重复扣款
    2. 解决：使用分布式锁+幂等设计
    3. 经验：第三方支付必须做幂等
    """,
    namespace="agentic-workflow"
)
```

## 命名空间约定

| 命名空间 | 用途 |
|---------|------|
| agentic-workflow | 工作流方法论 |
| debugging | 调试经验 |
| architecture | 架构决策 |
| tools | 工具使用经验 |

## 检索技巧

1. **使用具体关键词**：越具体结果越准确
2. **限定命名空间**：缩小搜索范围
3. **设置阈值**：threshold=0.3-0.5

## 注意事项

- 存储时包含足够的上下文
- 提取关键要点，便于后续检索
- 定期清理过时经验
