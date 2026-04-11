<!-- tier: ~15% core methodology -->

# REFINING - Core Methodology

## Method Skeleton

- **Phase purpose**: Close the feedback loop — discover problems, analyze root causes, fix errors, verify results
- **Entry trigger**: User requests iteration/improvement/optimization, other phases find unsolvable problems, tests/review fail, or explicit `/refining` command
- **Core method**: Four-step cycle (DISCOVER → ANALYZE → FIX → VERIFY) that repeats until saturation or P0/P1 problems resolved
- **Key principle**: Small steps, tight feedback loops; don't start fixing until root cause diagnosed
- **Hard-gate exit**: All P0/P1 problems fixed; P2+ problems planned for later iteration; VERIFY confirms no new problems introduced

## Feedback Loop State Machine

```
DISCOVER (find problems)
    ↓
ANALYZE (diagnose root cause)
    ↓
FIX (execute solution)
    ↓
VERIFY (confirm fix works)
    ↓
[Loop until problems resolved or resources exhausted]
```

## Iron Laws

1. **Don't hide problems**: Find and record everything; never ignore
2. **Diagnose before fixing**: Understand root cause before implementing solution
3. **Small steps fast**: Each fix small and testable; easy to revert if wrong
4. **Verify always**: Never assume fix worked; always verify
