# Tasks: {{TASK_NAME}}

> **Provenance Header**
> Generated-By: agentic-workflow
> Session: {{SESSION_ID}}
> Source-Spec: .specs/{{FEATURE_ID}}/spec.md
> Source-Plan: .specs/{{FEATURE_ID}}/plan.md
> Timestamp: {{TIMESTAMP}}
> Generated: {{GENERATION_TIMESTAMP}}

---

## Setup

- [ ] **TASK-SETUP-1:** [Task title]
  - **Files:** `path/to/file1.py`, `path/to/file2.py`
  - **Verification:** `[P]` pytest tests/test_setup.py -v
  - **Owner:** [agent/team-member]

## Foundational

- [ ] **TASK-FOUND-1:** [Task title]
  - **Files:** `src/core/`
  - **Verification:** `[P]` pytest tests/test_core.py -v
  - **Owner:** [agent/team-member]
  - **Blocked-By:** TASK-SETUP-1

## User Story 1: [Story Title]

- [ ] **TASK-US1-1:** [Task title]
  - **Files:** `src/features/user_story_1/task1.py`, `tests/features/user_story_1/test_task1.py`
  - **Verification:** `[P]` pytest tests/features/user_story_1/ -v
  - **Owner:** [agent/team-member]
  - **Acceptance:** [From spec acceptance criteria]
  - **Blocked-By:** TASK-FOUND-1

- [ ] **TASK-US1-2:** [Task title]
  - **Files:** `src/features/user_story_1/task2.py`
  - **Verification:** `[P]` pytest tests/features/user_story_1/ -v
  - **Owner:** [agent/team-member]
  - **Blocked-By:** TASK-US1-1

## User Story 2: [Story Title]

- [ ] **TASK-US2-1:** [Task title]
  - **Files:** `src/features/user_story_2/`
  - **Verification:** `[P]` pytest tests/features/user_story_2/ -v
  - **Owner:** [agent/team-member]
  - **Blocked-By:** TASK-FOUND-1

## Polish

- [ ] **TASK-POLISH-1:** [Task title]
  - **Files:** `README.md`, `docs/`
  - **Verification:** `[ ]` Manual review
  - **Owner:** [agent/team-member]
  - **Blocked-By:** TASK-US1-2, TASK-US2-1

---

## Task Provenance

| Task ID | Source | Story | Created |
|---------|--------|--------|---------|
| TASK-SETUP-1 | auto | - | {{TIMESTAMP}} |
| TASK-FOUND-1 | spec | - | {{TIMESTAMP}} |
| TASK-US1-* | spec | US-1 | {{TIMESTAMP}} |
| TASK-US2-* | spec | US-2 | {{TIMESTAMP}} |

## Parallel Groups

Tasks marked `[P]` can run in parallel within their group:

- **Group A:** TASK-SETUP-1, TASK-FOUND-1 (can run in parallel if no blocking deps)
- **Group B:** TASK-US1-1, TASK-US2-1 (can run in parallel after foundational complete)
- **Group C:** TASK-US1-2, TASK-US2-2 (sequential within story, parallel across stories)

## Conflict Groups

Tasks that MUST run sequentially due to shared state:

- **Conflict 1:** TASK-US1-1 -> TASK-US1-2 (same feature, sequential)
- **Conflict 2:** TASK-US2-1 -> TASK-US2-2 (same feature, sequential)

---

*This tasks.md is generated from spec.md and plan.md. Do not edit manually - changes will be overwritten.*
