# Meta-Harness + EvoSkills 研究摘要

> 关注点：如何把 benchmark、memory、skill 演化和自进化门禁串成更稳的闭环。

## 1. Meta-Harness: End-to-End Optimization of Model Harnesses

核心信息：
- 论文强调：LLM 系统性能不只取决于模型权重，也取决于 harness 代码，也就是“存什么、取什么、怎么呈现给模型”。
- 关键不是压缩更多文本，而是保留足够的执行轨迹、源码、分数和历史候选信息，供外层优化器搜索 harness。
- 它展示了一个外循环：基于 source code + scores + execution traces 去搜索 harness，且有明确的性能收益。

对本项目的启发：
- 你现在已经有很多“harness-like”设施：
  - `workflow_engine`
  - `unified_state`
  - `trajectory_logger`
  - `checkpoint_manager`
  - `memory_longterm`
  - `skill_evolution.py`
- 这篇论文支持你的现有方向：**benchmark/eval 应该是方向证据源，而不是仅仅记录结果**。
- 它也支持你之前做的总结链扩展：`planning_summary / research_summary / thinking_summary / review_summary / resume_summary` 的价值在于可恢复、可检索、可被外层循环利用。

可借鉴点：
- 保留 execution traces，不要只保留高度压缩的摘要。
- 让外层改进逻辑消费：
  - 代码
  - 运行轨迹
  - benchmark 分数
  - proposal artifact
- 对“harness 改进”做显式版本化和可回滚记录。

不建议直接照搬：
- 不要把主 runtime 变成自由搜索器。
- 不要让自动优化直接越过门禁修改核心 harness。

## 2. EvoSkills: Self-Evolving Agent Skills via Co-Evolutionary Verification

核心信息：
- 论文讨论的是：skill 是多文件、互相耦合的 artifact bundle，不能简单套用工具自进化方法。
- 它的关键设计是：
  - `Skill Generator`
  - `Surrogate Verifier`
  - 通过 co-evolution 迭代 refinement
- 重点不是“自动修改 skill”，而是“生成候选 skill + 由 verifier 提供可操作反馈 + 继续迭代”。

对本项目的启发：
- 你的项目已经开始做对了两件事：
  - `scripts/skill_evolution.py`：把 benchmark evidence 转成 proposal，而不是直接改 skill
  - `.self-improvement/self_improve.sh`：保留受控改进流程
- 这篇论文强化了一个判断：**skill 演化应该是 proposal-driven，而不是 runtime 自动 mutation**。
- 你目前的不足在于：proposal 只是生成了，还缺一个系统化的 surrogate verifier。

可借鉴点：
- 给 skill proposal 增加 verifier 层：
  - 读 proposal
  - 检查是否和 benchmark evidence 一致
  - 检查是否会破坏现有测试/门禁
  - 给出可执行反馈，而不是直接修改
- verifier 的输入应该来自：
  - benchmark JSON
  - `tests/test_skill_enhancements.py`
  - 核心回归测试
  - skill frontmatter / 文本一致性检查

不建议直接照搬：
- 不要让 generator 自动写回 `skills/*/skill.md`。
- 不要把 proposal verifier 变成另一个“无人审核”的自动改写器。

## 3. 对本项目的综合建议

优先级最高的三个动作：

1. 把 benchmark / trajectory / checkpoint 继续当作 harness 证据层。
2. 把 skill evolution 保持在 proposal + verifier 的受控流程里。
3. 继续把 summary / trace 保留得足够完整，避免过早压缩信号。

适合继续推进的方向：
- `skill_evolution.py` 后面接一个 `proposal_verifier.py`
- proposal 通过后再进入 `.self-improvement` 的可审阅改动候选
- benchmark 输出继续保留版本号、样本数、限制说明和策略建议

一句话结论：
- **Meta-Harness** 支持你继续强化 harness 级闭环和 trace 留存。
- **EvoSkills** 支持你把 skill 演化做成“proposal + verifier + gate”。
- 两者共同支持：**benchmark 负责定方向，proposal 负责承接证据，自进化只做受控执行**。
