# Integrated Development Workflow

> One command to start everything. A complete development workflow orchestrator for AI coding agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/integrated-dev-workflow)](https://github.com/mightyoung/integrated-dev-workflow)
[![GitHub forks](https://img.shields.io/github/forks/mightyoung/integrated-dev-workflow)](https://github.com/mightyoung/integrated-dev-workflow)

> **English** | [中文](README.zh-CN.md)

---

## Table of Contents

- [What is Integrated Development Workflow?](#what-is-integrated-development-workflow)
- [Get Started](#get-started)
- [Supported AI Agents](#supported-ai-agents)
- [Installation](#installation)
- [Usage](#usage)
- [Agent Compatibility](#agent-compatibility)
- [File Structure](#file-structure)
- [Required Sub-Skills](#required-sub-skills)
- [Workflow Phases](#workflow-phases)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Contributing](#contributing)

---

## What is Integrated Development Workflow?

Integrated Development Workflow **flips the script** on ad-hoc AI coding. Instead of vibe-coding every piece from scratch, this skill provides a **complete, orchestrated workflow** that guides the agent through:

1. **Requirements** — Clear, documented goals
2. **Planning** — Task breakdown with dependencies
3. **Implementation** — TDD with proper branch management
4. **Testing & Review** — Verification before completion
5. **Completion** — Clean merge/PR workflow

---

## Get Started

Simply tell the agent what you want to build:

```
I want to build a user login feature
Implement a shopping cart
Create an API for user management
Fix the login timeout bug
Refactor the data layer
```

The skill will automatically:

1. Check for previous session
2. Create tracking files (task_plan.md, findings.md, progress.md)
3. Guide through requirements
4. Plan the implementation
5. Execute with best practices

---

## Supported AI Agents

| Agent | Support | Notes |
|-------|---------|-------|
| Claude Code | Full | Hooks supported |
| OpenCode | Full | Via .agents/skills |
| Cursor | Full | Via .cursor/skills |
| Trae | Full | Via .trae/skills |
| Pi Agent | Full | Via npm |
| Windsurf | Full | Via .windsurf/skills |
| Roo Code | Full | Via .roo/skills |
| Codex CLI | Full | Via .codex/skills |
| Generic | Full | Reference skill |

---

## Installation

### Claude Code

```bash
mkdir -p .claude/skills
cp -r /path/to/integrated-dev-workflow .claude/skills/
```

### OpenCode

```bash
mkdir -p .agents/skills
cp -r /path/to/integrated-dev-workflow .agents/skills/
```

### Cursor

```bash
mkdir -p .cursor/skills
cp -r /path/to/integrated-dev-workflow .cursor/skills/
```

### Trae

```bash
mkdir -p .trae/skills
cp -r /path/to/integrated-dev-workflow .trae/skills/
```

### Pi Agent

```bash
pi install npm:integrated-dev-workflow
```

### Windsurf

```bash
mkdir -p .windsurf/skills
cp -r /path/to/integrated-dev-workflow .windsurf/skills/
```

### Manual Install

```bash
mkdir -p .agents/skills
cp -r /path/to/integrated-dev-workflow .agents/skills/
```

---

## Usage

### Quick Start

Simply tell the agent what you want to build. The skill automatically orchestrates the entire development process.

### Manual Invocation

```bash
skill("integrated-dev-workflow")
```

---

## Agent Compatibility

### Feature Comparison

| Feature | Claude Code | OpenCode | Cursor | Trae | Pi Agent | Windsurf |
|---------|-------------|----------|--------|------|----------|----------|
| Hooks | Full | Full | Limited | Limited | Limited | Limited |
| Session recovery | Automatic | Automatic | Via script | Via script | Via script | Via script |
| File templates | All | All | All | All | All | All |
| TDD workflow | Full | Full | Full | Full | Full | Full |
| Code review workflow | Full | Full | Full | Full | Full | Full |

### Claude Code

This skill uses hooks for persistent reminders:

- **PreToolUse**: Reminds to update task_plan.md before major actions
- **PostToolUse**: Prompts to update task status after file changes
- **Stop**: Confirms task progress before ending session

### OpenCode

Full support via `.agents/skills` directory:

1. Copy this skill folder to `.agents/skills/`
2. Skills are automatically discovered
3. Use `skill("integrated-dev-workflow")` to invoke

### Cursor

Similar to Claude Code, hooks may work if Cursor supports extensions:

1. Try copying to `.cursor/skills/`
2. If hooks not supported, manual session recovery

### Trae

Trae is built on VS Code extension model:

1. Copy to `.trae/skills/` or VS Code extensions folder
2. May require manual workflow management

### Pi Agent Limitations

- Hooks are not supported in Pi Agent
- Session recovery requires manual script:
  ```bash
  python3 scripts/session-recovery.py .
  ```

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
| planning-with-files | File-based task tracking |
| brainstorming | Requirement clarification |
| writing-plans | Task refinement |
| using-git-worktrees | Branch management |
| subagent-driven-development | Task execution |
| test-driven-development | TDD workflow |
| systematic-debugging | Issue resolution |
| verification-before-completion | Quality verification |
| requesting-code-review | Code review |
| receiving-code-review | Review handling |
XS|
XS|## Skill Integration Map
XS|
XS|This skill orchestrates 11 sub-skills into a seamless workflow. Here's how they work together:
XS|
XS|### Phase 1: Requirements & Design
XS|
XS|Use these skills to define and clarify requirements:
XS|
XS|- **brainstorming** - Deep requirement analysis and clarification
XS|- **planning-with-files** - Document requirements in task_plan.md
XS|
XS|### Phase 2: Technical Planning
XS|
XS|Use these skills to plan implementation:
XS|
XS|- **writing-plans** - Refine tasks and break into actionable items
XS|- **planning-with-files** - Record technical decisions in findings.md
XS|
XS|### Phase 3: Implementation
XS|
XS|Use these skills for execution:
XS|
XS|- **using-git-worktrees** - Create isolated feature branches
XS|- **subagent-driven-development** - Delegate and execute tasks
XS|- **test-driven-development** - TDD workflow for each task
XS|- **systematic-debugging** - Fix issues when they arise
XS|- **planning-with-files** - Update progress.md after each action
XS|
XS|### Phase 4: Testing & Review
XS|
XS|Use these skills for quality assurance:
XS|
XS|- **verification-before-completion** - Run tests, verify build
XS|- **requesting-code-review** - Formal code review
XS|- **receiving-code-review** - Handle feedback and fix issues
XS|
XS|### Phase 5: Completion
XS|
XS|Use these skills to finish:
XS|
XS|- **finishing-a-development-branch** - Merge, PR, or cleanup options
XS|- **planning-with-files** - Final status update
XS|
XS|### Skill Coordination
XS|
XS|This skill acts as an **orchestrator** that:
XS|
XS|1. **Delegates** specific tasks to specialized skills
XS|2. **Coordinates** hand-offs between skills (e.g., TDD -> debugging -> verification)
XS|3. **Persists** context via planning-with-files across all phases
TW|**Why this works:** Each sub-skill is an expert in its domain. By orchestrating them together, you get best-in-class functionality for each phase without reinventing the wheel.
KK|
KK|## Zero-Dependency Hybrid Mode
KK|
KK|This skill works in **two modes**:
KK|
KK|### Mode 1: Advanced (with sub-skills)
KK|If sub-skills are installed, this skill delegates to them for optimal experience:
KK|
KK|- Try `skill("brainstorming")` first
KK|- If skill not found, use inline fallback guide
KK|
KK|### Mode 2: Standalone (zero-dependency)
KK|If sub-skills are NOT installed, this skill uses **built-in fallback** content:
KK|
KK|- All core workflows are documented inline
KK|- Templates are embedded in this skill
KK|- You follow the same process, but with guidance in this file
KK|
KK|### How It Works
KK|
KK|1. **First**: Try to invoke sub-skill `skill("xxx")`
KK|2. **If not found**: Use the inline fallback guide for that step
KK|3. **Result**: Works identically either way - just different experience levels
KK|
KK|**Recommended**: Install sub-skills for best experience, but skill works completely without them!
XS|
XS|---
XS|
XJ|## Workflow Phases
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

User: "Add user authentication"

- Creates task_plan.md
- Asks: "What should auth include?"
- Documents requirements
- Plans: login, register, password reset, token handling
- Implements each with TDD
- Verifies and creates PR

### Example 2: Bug Fix

User: "Fix the login timeout"

- Creates task_plan.md
- Asks: "When does it timeout?"
- Researches in findings.md
- Plans: fix timeout, add retry
- Implements and verifies

### Example 3: Refactoring

User: "Refactor data layer"

- Creates task_plan.md
- Documents current problems
- Plans: extract interface, create repo, migrate
- Executes with test coverage
- Full regression testing

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

MIT License - See LICENSE for details.

---

## Contributing

Contributions welcome! See CONTRIBUTING.md for guidelines.

---

## Documentation

| Document | English | Chinese |
|----------|---------|---------|
| Usage Guide | README.md | README.zh-CN.md |
| Contributing | CONTRIBUTING.md | CONTRIBUTING.zh-CN.md |
| Pressure Tests | tests/scenarios/pressure-tests.md | tests/scenarios/pressure-tests.zh-CN.md |
