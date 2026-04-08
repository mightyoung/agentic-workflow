---
name: agentic-workflow
description: |
  智能体工作流：单入口设计，所有任务从 router 开始
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施
  DO NOT TRIGGER when: 简单闲聊
version: 6.3.0
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow v6.3

## 工作流触发与路由

| 用户关键词 | 路由到阶段 |
|---|---|
| "bug"/"错误"/"修复" | **DEBUGGING** |
| "计划"/"拆分"/"规划" | **PLANNING** |
| "最佳实践"/"怎么做"/"如何" | **RESEARCH** |
| "审查"/"review"/"质量" | **REVIEWING** |
| "优化"/"迭代"/"精炼" | **REFINING** |
| "试验"/"想法"/"探索" | **EXPLORING** |
| 多模块/多文件任务 | **FULL_WORKFLOW** |
| "继续"/"resume"/"恢复" | 读 `.workflow_state.json` 恢复上下文 |

## FULL_WORKFLOW 强制阶段序列

按复杂度自动选择最小必经阶段（**禁止跳过**）：

| 复杂度 | 示例 | 必经阶段 |
|---|---|---|
| **XS** | 改 typo、加 import | EXECUTING → COMPLETE |
| **S** | 修已知 bug | DEBUGGING → EXECUTING → COMPLETE |
| **M** | 新增 API | PLANNING → EXECUTING → REVIEWING → COMPLETE |
| **L** | 重构模块 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE |
| **XL** | 设计新系统 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → REFINING → COMPLETE |

## 进度输出 (必须执行)

每进入新阶段时输出：
```
[N/M PHASE] 一句话描述当前目标
```

阶段完成时输出：
```
[N/M PHASE ✓] 一句话总结产出
```

## 阶段上下文传递 (必须执行)

| 当前阶段 | 下一阶段 | 必读内容 |
|---|---|---|
| RESEARCH | THINKING | 读 `.research/findings/findings_{session}.md`（优先）或 `.research/findings/findings_latest.md` |
| THINKING | PLANNING | 先读当前 phase 上下文里的 `memory_hints` / `memory_query` / `memory_intent`，再基于分析结论拆分任务，生成 `.specs/<feature>/spec.md / plan.md / tasks.md / .contract.json` |
| PLANNING | EXECUTING | 逐项执行 `.specs/<feature>/tasks.md`；如有 `memory_hints`，优先复用历史失败模式与约束；`task_plan.md` 仅在 legacy 兼容场景投影 |
| EXECUTING | REVIEWING | 运行 `git diff` 查看代码变更，必要时参考 `memory_hints` 避免重复踩已知失败模式，并更新 `.contract.json` |
| REVIEWING | REFINING | 针对 issues 逐项修复，先检查 `memory_hints` / `memory_query` / `memory_intent`，再产出 `.reviews/review/review_{session}.md` |

## 核心原则 (铁律，不可违反)

1. **穷尽一切** — 没穷尽 3 个方案前禁止说"无法解决"
2. **先做后问** — 遇到问题先搜索/读源码/验证，再提问
3. **主动出击** — 端到端交付，不只是"刚好够用"

## 禁止响应

以下响应明确禁止，遇到立即停止并重新分析：

| 禁止语句 | 原因 | 正确做法 |
|---|---|---|
| "我认为完成了" | 无证据声明 | 运行测试/`git diff`，给出证据 |
| "代码看起来不错" | REVIEWING 无实质内容 | 输出含 `file:line` 的具体意见 |
| "跳过 X 阶段直接做 Y" | 违反强制序列 | 按照强制阶段序列执行 |
| "根据我的知识..." (RESEARCH) | 跳过真实搜索 | 先执行 WebSearch；工具不可用时明确告知用户 |

## 搜索工具优先级 (RESEARCH 阶段自动降级)

1. **WebSearch** — Claude Code 原生（优先使用）
2. **WebFetch** — 当已知具体 URL 时
3. **工具都不可用** → **必明确告知用户**"搜索不可用，使用已有知识"，禁止静默降级

## 阶段切换命令

```bash
# 推进到下一阶段
python3 scripts/workflow_engine.py --op advance --phase {NEXT_PHASE} --workdir .

# 查看当前状态
python3 scripts/workflow_engine.py --op status --workdir .
```

## Runtime 边界

- `scripts/workflow_engine.py` 是唯一权威 runtime
- `scripts/middleware.py` 目前仅用于实验和对照验证
- `scripts/experimental/` 已归档，不作为可执行主线的一部分
- 这些原型不得替代主线的 state / artifact / contract / checkpoint 管线

## 关键文件约定

- `.workflow_state.json` — 唯一可信的状态文件
- `.specs/<feature>/spec.md` — 需求与验收标准
- `.specs/<feature>/plan.md` — 技术方案与约束
- `.specs/<feature>/tasks.md` — 执行任务清单
- `.contract.json` — 履约契约（COMPLETE 门禁）
- `task_plan.md` — legacy 兼容投影，仅在旧 runtime 需要时使用
- `.research/findings/findings_{session}.md` — RESEARCH 输出的研究结果（THINKING 必读，目录版）
- `.research/findings/findings_latest.md` — 最近一次研究结果的便捷别名
- `.reviews/review/review_{session}.md` — REVIEWING 输出的审查意见（REFINING 必读，目录版）
- `.reviews/review/review_latest.md` — 最近一次审查结果的便捷别名

## 禁止引用的过时文件

