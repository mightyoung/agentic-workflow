# Paper Notes: Agent Memory / Skill Evolution / Research-Agent Bottlenecks

## 1) D-MEM: Dopamine-Gated Agentic Memory via Reward Prediction Error Routing

- URL: https://arxiv.org/abs/2603.14597
- TL;DR: use a lightweight critic/router to decide whether an interaction is routine enough to skip/cache, or surprising/important enough to trigger heavier memory evolution.
- Core idea:
  - Low-RPE / routine inputs go to a fast path.
  - High-RPE / contradictory / preference-shift inputs trigger memory graph updates.
  - Goal is to avoid O(N^2) “append-evolve everything” cost and reduce token usage.
- Project relevance:
  - Strong fit for `memory_longterm`, `experience_ledger`, and the existing structured summaries (`planning_summary`, `thinking_summary`, `research_summary`, `review_summary`).
  - Best use: add a gating layer before writing memory / summaries, so routine outputs do not cause expensive long-term memory restructuring.
  - Caution: do not turn this into a new always-on autonomous rewrite loop. Keep the gate explicit and conservative.

## 2) SkillClaw: Let Skills Evolve Collectively with Agentic Evolver

- URL: https://huggingface.co/papers/2604.08377
- TL;DR: skills are treated as a shared repository that can be updated from multi-user trajectories and then synchronized system-wide.
- Core idea:
  - Aggregate usage trajectories across users.
  - An autonomous evolver identifies recurring patterns.
  - The skill set is refined/extended and shared back to all users.
- Project relevance:
  - Strong fit for the project’s skill/versioning workflow, benchmark-driven notes, and the existing “skill docs should reflect runtime reality” discipline.
  - Best use: offline skill evolution proposals based on accumulated evidence, not blind self-mutation.
  - Caution: keep human-reviewed gating for merged skill changes; use benchmark evidence as the input signal.

## 3) AIRA_2: Overcoming Bottlenecks in AI Research Agents

- URL: https://arxiv.org/abs/2603.26499
- TL;DR: research agents are bottlenecked by throughput, evaluation noise, and fixed single-turn operators; solve this with async worker pools, consistent evaluation, and dynamic ReAct agents.
- Core idea:
  - Asynchronous multi-worker execution increases sample throughput.
  - Hidden consistent evaluation reduces misleading validation noise.
  - Dynamic ReAct agents scope actions and debug interactively.
- Project relevance:
  - Strong support for keeping the benchmark/eval line as the authority on “what to change”.
  - Suggests the project should optimize evaluation consistency and parallelize independent checks, rather than letting autonomous loops choose directions on weak signal.
  - Best use: consistent benchmark protocols, parallel specialist checks, and evaluation noise guards.

## Practical Takeaways for agentic-workflow

1. **Memory gating > unconditional memory growth**
   - Borrow D-MEM’s fast/slow routing for memory writes and summary propagation.

2. **Skill evolution should be evidence-driven**
   - Borrow SkillClaw’s collective evolution, but keep approval gates and benchmark evidence.

3. **Benchmark signal is more valuable than autonomous self-editing**
   - Borrow AIRA_2’s consistent evaluation emphasis.
   - Keep evaluation protocols stable and use them as the source of truth for skill changes.

4. **Avoid overfitting the runtime with heavy prompt inflation**
   - These papers all point toward selective activation, not “always-on full context”.

## Suggested next implementation steps

- Add a memory write gate based on novelty / contradiction / utility.
- Introduce a “skill evolution proposal” artifact that is reviewed before landing.
- Strengthen benchmark consistency and treat benchmark evidence as the primary input for skill updates.
- Keep autonomous improvement loops as executors, not as primary decision makers.
