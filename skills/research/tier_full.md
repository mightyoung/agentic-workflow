<!-- tier: ~45% full methodology + commands -->

# RESEARCH - Full Methodology

## Entry Criteria (Expanded)

### Explicit Triggers
- User says: "帮我搜索...", "调研一下...", "查找最佳实践...", "选型建议..."

### Implicit Triggers
Task involves:
- Complex task (3+ steps)
- New technology domain
- External reference needed for technical decision
- Keywords: best practices, "how to", "what are", implementation case studies

### Router Keywords
最佳实践, 有什么, 有哪些, 选型, 怎么做, 怎么实现, 如何实现, 参考, 案例

## Research Summary Fields

Research findings propagate to downstream stages via these fields:

| Field | Purpose | Example |
|-------|---------|---------|
| `research_found` | Did search succeed? | true/false |
| `research_source` | Where findings stored | artifact_registry/findings_latest |
| `research_path` | File location | .research/findings/findings_{session}.md |
| `key_terms` | Search keywords used | "Python async best practices" |
| `search_engine` | Tool used | google/baidu |
| `sources_count` | Number of sources found | 5 |
| `used_real_search` | Real search executed (not AI only)? | true/false |
| `degraded_mode` | Fallback mode activated? | true/false |
| `evidence_status` | Quality of evidence | verified/degraded |

## Core Process (Complete)

### Step 1: Identify Research Problem

Formalize the research question:
```
User request: [Original request]
Research question: [Extracted core problem]
Search scope: [Network best practices | GitHub projects | Official docs | Community discussion]
```

### Step 2: Execute Search

**Search Tool Priority** (auto-degrade on unavailability):

1. **WebSearch** (preferred — Claude Code native)
   ```bash
   WebSearch(query="distributed transaction best practices", num_results=10)
   ```

2. **WebFetch** (when specific URL known)
   ```bash
   WebFetch(url="https://docs.example.com/architecture", query="caching strategies")
   ```

3. **Tavily** (if available)
   - Check availability first; skip if unavailable

**Degradation Strategy**: 
If all search tools unavailable → explicitly tell user (do NOT silently use pure AI knowledge).

**Do NOT assume**:
- Tavily always available
- Baidu API key configured (requires `BAIDU_QIANFAN_API_KEY`)

### Step 3: Source Reliability Assessment

**Source Grading Table**:

| Grade | Type | Reliability | Usage |
|-------|------|-------------|-------|
| **A** | Official docs, RFCs, standards | Highest | Cite as authority |
| **B** | GitHub official/popular repos, tech books | High | Use as implementation reference |
| **C** | Tech blogs (Medium, InfoQ), industry reports | Medium | Cross-validate; note as reference |
| **D** | Forums (Stack Overflow), personal blogs, Zhihu | Low | Multi-source validation required |

**Key Finding Verification**:
```
FOR EACH key_finding IN search_results:
    IF source_grade < C THEN
        Mark "pending verification"
        Attempt cross-validation from other sources
    ELSE IF cannot cross-validate THEN
        Annotate in findings: "reliability pending confirmation"
    END
END
```

**Analyze Search Results**:
1. Web best practices: categorize by source, extract key points, mark applicable scenarios
2. GitHub projects: name, characteristics, use cases, tech stack
3. Community experience: common pitfalls, best practice summary, lessons learned

### Step 4: Generate `.research/findings/findings_{session}.md`

Create findings file with structure:
```markdown
# 研究发现 - [Research Topic]

## 研究问题
> [Core problem description]

## 网络最佳实践

### Source 1 Name
- Key points: [list]
- Applicable scenarios: [list]
- Reference: [URL]

### Source 2
...

## GitHub 成熟项目

| Project | Characteristics | Use Cases |
|---------|-----------------|-----------|
| name1 | desc | uses |

## 社区经验总结
- Lesson 1: [description]
- Lesson 2: [description]

## 技术决策

| Decision | Alternatives | Rationale |
|----------|--------------|-----------|
| choice | options | why |

## 待验证假设
- Assumption 1: [description]
- Assumption 2: [description]
```

### Step 5: Spawn Researcher Sub-Agent (Optional)

For large-scale research, spawn parallel researcher agents:
```
→ Spawn researcher sub-agent
→ Execute multiple searches in parallel
→ Aggregate results
→ Write to `.research/findings/findings_{session}.md`
```

## Auto-Verify Before Phase Transition

```bash
# Findings file exists and has substantial content (>100 bytes)
find .research/findings -type f -name 'findings_*.md' -size +100c | grep -q .
```

## Completion Status Protocol

| Status | Meaning | Exit Condition |
|--------|---------|----------------|
| **DONE** | Phase complete | Findings stored in file; ready for THINKING/PLANNING |
| **DONE_WITH_CONCERNS** | Complete with caveats | Findings usable, but unresolved questions remain |
| **BLOCKED** | Phase blocked | Network issues or tool failure; user intervention needed |
| **NEEDS_CONTEXT** | Needs more info | Research question unclear; more user input required |

### Research Quality Checklist

- [ ] Search covered major sources (official docs, blogs, GitHub)
- [ ] Key points extracted (not just copied)
- [ ] Scenarios and limitations noted
- [ ] Results structured for downstream use
- [ ] No hardcoded secrets or sensitive data
