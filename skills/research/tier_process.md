<!-- tier: ~30% core process flow -->

# RESEARCH - Core Process

## Entry Criteria

Research phase begins when:
1. User explicitly requests: "搜索...", "调研...", "查找最佳实践...", "选型建议..."
2. Task involves: 3+ steps, new technology domain, decisions requiring external references, "best practices", "how to implement", "use cases"
3. Keywords detected: 最佳实践, 有什么, 有哪些, 选型, 怎么做, 怎么实现, 如何实现, 参考, 案例

## Core Process Steps

**Step 1: Identify Research Problem**
Extract the core research question from user request. Map search scope (network best practices | GitHub projects | official docs | community discussion).

**Step 2: Execute Search**
Use search tools in priority order (auto-degrade on unavailability):
1. WebSearch (Claude Code native, preferred)
2. WebFetch (when specific URL known)
3. Fallback: inform user if all tools unavailable; do NOT silently use AI knowledge

**Step 3: Assess Source Reliability**
Grade sources: A (official docs/RFCs—highest), B (GitHub official/open source—high), C (tech blogs/reports—medium), D (forums/personal blogs—low).
For key findings from C/D sources: attempt cross-validation or mark "reliability pending confirmation" in findings file.

**Step 4: Analyze & Structure Results**
Extract from search results: best practices (key points + applicable scenarios), GitHub projects (characteristics + use cases), community lessons (pitfalls + experience summaries).

**Step 5: Generate Findings File**
Create `.research/findings/findings_{session}.md` containing: research problem, web best practices (by source), GitHub projects (table), community experience, technical decisions, pending assumptions.

## Key Decision Points

- **Tool availability**: If WebSearch fails, try WebFetch; if both fail, explicitly inform user and halt (do not degrade to pure AI knowledge)
- **Source grading**: A/B sources proceed directly; C/D sources require additional cross-validation or reliability disclaimer
- **Search coverage**: Stop when major information sources (official, blogs, GitHub) are covered

## Exit Criteria Details

All must be true:
- Findings file exists with >100 characters of content
- At least one real search tool successfully executed (not AI knowledge alone)
- Search results analyzed and key points extracted
- Results ready for THINKING/PLANNING stages to consume
- No unresolved tool failures hidden from user
