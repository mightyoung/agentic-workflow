# Integrated Development Workflow

> **One command to start everything.** A complete development workflow orchestrator for AI coding agents.

[![npm version](https://img.shields.io/npm/v/integrated-dev-workflow.svg)](https://www.npmjs.com/package/integrated-dev-workflow)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **English** | [中文](README.zh-CN.md)

---

## The Problem

AI coding agents often struggle with:
- **Scope creep** — Tasks grow without clear boundaries
- **Lost context** — Long sessions lose track of progress
- **Skipped verification** — "It works" without testing
- **Inconsistent workflows** — Each task feels different

## The Solution

This skill provides a **complete, orchestrated workflow** that guides the agent through:
1. **Requirements** → Clear, documented goals
2. **Planning** → Task breakdown with dependencies
3. **Implementation** → TDD with proper branch management
4. **Testing & Review** → Verification before completion
5. **Completion** → Clean merge/PR workflow

---

## Installation

### Claude Code / Claude Desktop

1. Navigate to your project root
2. Create `.claude/skills` directory if it doesn't exist
3. Copy this skill folder into `.claude/skills/`
4. Restart Claude Code

```bash
mkdir -p .claude/skills
cp -r /path/to/integrated-dev-workflow .claude/skills/
```

### Pi Agent

```bash
pi install npm:integrated-dev-workflow
```

### Manual Install

1. Navigate to your project root
2. Create `.agents/skills` directory if it doesn't exist
3. Copy this skill folder into `.agents/skills/`

---

## Usage

### Quick Start

Simply tell the agent what you want to build:

```
"I want to build a user login feature"
"Implement a shopping cart"
"Create an API for user management"
"Fix the login timeout bug"
"Refactor the data layer"
```

The skill will automatically:
1. ✅ Check for previous session
2. ✅ Create tracking files (task_plan.md, findings.md, progress.md)
3. ✅ Guide through requirements
4. ✅ Plan the implementation
5. ✅ Execute with best practices

### Manual Invocation

```bash
# Invoke the skill directly
skill("integrated-dev-workflow")
```

---

## Agent Compatibility

| Feature | Claude Code | Pi Agent | Generic |
|---------|-------------|----------|---------|
| Hooks (PreToolUse/PostToolUse) | ✅ Full support | ⚠️ Limited | ❌ Not supported |
| Session recovery | ✅ Automatic | ⚠️ Via script | ❌ Manual |
| File templates | ✅ All | ✅ All | ✅ All |
| TDD workflow | ✅ Full | ✅ Full | ✅ Full |
| Code review workflow | ✅ Full | ✅ Full | ✅ Full |

### Claude Code Specific

This skill uses hooks for persistent reminders:
- **PreToolUse**: Reminds to update task_plan.md before major actions
- **PostToolUse**: Prompts to update task status after file changes
- **Stop**: Confirms task progress before ending session

### Pi Agent Limitations

- Hooks are not supported in Pi Agent
- Session recovery requires manual script:
  ```bash
  python3 scripts/session-recovery.py .
  ```

### Generic Agents

Works as a pure reference skill. The agent must manually:
- Check for existing tracking files
- Update progress after each action
- Follow the workflow steps explicitly

---

## File Structure

When installed, this skill creates tracking files:

```
your-project/
├── task_plan.md      # Phase tracking, task checklist
├── findings.md       # Research, decisions, notes  
└── progress.md       # Session log, test results, errors
```

### task_plan.md
```markdown
# Task Plan

## Goal
[BUILD X]

## Phases
- [ ] Phase 1: Requirements
- [ ] Phase 2: Planning
- [ ] Phase 3: Implementation
- [ ] Phase 4: Testing & Review
- [ ] Phase 5: Completion

## Current Phase
Phase 1

## Tasks
- [ ] Task 1
- [ ] Task 2
```

### findings.md
```markdown
# Findings

## Research
- [research notes]

## Technical Decisions
- [decisions made]

## Notes
- [additional notes]
```

### progress.md
```markdown
# Progress

## Session Log
- Started: 2024-01-01 10:00
- Created task_plan.md
- Defined requirements with user

## Test Results
| Test | Status |
|------|--------|
| | |

## Errors Encountered
| Error | Resolution |
|-------|------------|
| | |
```

---

## Required Sub-Skills

This skill orchestrates these sub-skills:

| Skill | Purpose |
|-------|---------|
| `planning-with-files` | File-based task tracking |
| `brainstorming` | Requirement clarification |
| `writing-plans` | Task refinement |
| `using-git-worktrees` | Branch management |
| `subagent-driven-development` | Task execution |
| `test-driven-development` | TDD workflow |
| `systematic-debugging` | Issue resolution |
| `verification-before-completion` | Quality verification |
| `requesting-code-review` | Code review |
| `receiving-code-review` | Review handling |
| `finishing-a-development-branch` | Completion |

---

## Workflow Phases

### Phase 1: Requirements & Design
- Define requirements with user
- Create specification (via spec-kit)
- Review and approve spec

### Phase 2: Technical Planning
- Plan technical approach
- Break into tasks
- Identify dependencies

### Phase 3: Implementation
- Create feature branch
- TDD for each task
- Update progress continuously

### Phase 4: Testing & Review
- Run all tests
- Verify build passes
- Code review

### Phase 5: Completion
- Final verification
- Create PR / merge
- Update final status

---

## Examples

### Example 1: New Feature
```
User: "Add user authentication"

→ Creates task_plan.md
→ Asks: "What should auth include?"
→ Documents requirements
→ Plans: login, register, password reset, token handling
→ Implements each with TDD
→ Verifies and creates PR
```

### Example 2: Bug Fix
```
User: "Fix the login timeout"

→ Creates task_plan.md
→ Asks: "When does it timeout?"
→ Researches in findings.md
→ Plans: fix timeout, add retry
→ Implements and verifies
```

### Example 3: Refactoring
```
User: "Refactor data layer"

→ Creates task_plan.md
→ Documents current problems
→ Plans: extract interface, create repo, migrate
→ Executes with test coverage
→ Full regression testing
```

---

## Troubleshooting

### Session recovery fails
**Solution:** Read existing files, ask user to resume or start fresh

### User doesn't want to define requirements
**Solution:** Create minimal task_plan.md, note assumptions in findings.md

### Too many tasks
**Solution:** Break into phases, use subtask files

### Workflow interrupted
**Solution:** Update task_plan.md with exact next step before stopping

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Documentation

| Document | English | 中文 |
|----------|---------|------|
| Usage Guide | [README.md](README.md) | [README.zh-CN.md](README.zh-CN.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) | [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md) |
| Pressure Tests | [tests/scenarios/pressure-tests.md](tests/scenarios/pressure-tests.md) | [tests/scenarios/pressure-tests.zh-CN.md](tests/scenarios/pressure-tests.zh-CN.md) |
