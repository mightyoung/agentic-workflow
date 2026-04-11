<!-- tier: remaining reference + implementation notes -->

# REFINING - Reference & Implementation

## Completion Status Codes

### DONE
All problems fixed, verification passed.
```
[REFINING] DONE
- issues_fixed: [ISSUE-001, ISSUE-002]
- issues_deferred: [ISSUE-003]
- iterations: 2
```

### DONE_WITH_DEBT
Problems fixed, but technical debt recorded for later.
```
[REFINING] DONE_WITH_DEBT
- issues_fixed: [ISSUE-001]
- technical_debt: [ISSUE-002]
- debt_reason: Fix cost too high; defer to next iteration
```

### BLOCKED
Encountered unfixable problem; requires escalation.
```
[REFINING] BLOCKED
- blocker: ISSUE-001
- reason: Max iterations reached; problem persists
- action: Escalate to user
```

### NEEDS_ESCALATION
User decision or additional resources required.
```
[REFINING] NEEDS_ESCALATION
- question: Should we refactor auth module?
- options: [quick_fix, proper_refactor, defer]
- impact: Affects timeline by 1-3 days depending on choice
```

## Relationship to Other Phases

### DISCOVERING Problems
- Comes from: REVIEWING (explicit problems found), EXECUTING (obstacles hit), PLANNING (conflicts), automated checks (tests fail)
- Goes to: ANALYZE (diagnose problems)

### ANALYZING Causes
- Comes from: DISCOVER (list of problems)
- Goes to: FIX (choose solution to execute)

### FIXING Implementation
- Comes from: ANALYZE (chosen solution)
- Goes to: VERIFY (confirm fix works)

### VERIFYING Results
- Comes from: FIX (completed fix)
- Goes to: Next problem or phase exit

## Anti-Patterns in REFINING

### Anti-Pattern 1: Fixing Without Diagnosing
- Wrong: See problem → immediately code fix
- Right: See problem → analyze root cause → choose best solution → code

### Anti-Pattern 2: Skipping Verification
- Wrong: Fix code → assume it works → move on
- Right: Fix code → test thoroughly → confirm no regressions → then move on

### Anti-Pattern 3: Fixing Only Symptoms
- Wrong: "Error message is confusing" → change message text
- Right: "Error message is confusing" → why? → fix root cause → message becomes clear

### Anti-Pattern 4: Scope Creep During Fixes
- Wrong: Fixing ISSUE-001 → also refactor nearby code → also optimize database
- Right: Fixing ISSUE-001 → only change what's necessary → defer other improvements

## Tips for Effective REFINING

### Tip 1: Start with P0s
Don't get distracted by P3s. Fix critical problems first.

### Tip 2: One Problem at a Time
DISCOVER all problems at once, but FIX one at a time. Easier to verify.

### Tip 3: Test-First Verification
Before fixing, write a test that fails. Fix code. Verify test now passes.

### Tip 4: Document As You Go
Each ISSUE should have: problem statement, root cause, fix applied, tests added, verification result.

### Tip 5: Know When to Stop
Max iterations exist for a reason. If problem persists after max attempts, escalate.

## Integration with Memory System

Store successful fix patterns:
- Problem type → root cause → solution pattern
- Enable pattern reuse in future refining cycles

Example memory entry:
```
Key: "API-error-format-inconsistency"
Value: "Root cause: individual endpoints override error handler. 
Solution: centralize error handler in middleware. 
Prevention: add integration tests for error format consistency."
```

## Handling Complex Problems

For multi-faceted problems:
1. Break into sub-issues with IDs
2. Analyze each separately
3. Fix in dependency order (if some fixes depend on others)
4. Verify each sub-fix
5. Do regression test on all together

Example:
```
ISSUE-001: API auth broken
├─ ISSUE-001a: Token validation wrong
├─ ISSUE-001b: Error message confusing
└─ ISSUE-001c: Rollback didn't work

Fix order: 001a → 001c → 001b
(001c depends on 001a being fixed)
```

## When REFINING Loops Too Much

If same issue appears in multiple iterations:
1. Question the diagnosis (is root cause really identified?)
2. Consider escalation (is this beyond current capability?)
3. Record as technical debt (defer to future dedicated refactor)

Example escalation:
```
ISSUE-002 resurfaced after 3 fix attempts.
Root cause: Architecture limitation, not a bug.
Action: Escalate to ARCHITECTURE phase for redesign.
Record as technical debt: "Refactor order processing architecture"
```

## Example: Large Refining Cycle

```
User feedback: "Dashboard loads very slowly"

DISCOVER:
- Dashboard page load time: 15 seconds
- Severity: P1_HIGH (critical user experience)
- Source: User testing + monitoring data

ANALYZE:
- Why1: Lots of data fetched
- Why2: Single endpoint returns all data
- Why3: No pagination or filtering
- Why4: Endpoint designed for admin report, not user dashboard
- Root cause: Wrong API endpoint used; needs optimization

Solution options:
- A: Add pagination to existing endpoint (quick, partial fix)
- B: Create dedicated dashboard endpoint (proper, more work)
- Recommend: B (addresses root cause)

FIX:
- Create new /api/dashboard/summary endpoint
- Returns minimal data set
- Add pagination support
- Update dashboard component to use new endpoint
- Add tests for new endpoint
- Commit: "fix: create optimized dashboard endpoint for page load performance"

VERIFY:
- Page load time: 15s → 2s (measured)
- No data missing in dashboard
- Tests pass (10/10)
- User testing: "Much better!"
- Status: PASS ✓

Result: Problem solved, root cause addressed, no regressions.
```
