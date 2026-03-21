---
name: AskUserQuestion
description: Standardized format for requesting user decisions during skill execution
version: 1.0.0
tags: [shared, user-interaction, decision-making]
---

# AskUserQuestion Format

## 何时使用

当 skill 需要用户做出决策时，必须使用此格式。典型场景：

- 技术方案选择（框架、库、架构）
- 优先级排序（先做 A 还是 B）
- 确认意图（是否继续当前方向）
- 资源决策（是否投入更多时间深挖）
- 方向调整（当前计划是否需要变更）

**禁止**：
- 直接询问"你怎么看"
- 只给是/否选项而无分析
- 提供过多选项（超过 4 个）
- 在紧急流程中询问非关键问题

---

## 四步标准格式

### Step 1: Re-ground

重新说明项目上下文，确保用户基于最新状态做决策。

```
## Re-ground
- **项目**: [项目名称]
- **分支**: [当前分支名]
- **当前状态**: [简述已完成的工作]
- **进行中的计划**: [当前执行的计划/任务]
```

### Step 2: Simplify

用 16 岁可理解的简单语言解释问题和核心权衡。

```
## Simplify
[用最简单的语言解释问题]
[核心权衡：如果选 A 会怎样，如果选 B 会怎样]
```

### Step 3: Recommend

给出推荐选项，说明理由，并提供 Completeness 评分。

```
## Recommend
**推荐**: [推荐选项及理由]

**Completeness 评分**:
| 评分 | 含义 | 说明 |
|------|------|------|
| 10   | 完整实现 | 覆盖所有边界情况，经过充分测试 |
| 7    | 覆盖主路径 | 覆盖主要使用场景，minor 问题可后续修复 |
| 3    | 捷径 | 快速见效但有技术债务，适合临时方案 |

**预估 Effort**:
- human: ~[用户需要投入的时间]
- CC: ~[Claude Code 消耗的 tokens/调用成本]
```

### Step 4: Options

用字母标识选项，A) B) C) 格式。

```
## Options

A) [选项 A 描述]
   - 优点: [列出关键优点]
   - 缺点: [列出关键缺点]
   - Completeness: [评分]

B) [选项 B 描述]
   - 优点: [列出关键优点]
   - 缺点: [列出关键缺点]
   - Completeness: [评分]

C) [跳过此决策，继续当前计划]
   - 理由: [为什么跳过可能是合理的]
```

---

## 示例

```markdown
## Re-ground
- **项目**: agentic-workflow
- **分支**: feature/user-auth
- **当前状态**: 完成了基础认证流程，但 Session 存储方案未定
- **进行中的计划**: 实现 JWT Refresh Token 轮转机制

## Simplify
问题是：用户登录后，access token 过期了怎么办？

**选项 A（推荐）**: 用 Refresh Token 自动续期
- 就像APP自动续会员一样，用户无感知

**选项 B**: 让用户重新登录
- 简单但体验差，用户可能流失

## Recommend
**推荐**: A) Refresh Token 方案
**理由**: 用户无感知，安全性高，符合业界最佳实践

**Completeness**: 7/10
- 主路径完整，refresh token 撤销和强制登出可后续补充

**预估 Effort**:
- human: ~15min（理解方案和做决策）
- CC: ~500 tokens

## Options

A) 实现 Refresh Token 自动续期
   - 优点: 用户体验最佳，安全性高，可精细化控制
   - 缺点: 实现复杂度稍高，需要处理并发刷新
   - Completeness: 7/10

B) 使用长期 Access Token（24h）
   - 优点: 实现简单，前端无需处理续期逻辑
   - 缺点: 安全风险更高，token 泄露影响时间长
   - Completeness: 5/10

C) 跳过此问题，先完成其他功能
   - 理由: 当前已有 basic auth 可以工作
```

---

## 最佳实践

1. **保持简洁**: Re-ground 不超过 5 行，Simplify 不超过 3 句
2. **Completeness 诚实**: 不要为了显得方案好而虚报评分
3. **选项平衡**: 选项之间应有真实权衡，避免一个选项明显最优
4. **及时使用**: 在需要决策时立即询问，不要等到积累多个问题
5. **包含上下文**: 让用户知道当前处于什么阶段、已完成什么
