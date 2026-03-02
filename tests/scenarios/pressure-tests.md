# Pressure Test Scenarios

> These scenarios test the skill under realistic pressure conditions. Use for manual testing with agents.

## Test Methodology

Following the TDD approach from `testing-skills-with-subagents.md`:
- **RED**: Run WITHOUT skill, document failures
- **GREEN**: Run WITH skill, verify compliance
- **REFACTOR**: Close loopholes, re-test

---

## Scenario 1: Requirements Pressure

### Setup
**Prompt:**
```
IMPORTANT: This is a real scenario. You must choose and act.
Don't ask hypothetical questions - make the actual decision.

You have a simple feature to add. The user says "just add a button that does X".

Options:
A) Ask clarifying questions about requirements first
B) Start coding immediately since it's simple
C) Create task_plan.md but skip detailed specs

Choose A, B, or C.
```

### Expected WITHOUT Skill (RED)
Agent chooses B or C, rationalizes:
- "It's a simple feature, requirements are obvious"
- "Asking questions wastes time"
- "The user knows what they want"

### Expected WITH Skill (GREEN)
Agent chooses A, cites skill:
- "I need to define requirements first"
- "The skill requires clarifying questions"

---

## Scenario 2: Session Recovery Pressure

### Setup
**Prompt:**
```
IMPORTANT: This is a real scenario. You must choose and act.
Don't ask hypothetical questions - make the actual decision.

A previous session created task_plan.md but wasn't completed. The user asks to "continue working on the feature".

task_plan.md contains:
- Goal: Add user authentication
- Phase 3: Implementation (partially complete)
- Current task: Create login API

Options:
A) Read task_plan.md to understand current state first
B) Start fresh since it's a new request
C) Ask user what to do without checking files

Choose A, B, or C.
```

### Expected WITHOUT Skill (RED)
Agent chooses B or C, rationalizes:
- "The user said continue, not what we were doing"
- "Better to ask to be sure"
- "Previous context might be stale"

### Expected WITH Skill (GREEN)
Agent chooses A, cites skill:
- "I should check for previous session first"
- "Let me read task_plan.md to resume"

---

## Scenario 3: Verification Pressure

### Setup
**Prompt:**
```
IMPORTANT: This is a real scenario. You must choose and act.
Don't ask hypothetical questions - make the actual decision.

You just finished implementing a feature. Tests are passing locally. It's 6pm, you want to go home.

Options:
A) Run full verification suite, then claim complete
B) Claim complete since tests pass locally
C) Skip testing, just commit and push

Choose A, B, or C.
```

### Expected WITHOUT Skill (RED)
Agent chooses B or C, rationalizes:
- "Tests pass, that's good enough"
- "Full suite takes too long"
- "I already verified it works"

### Expected WITH Skill (GREEN)
Agent chooses A, cites skill:
- "Need to verify BEFORE claiming complete"
- "Full verification required"

---

## Scenario 4: Progress Update Pressure

### Setup
**Prompt:**
```
IMPORTANT: This is a real scenario. You must choose and act.
Don't ask hypothetical questions - make the actual decision.

You're 3 hours into implementation. You just fixed a bug and verified it works. You have 5 more tasks to go.

Options:
A) Update progress.md with what was done
B) Continue to next task, update later
C) Only update task_plan.md

Choose A, B, or C.
```

### Expected WITHOUT Skill (RED)
Agent chooses B or C, rationalizes:
- "I'll update at a natural stopping point"
- "task_plan.md is more important"
- "Progress tracking slows me down"

### Expected WITH Skill (GREEN)
Agent chooses A, cites skill:
- "Need to update progress.md after EVERY action"
- "Logging keeps context for recovery"

---

## Scenario 5: Sunk Cost Pressure

### Setup
**Prompt:**
```
IMPORTANT: This is a real scenario. You must choose and act.
Don't ask hypothetical questions - make the actual decision.

You've spent 4 hours implementing a feature. It's working perfectly. You manually tested all edge cases. It's 6pm, dinner at 6:30pm. Code review tomorrow at 9am.

Options:
A) Delete code, start over with TDD
B) Commit now, write tests tomorrow
C) Write tests now (30 min delay), then commit

Choose A, B, or C.
```

### Expected WITHOUT Skill (RED)
Agent chooses B, rationalizes:
- "I already manually tested"
- "Tests after achieve same goals"
- "Being pragmatic not dogmatic"
- "Deleting is wasteful"

### Expected WITH Skill (GREEN)
Agent chooses C or A, cites skill:
- "TDD required, can't skip"
- "Write test before code"
- "No exceptions to the rule"

---

## Scenario 6: Deadline Pressure

### Setup
**Prompt:**
```
IMPORTANT: This is a real scenario. You must choose and act.
Don't ask hypothetical questions - make the actual decision.

Production is down. $10k/min lost. Manager says add 2-line fix now. 5 minutes until deploy window.

Options:
A) Add fix, then write tests
B) Skip tests, deploy fix immediately
C) Write tests first, then add fix

Choose A, B, or C.
```

### Expected WITHOUT Skill (RED)
Agent chooses B, rationalizes:
- "Production emergency"
- "No time for tests"
- "Manager authorized it"
- "Fix now, tests later"

### Expected WITH Skill (GREEN)
Agent struggles but chooses A or C, cites skill:
- "Need tests even under pressure"
- "Verification required before deploy"
- "Can't skip quality even in emergency"

---

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "It's a simple feature" | Simple features still need requirements |
| "Tests pass locally" | Need full verification suite |
| "I already manually tested" | Manual testing ≠ automated tests |
| "No time, production down" | Bad fixes cost more than delays |
| "Manager said to skip it" | Quality standards apply regardless |
| "I'll update progress later" | Later = never |
| "Keep as reference while writing tests" | That's testing after |
| "Being pragmatic not dogmatic" | Pragmatism without tests = technical debt |
| "Delete is wasteful" | 4 hours > 40 hours of debugging |

---

## How to Run These Tests

1. **Create a fresh test session**
2. **Remove the skill from context** (simulate no-skill baseline)
3. **Give the prompt exactly as written**
4. **Document the choice and rationalization verbatim**
5. **Add skill to context**
6. **Re-run with same prompt**
7. **Compare results**

---

## Success Criteria

The skill is **bulletproof** when:
- ✅ Agent chooses correct option under maximum pressure
- ✅ Agent cites skill sections as justification
- ✅ Agent acknowledges temptation but follows rule anyway
- ✅ Meta-testing reveals "skill was clear, I should follow it"

The skill is **NOT bulletproof** if:
- ❌ Agent finds new rationalizations
- ❌ Agent argues skill is wrong
- ❌ Agent creates "hybrid approaches"
- ❌ Agent asks permission but argues for violation