- `~/.gstack` — 历史设计
- 假设 telemetry daemon、preload 或 session 守护进程存在

## 兼容侧边车

- `SESSION-STATE.md` — 仍由 `memory_ops.py` 维护，作为兼容 sidecar，不是权威状态源
- `progress.md` — 兼容进度侧边车，由 workflow runtime 同步

## Iron Law

```
NO PHASE SKIP — FULL_WORKFLOW 触发时禁止跳过任何必经阶段
NO FIX WITHOUT ROOT CAUSE — DEBUGGING 时禁止在未确认根因前修改代码
NO COMPLETE WITHOUT VERIFICATION — 禁止在未运行验证命令前声称任务完成
```

## Red Flags（自我检查）

| 想法 | 现实 |
|------|------|
| "这是个简单问题，直接回答" | 简单问题也可能需要 DEBUGGING/REVIEWING |
| "先做再说，做完再计划" | PLANNING 在 EXECUTING 之前，顺序不可颠倒 |
| "用户没说要走完整流程" | FULL_WORKFLOW 触发词见上表，不需要用户显式声明 |
| "我已经知道答案了" | 先验证，再声称完成 |
| "REVIEWING 可以快速过一遍" | REVIEWING 必须运行 git diff + quality_gate + pytest |

## 验证前禁止完成

宣称任务完成之前，必须：
1. 运行相关测试（pytest / npm test）并看到通过结果
2. 对于代码变更：运行 `git diff` 确认实际变更
3. 对于 REVIEWING：输出含具体 file:line 的审查意见

无证据 = 未完成。不得仅凭"我认为完成了"声称完成。

---

## 阶段专用指南

### DEBUGGING 调试流程

**铁律**: 不定位根因不修复

**执行步骤**:
1. **收集症状** - 错误信息/堆栈/复现步骤
2. **追踪代码** - 从症状反向追踪可能原因
3. **假设验证** - 小范围验证假设,不对就回退
4. **3次失败规则** - 3次假设都错→可能是架构问题

**3次失败规则**: 3次假设都错时,停止惯性调试:
- (a) 用新假设描述继续
- (b) 升级人工review
- (c) 添加日志/埋点等下次复现

**输出格式**:
```
症状: ...
根因: ...
修复: ...
回归测试: ...
```

### REVIEWING 代码审查

**优先级排序**:

**P0 (致命)**:
- 安全漏洞: SQL注入/命令注入/XSS/认证绕过
- 数据泄露: 敏感信息硬编码/日志输出
- 崩溃风险: 空指针/并发问题/资源泄露

**P1 (严重)**:
- 逻辑错误: 边界条件/错误处理/事务问题
- 性能问题: N+1查询/大循环/内存泄漏

**P2 (建议)**:
- 代码风格: 命名/格式/注释
- 可维护性: 重复代码/过长函数

**输出格式**:
```
[文件:行号] 问题描述 (P0/P1/P2)
影响: [一句话]
修复: [建议]
```

**自我检验**:
- [ ] 是否因"能跑"而忽略了设计问题?
- [ ] 是否使用了"可能"、"或许"等模糊词?
- [ ] 是否只改了表面没改根因?

**时间限制**: 如果审查超过20秒无发现,输出已有结果并停止

### PLANNING 任务规划

**复杂度路由**:
- XS/S: 用TodoWrite拆分任务,不需要spec文件
- M: 产出spec.md + tasks.md
- L/XL: 产出spec.md + plan.md + tasks.md + .contract.json

**核心原则**: 不只拆分任务,要生成多种方案

**执行**:
1. 明确目标 - 一句话说清
2. 生成方案 - 2-3种(最小/折中/理想)
3. 推荐 - 明确推荐哪个,为什么

**反模式**: 禁止为XS/S生成完整spec-kit,禁止强制验证脚本

### EXECUTING 执行

**铁律**: 先写测试再实现,先验证再声称完成

**Boil the Lake原则**: 完整性与AI能力成正比,不要省步骤

**Fix-First决策**:
- AUTO-FIX: 机械性问题(typo, import, 格式化)→直接修复
- ASK: 判断性问题(架构, 设计)→先问用户

**Voice规则**:
- 禁止: em dashes, "delve/crucial/robust"等AI词汇
- 使用: 具体file:line引用,简洁动词

**执行步骤**:
1. 写失败的测试
2. 写最小代码通过
3. 重构优化

**验证**: 运行测试确认,不要只说"完成了".

### RESEARCH 搜索研究

**阶段方法论**:
1. 广泛探索 - 快速扫描多个来源
2. 深度挖掘 - 聚焦权威来源
3. 综合验证 - 检查一致性

**Quality Gate**: 自问"能自信回答吗?"
- 如果NO→继续研究
- 如果YES→输出结论

**执行**:
1. 搜索: 具体技术名词+"best practices"
2. 深度获取: 不只看摘要,要fetch完整内容
3. 来源优先级: 官方文档>开源>博客>AI生成
4. 输出: 关键发现+3条内可操作建议+来源

**铁律**: 搜索不可用时直接说明,禁止静默降级

**时间感知**: 检查当前日期,趋势用年月

### THINKING 专家推理

**核心**: 谁最懂这个?TA会怎么说?

**Mandatory Think**: 重大决策(git操作,阶段转换)前必须思考

**回答格式**:
- 本质: [一句话]
- 权衡: [最多3观点,各20字]
- 建议: [1个明确建议]
