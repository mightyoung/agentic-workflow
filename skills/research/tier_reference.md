<!-- tier: remaining reference + implementation notes -->

# RESEARCH - Reference & Implementation

## Relationship to Other Phases

| Phase | Relationship |
|-------|--------------|
| THINKING | RESEARCH findings serve as expert perspective input |
| PLANNING | RESEARCH discoveries inform planning decisions |
| EXECUTING | RESEARCH must complete before complex task execution |

## Default Strategy

`defer_or_lighten` — Only inject full research skill when external facts, best practices, or authoritative sources are needed. Otherwise keep lightweight to avoid token overhead.

## Implementation Notes

### Researcher Sub-Agent Pattern

Use when research scope is large:
```
1. Identify 3-5 parallel search tracks
2. Spawn researcher agents for each track
3. Collect results
4. Synthesize into single findings file
```

### Handling Tool Failures

**If WebSearch unavailable**:
1. Attempt WebFetch on known reference sites
2. If WebFetch also unavailable → BLOCKED
3. Inform user explicitly; do NOT fall back to pure AI knowledge

**If all search tools unavailable**:
```
Report to user:
"I cannot access web search tools (WebSearch and WebFetch are unavailable). 
I can proceed with knowledge-based analysis, but findings will not include real-time research. 
Would you like me to:
A) Continue with knowledge-based analysis
B) Wait and retry when tools available
C) Cancel research phase"
```

## Findings File Location Convention

- **Standard location**: `.research/findings/findings_{session}.md`
- **{session}**: Unique identifier for current session/task
- **Directory creation**: Auto-create `.research/findings/` if not exists

## Integration with Memory System

Research findings integrate with agentic-workflow memory:
- Store key findings in `.research/findings/findings_{session}.md`
- Propagate findings metadata to next phase via `research_summary` fields
- Enable memory recall of past research in same domain (if multiple sessions)

## Integration with AskUserQuestion

When user input needed during research:
- Clarify research scope
- Confirm which sources are most relevant
- Validate if findings meet requirements

Use AskUserQuestion format (see shared preamble).

## When Research Alone Is Insufficient

If findings show conflicting expert opinions:
1. Note conflicting viewpoints in findings file
2. Mark reliability status appropriately
3. Escalate decision to downstream phases (THINKING can pick authoritative source)

## Degraded Mode Handling

Degraded mode occurs when search tools fail but findings are still needed:
- Mark `degraded_mode: true` in metadata
- Use best available knowledge
- Clearly flag as "knowledge-based, not search-backed"
- Inform user of quality downgrade

## Example: Small Research Task

User: "帮我找一下React性能优化的最佳实践"

```
Step 1: Research Problem
→ Question: "What are React performance optimization best practices?"
→ Scope: Official docs, popular blogs, GitHub projects

Step 2: Search Execution
→ WebSearch("React performance optimization best practices")
→ WebFetch("https://react.dev/reference/react")

Step 3: Source Assessment
→ React.dev (A-grade: official)
→ Popular GitHub repos (B-grade: proven implementations)
→ Tech blog posts (C-grade: validated with other sources)

Step 4: Results Structure
→ Group by: Rendering optimization, Memory leaks, Code splitting
→ Include applicable scenarios and trade-offs

Step 5: Generate File
→ `.research/findings/findings_react_perf_2024.md`
→ 3-5 sources, 300-500 words, ready for THINKING phase
```

## Example: Large Research Task

User: "我想选一个微服务架构框架，请调研一下有什么选项"

```
Step 1: Problem Identification
→ Decision: "Which microservice framework to adopt?"
→ Scope: Multi-track (Kubernetes, Docker, Service mesh, API Gateway, monitoring)

Step 2: Parallel Search (Sub-agents)
→ Agent 1: Kubernetes + container orchestration
→ Agent 2: Service mesh (Istio, Linkerd, Consul)
→ Agent 3: API Gateway (Kong, AWS API Gateway, nginx)
→ Agent 4: Monitoring (Prometheus, Datadog, New Relic)

Step 3: Aggregate & Analyze
→ Consolidate findings from 4 agents
→ Cross-validate recommendations across sources

Step 5: Output
→ `.research/findings/findings_microservice_2024.md`
→ Comprehensive framework comparison table
→ Trade-off analysis for each option
→ Recommendation with rationale
```

## Related Concepts

- **Research Summary**: Metadata struct propagated to THINKING/PLANNING
- **Boil the Lake**: See shared preamble for iterative question-asking pattern
- **Findings File**: `.research/findings/findings_{session}.md` format and location
