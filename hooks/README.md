# hooks/ — Claude Code 自动观测钩子

本目录包含 Claude Code hook 脚本，实现 **100% 可靠的行为观测**
（相比 skill 加载的 ~50-80% 可靠性，hooks 在每次工具调用时都会触发）。

## 钩子说明

| 文件 | 触发时机 | 作用 |
|------|---------|------|
| `observe.sh` | PreToolUse | 记录工具调用到 `.observations.jsonl` |
| `evaluate-session.sh` | Stop | 会话结束时提取模式并写入长期记忆 |

## 启用方法

在项目的 `.claude/settings.json` 中添加：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash hooks/observe.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash hooks/evaluate-session.sh"
          }
        ]
      }
    ]
  }
}
```

## 数据文件

- `.observations.jsonl` — 本会话工具调用记录（自动轮转保留最近 1000 条）
- `.memory_index.jsonl` — 结构化长期记忆索引（由 `memory_longterm.py` 维护）
- `MEMORY.md` — 人类可读的长期记忆汇总

## 隐私

钩子只记录工具名称和时间戳，**不记录工具输入内容**（避免泄露敏感信息）。
