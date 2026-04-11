<!-- tier:50% -->

## 完整 Triage 流程

### Step 0.5: Reflexion 检索 — 读取历史反思

> 对标 Reflexion (arXiv 2303.11366)：在开始调试前，先检索本项目过去的同类错误反思，避免重复踩坑。

```bash
# 层 1: 因果图检索 — 错误信号 → 已知修复方案（MAGMA Causal Graph 代理）
python3 scripts/memory_longterm.py \
  --op search-causal \
  --query "${错误信号，如: ModuleNotFoundError / TypeError unsupported |}" \
  --limit 3 2>/dev/null || true

# 层 2: 全量意图检索（包含因果图 + 结构化索引 + MEMORY.md fallback）
python3 scripts/memory_longterm.py \
  --op search \
  --query "${问题关键词，如: import error / type annotation / contract gate}" \
  --intent debug \
  --limit 3 2>/dev/null || true
```

**处理规则**：
- `search-causal` 有命中 → Fix 字段即为已验证解决方案，直接参考，跳过相同失败路径
- `search` 有命中 → 在 Step 1 分析中优先考虑历史教训
- 两者均无结果 → 正常进入 Step 1，调试结束后在 Step 5.5 写入新反思

### Step 1: 闻味道 (Sense the Problem)

强制自动诊断 — 进入 DEBUGGING 时必须先执行以下命令收集信息：

```bash
git diff HEAD~3 --stat
git log --oneline -5
python3 -m pytest --tb=long -q 2>&1 | tail -50
python3 -m ruff check . 2>&1 | head -20 || true
```

操作：
1. 收集错误信息（错误消息、堆栈跟踪、返回码）— 必须从上述命令输出中提取
2. 复现问题（确认问题可重现）
3. 确定问题域（前端/后端/数据库/网络/配置）
4. 评估紧急程度和影响范围

压力升级：1次失败 → 继续 Step 2；2次失败 → 切换策略；3次失败 → 深度分析模式

### Step 2: 揪头发 (Root Cause Analysis)

操作：5Why 分析法、鱼骨图（人机料法环测）、差异分析（正常 vs 异常）、假设验证

**假设驱动调查协议 (ACH) — 7步：**
1. 理解假设 — 明确假设成立的条件
2. 定义证据标准 — 确认证据 vs 否定证据 vs 模糊证据
3. 收集直接证据 — 搜索代码路径、数据流、配置
4. 收集支持证据 — 相关错误、日志、相似 bug
5. 测试假设 — 构建最小复现场景
6. 评估置信度 — High(>80%) / Medium(50-80%) / Low(<50%)
7. 报告发现 — 包含因果链和证据引用

### Step 3: 照镜子 (Self Reflection)

**7项检查清单**：

| # | 检查项 | 检查内容 |
|---|--------|----------|
| 1 | 日志检查 | 是否有足够的日志定位问题？日志级别是否合适？ |
| 2 | 边界检查 | 边界条件是否正确处理？空值、极值、并发？ |
| 3 | 并发检查 | 是否有竞态条件？锁的使用是否正确？ |
| 4 | 资源检查 | 是否有资源泄漏？连接池、内存、文件句柄？ |
| 5 | 配置检查 | 配置是否正确加载？环境变量是否到位？ |
| 6 | 依赖检查 | 依赖版本是否兼容？API 是否变更？ |
| 7 | 环境检查 | 不同环境下行为是否一致？ |

### Step 4.5: Simple-Failure Downgrade

- 单文件、低依赖、错误信息明确 → 优先 `0% / 25%`
- 多文件联动、失败历史重复、根因不清 → 升到 `50%`
- 只有高价值疑难缺陷才进入完整上下文调试

### Step 4: 执行 (Execute — Fix and Verify)

操作：
1. 制定修复方案（最小修改原则）
2. 实施修复（遵循 immutable 原则）
3. 编写/更新测试用例
4. 执行测试验证
5. 交叉验证（其他测试是否受影响）

**Boil the Lake**：修复必须包含完整测试覆盖，不能只修表面，避免引入新的技术债务。

### Step 5: 复盘 (Review)

操作：记录问题根因和修复方案、提取可复用模式、识别预防措施、更新检查清单

### Step 5.5: Reflexion Entry — 写入语言反思

> 对标 Reflexion (arXiv 2303.11366)：每次调试结束后生成结构化 verbal 反思，存入长期记忆。

反思格式：
```
当 [具体触发场景/错误类型] 时，
我错误地 [具体错误行为/错误假设]。
正确做法应该是 [正确行为]，
因为 [根本原因]。
下次遇到 [关键识别特征] 应立即 [正确行动]。
```

写入命令：
```bash
python3 scripts/memory_longterm.py \
  --op add-experience \
  --exp "Task:[问题类型] Trigger:[触发场景] Mistake:[错误行为] Fix:[正确做法] Signal:[识别特征]" \
  --confidence 0.7 \
  --scope project
```

**何时可以跳过**：DONE 状态且问题极简单（typo 级别）→ 可跳过；其他情况一律写入。

---

## 调试激活档位上下文

| 档位 | 场景 | 触发条件 |
|------|------|----------|
| `0% / 25%` 轻量 | 局部简单修复、单文件、错误明确 | 默认降档 |
| `50%` 深度 | 多文件联动、重复失败、根因不清 | `syntax_error` / `type_error` / `quality_gate_failed` / 重复 `test_failure` |

---

## Reflexion 失败反思工作流

```
调试失败 / 完成
    │
    ▼
生成 verbal 反思（5句格式）
    │
    ▼
memory_longterm.py --op add-experience
    │
    ▼
自动触发图索引重建（causal graph）
    │
    ▼
下次同类错误可通过 search-causal 命中
```

---

## 验证命令

```bash
# 运行相关测试
python3 -m pytest tests/ -k "相关测试模块" --tb=short

# 检查类型
python3 -m mypy src/ --ignore-missing-imports

# 检查 lint
python3 -m ruff check . 2>&1 | head -30
```

---

## 反模式（Anti-patterns）

- 在未定位根因前提出修复方案
- "我觉得可能是..." 替代具体 file:line 证据
- 只修表面症状，不挖掘根本原因
- 跳过回归测试直接宣布修复完成
- 不写 Reflexion Entry，导致下次重复踩坑

---

## 错误分类集成

DEBUGGING 阶段对接 error_classifier 模块，识别以下错误类型并调整激活档位：
- `syntax_error` / `type_error` → 触发档位升级
- `quality_gate_failed` → 触发档位升级
- 重复 `test_failure`（相同 test_id 出现 ≥2次）→ 触发档位升级
- 首次 `test_failure` / `import_error`（已有 causal 命中）→ 保持轻量档位
