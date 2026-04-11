<!-- tier: ~30% core process flow -->

# OFFICE HOURS - Core Process

## Entry Criteria

Office Hours phase begins when:
1. **Explicit trigger**: User describes product idea or feature need:
   - "I want to build a..."
   - "Help me develop a..."
   - "Product concept is..."
   - "Need clarification on requirements"
2. **Implicit trigger**: Task involves unclear/incomplete/misaligned requirements
3. **Keywords**: 帮我做, 帮我开发, 我想做, 产品概念, 产品设计, 产品思路, 不知道怎么开始, 不确定

## Core Process Steps

**Step 1: Identify Real Problem**
Using expert simulation (senior PM), understand the true problem:
- What problem is user trying to solve? (not their proposed solution)
- What's the essence of the problem?
- How do they currently solve it?
- What makes success?

**Output format**:
```
User's original idea: [description]
Real problem behind it: [extracted core problem]
Current solution: [how they solve it now]
```

**Step 2: Detect False-Need Patterns**
Before deep inquiry, identify common pseudo-requirements:

| Pattern | Signal | Response |
|---------|--------|----------|
| Over-optimization | "support 1M concurrent", "elastic scaling" | Ask: actual users now? |
| Speculation | "users might need...", "I think..." | Ask: actual feedback or data? |
| Scope creep | "add XX feature, would be better", "competitor has it" | Ask: core value vs nice-to-have |
| Tech-driven | "blockchain implementation", "must be microservices" | Ask: business goal? Tech is means |
| Perfectionism | "do it best", "perfect solution" | Ask: MVP scope? Iterate? |
| Competition anxiety | "competitor has XX", "need parity" | Ask: what does user really need? |

**Step 3: Ask Right Questions**
Structured Q&A to clarify:

1. **Target users**: Who uses this? Skills? Demographics?
2. **Use scenarios**: When/where used? Frequency? Flow?
3. **Success metrics**: How measure success? Data? User satisfaction?
4. **Constraints & risks**: Tech constraints? Budget/time? Biggest risk?
5. **MVP thinking**: Minimum viable version? Must-have vs nice-to-have? One feature focus?

**Step 4 (Optional): Deep-Dive Socratic Questions**
After structure, optionally use Socratic method (5-Why, assumptions, boundaries, contradictions) to uncover deeper thinking.

**Step 5: Generate Product Clarification**
Output structured document with: original need, real problem, users, scenarios, success metrics, MVP scope, risks, open questions.

**Step 6: Get User Confirmation**
Use AskUserQuestion format to confirm direction before proceeding.

## Key Decision Points

- **Pseudo-need detection**: Flag for re-examination in Step 3
- **MVP scope**: Distinguish P0 (must), P1 (nice), YAGNI (skip)
- **Success definition**: Vague vs measurable metrics

## Exit Criteria Details

All must be true:
- Core product goal clarified and user confirms
- Target users and scenarios defined
- Success criteria explicitly stated
- MVP scope boundary set (must/nice/skip)
- Major risks identified
- Ready to proceed to PLANNING or next phase
