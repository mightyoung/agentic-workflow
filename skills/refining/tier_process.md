<!-- tier: ~30% core process flow -->

# REFINING - Core Process

## Entry Criteria

Refining phase begins when:
1. **Active trigger**: User requests iteration, improvement, optimization, refinement
2. **Passive trigger**: Other phases encounter unsolvable problems
3. **Auto-trigger**: Review/tests find serious issues
4. **Command trigger**: `/refining` or `/iterate` explicit command

## DISCOVER Step

**Task**: Identify all problems in current work

**Check categories** (use all):
- Consistency: Internal contradictions, conflicting assumptions?
- Completeness: Missing edge cases?
- Feasibility: Can this technically be built?
- Performance: Bottlenecks or resource waste?
- Quality: Code/docs standards met?
- Alignment: Matches user expectations?

**Problem severity classification**:
- `P0_CRITICAL`: Blocks everything; must fix now
- `P1_HIGH`: Affects core functionality; fix soon
- `P2_MEDIUM`: Affects experience; fix when possible
- `P3_LOW`: Edge case; fix later

**Output format**:
```markdown
| ID | Problem | Category | Severity | Source |
|----|---------|----------|----------|--------|
| ISSUE-001 | ... | consistency | P1_HIGH | review |
```

## ANALYZE Step

**Task**: Diagnose root cause using 5-Why analysis and impact mapping

**Root cause template**:
```
Problem: xxx
Why1: xxx
Why2: xxx (based on Why1 answer)
Why3: xxx (based on Why2 answer)
Why4: xxx
Why5: xxx
Root cause: [pattern emerges]
```

**Impact scope**:
- Which files/modules affected?
- Which user scenarios affected?
- Risk of rollback/regression?

**Choose fix options** — trade analysis table:
```
| Option | Pros | Cons | Cost |
|--------|------|------|------|
| A | | | |
| B | | | |
```

## FIX Step

**Task**: Execute chosen fix solution

**Execution checklist**:
- [ ] Create fix branch (if needed)
- [ ] Backup original files
- [ ] Execute fix
- [ ] Update docs
- [ ] Update tests
- [ ] Commit changes

**Output**:
```markdown
| ID | Problem | Solution | Files Changed |
|----|---------|----------|---|
| ISSUE-001 | ... | Plan B | file1, file2 |
```

## VERIFY Step

**Task**: Confirm fix works and no new problems introduced

**Verification checklist**:
- [ ] Original problem gone
- [ ] No new problems introduced
- [ ] Tests pass
- [ ] Docs updated
- [ ] User confirms (if applicable)

**Output**: Pass/Fail per problem + regression test summary

## Key Decision Points

- **Severity triage**: P0 blocks all work; P1 must fix before exit; P2+ can defer
- **Max iterations**: P0=5, P1=3, P2=2, P3=1 max attempts per problem
- **Escalation**: If max attempts reached → surface as technical debt

## Exit Criteria Details

All must be true:
- All P0 and P1 problems fixed and verified
- P2+ problems either fixed or recorded as technical debt
- No new problems introduced by fixes
- VERIFY step confirms all changes working
- Ready to proceed to next phase
