# Plan: {{TASK_NAME}}

> **Provenance Header**
> Generated-By: agentic-workflow
> Session: {{SESSION_ID}}
> Source-Spec: .specs/{{FEATURE_ID}}/spec.md
> Timestamp: {{TIMESTAMP}}

---

## Technical Context

### Project Overview
[Brief description of the project and its goals]

### Technology Stack
- **Language:** [e.g., Python 3.11+]
- **Framework:** [e.g., FastAPI, React]
- **Database:** [e.g., PostgreSQL 14+, SQLite]
- **Key Dependencies:** [list of major dependencies]

### Architecture
[Describe the high-level architecture and design decisions]

---

## Structure Decisions

### Directory Structure
```
/
├── src/
│   └── [source files]
├── tests/
│   └── [test files]
├── docs/
│   └── [documentation]
└── [config files]
```

### Module Design
[Describe how the code is organized into modules]

### Data Model
[Describe the key data structures and their relationships]

---

## Constraints

### Technical Constraints
- [ ] **Tech Stack:** [e.g., Python 3.11+, must use type hints]
- [ ] **Performance:** [e.g., <100ms latency, 99.9% uptime]
- [ ] **Security:** [e.g., no secrets in code, encrypted at rest]

### Business Constraints
- [ ] **Timeline:** [delivery date or milestone]
- [ ] **Budget:** [resource constraints]
- [ ] **Scope:** [what is in/out of scope]

### Compliance Constraints
- [ ] **Compliance:** [e.g., GDPR, SOC2, data residency]

---

## Performance & Scale Goals

### Scale Targets
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| [e.g., Latency] | [e.g., <100ms p99] | [how to measure] |
| [Throughput] | [e.g., 1000 req/s] | [how to measure] |

### Resource Limits
- **Memory:** [e.g., <512MB per instance]
- **CPU:** [e.g., <2 cores per instance]
- **Storage:** [e.g., <10GB]

---

## Constitution Check

This plan has been reviewed against project constitution:

- [ ] **AI-Safe:** No prompt injection vectors in user inputs
- [ ] **Testable:** All features have measurable acceptance criteria
- [ ] **Observable:** Logging/metrics for all critical paths
- [ ] **Recoverable:** Graceful degradation on external service failure
- [ ] **Secure:** No secrets in code, proper auth/authz

---

## Output Artifacts

This plan generates the following artifacts:

| Artifact | Source | Description |
|----------|--------|-------------|
| `.contract.json` | plan.md | Machine-readable contract for completion gate |
| `tasks.md` | plan.md | Task breakdown with parallel markers |
| `task_plan.md` | tasks.md | Execution checklist for workflow_engine |

---

## Risk Assessment

### High-Risk Areas
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | [H/M/L] | [H/M/L] | [Mitigation strategy] |

### Open Questions
| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | [Question] | [Who] | OPEN |

---

*This plan is generated from spec.md and drives task decomposition. Changes here should propagate to tasks.md and .contract.json.*