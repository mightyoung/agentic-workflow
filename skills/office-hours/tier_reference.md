<!-- tier: remaining reference + implementation notes -->

# OFFICE HOURS - Reference & Implementation

## Relationship to Other Phases

### Upstream: ROUTER
OFFICE-HOURS is often the natural output of ROUTER.
When router detects "product decision needed" → OFFICE-HOURS starts.

### Downstream: PLANNING
OFFICE-HOURS output (clarified product spec) → PLANNING builds the implementation plan.

### Upstream Alternative: THINKING
If user has already thought deeply → skip OFFICE-HOURS, go direct to THINKING.

### Alternative Path: EXPLORING
If user's thinking is fuzzy/contradictory → EXPLORING first (deep dive), then OFFICE-HOURS (clarify).

## Distinction: OFFICE-HOURS vs EXPLORING

| Aspect | OFFICE-HOURS | EXPLORING |
|--------|--------------|-----------|
| Purpose | Clarify product requirements | Dig into deep thinking |
| Scope | Structured Q&A on product elements | Open-ended Socratic method |
| Output | Product spec document | Synthesis of insights |
| When use | User has product idea but it's vague | User's thinking is fuzzy/contradictory |
| Next step | → PLANNING | → THINKING or OFFICE-HOURS |

They can sequence or run independently:
- **Shallow need clarification?** → OFFICE-HOURS
- **Deep thinking exploration?** → EXPLORING
- **Both?** → EXPLORING first, then OFFICE-HOURS

## Expert Simulation Details

**Role**: Senior Product Manager
**Experience**: 10+ years in user research, product strategy, startup experience
**Worldview**: 
- User's real problem > user's proposed solution
- Data > assumptions
- MVP > perfection
- Iteration > big bang
- Talk to users > hypothesize

**Method**: 5-Why analysis
**Mantra**: "Get to root cause; don't treat symptoms"

## Anti-Patterns to Avoid

### Anti-Pattern 1: Following Proposed Solution Blindly
**Wrong**: User says "build a blockchain app" → you ask blockchain tech questions
**Right**: User says "build a blockchain app" → you ask "what PROBLEM does blockchain solve here?"

### Anti-Pattern 2: Accepting Pseudo-Requirements
**Wrong**: User says "support 1M users" → you start thinking about infrastructure
**Right**: User says "support 1M users" → you ask "when? with what budget?"

### Anti-Pattern 3: Skipping MVP Definition
**Wrong**: Understanding all requirements, starting implementation
**Right**: Define MVP scope FIRST, build MVP, get feedback, iterate

### Anti-Pattern 4: Not Documenting Decisions
**Wrong**: Have great conversation, move to PLANNING, forget details
**Right**: Document conversation → product_clarification.md → shared reference

## How to Detect If OFFICE-HOURS Is Needed

**Signals that OFFICE-HOURS is needed**:
- [ ] User describes an idea but hasn't deeply thought it through
- [ ] Multiple conflicting views on what to build
- [ ] "I don't know where to start" or "not sure what's most important"
- [ ] Requirements are vague (lots of "maybe", "probably")
- [ ] Success criteria undefined or contradictory
- [ ] Scope feels unbounded (feature creep risk)

**Signals to skip OFFICE-HOURS** (user already clear):
- [ ] User has written spec/requirements doc
- [ ] Success metrics are explicit and measurable
- [ ] User can articulate MVP scope clearly
- [ ] Similar product exists; user is building variant

## Role Play: When to Use Expert Simulation vs Direct Advice

**Use expert simulation** when:
- Product domain is new to you
- User hasn't thought deeply
- Need to build legitimacy through expertise
- Exploring non-obvious possibilities

**Use direct advice** when:
- User is already expert; just needs implementation help
- Time is critical; skip exploration
- You have specific domain expertise user needs

## Interaction Tips

### Tip 1: "Comfortable Silence"
Don't fill pauses. After asking a question, wait. User will elaborate.

### Tip 2: "Tell Me More"
When answer is interesting, probe deeper: "Tell me more about that."

### Tip 3: "Play Devil's Advocate"
When user sounds certain, challenge gently: "What if that assumption was wrong?"

### Tip 4: "Reflect Back"
Summarize what you heard: "So if I understand, you're trying to..."

### Tip 5: "Normalize Uncertainty"
Many users feel embarrassed about not having all answers.
"This is totally normal. Most products start fuzzy. That's what clarification is for."

## Example Flow: Vague Idea → Clear Spec

```
User: "I want an AI coding assistant"

VAGUE. Need OFFICE-HOURS.

Step 1: Real Problem
Q: "What specific coding problems frustrate you?"
A: "Writing tests takes forever"
→ Real problem: Test generation, not "general AI assistant"

Step 2: Pattern Detection
Q: "How many developers would use this?"
A: "Everyone should, right? Like a trillion potential users"
→ Pattern: Over-optimization
→ Challenge: "Let's start with your team. How many? What skills?"

Step 3: Structured Questions
Q: "Walk me through a test-writing session. When stuck?"
A: [detailed description of workflow]
→ Use scenario: writing unit tests for async functions

Q: "How do you measure success?"
A: [vague answers]
→ Help clarify: "80% test coverage in 1/3 the time?"

Q: "What's MVP?"
A: [realizes hadn't thought about it]
→ Together define: "MVP = suggest test cases based on code"
→ "Later: auto-generate, run tests, fix failures"

Step 4: Deep Dive (Optional)
Q: "You assume tests are the main problem. What else slows down dev?"
A: [discovers debugging is actually bigger pain]
→ Recalibration: maybe debugging feature should be P0?

Step 5: Product Clarification
Document everything: users, scenarios, metrics, MVP, risks

Step 6: Confirm
Show user doc. "Does this match what you're thinking?"
A: "Yes, but I also want..."
→ Adjust: update doc, confirm again

Result: Vague "AI coding assistant" → Clear "AI-assisted test case suggestion tool"
Ready for PLANNING.
```

## Integration with Memory System

Store product learnings:
- Problem type → user patterns
- Domain-specific questions that work well
- Effective pseudo-need detection patterns

Example memory:
```
Key: "product-clarification-best-practices"
Value: "For tech product ideas: always ask 'what's the actual pain?' 
before 'what features?'. 80% of proposals are over-engineered."
```

## Handling Difficult Cases

### User Can't Articulate Problem
- Offer examples: "Other teams struggle with X, Y, Z. Any resonant?"
- Suggest observation: "Can we talk to your intended users?"
- Permission to defer: "Let's come back to this when clearer"

### User Wants Everything (Scope Creep)
- Reality check: "If you had to pick ONE thing, what's it?"
- Reframe: "What's MVP? What's v2? What's v5?"
- Commit: "We'll build MVP, launch, iterate. Unrealistic to do all at once"

### User Changes Direction Mid-Clarification
- Normal: "Product ideas evolve. Let's update our document."
- Opportunity: "What triggered the shift? New insight?"
- Incorporate: "So new direction is [new idea]. Let me clarify that..."

## Output Artifacts

### Primary: product_clarification.md
- Location: Project root or session directory
- Reusable: Input to PLANNING phase
- Updates: Can evolve as understanding deepens

### Secondary: Conversation Notes
- Capture interesting questions / discoveries
- Use for pattern memory / future reference

## Completeness Scoring Explained

**Score 10 = "Complete"**
- ✓ Users fully defined
- ✓ Scenarios cover main workflows
- ✓ Metrics explicit and measurable
- ✓ MVP vs future features clear
- ✓ Risks identified
→ Ready for PLANNING with high confidence

**Score 7 = "Sufficient"**
- ✓ Main elements defined
- ○ Some details pending (e.g., edge cases)
- ○ User can answer if needed
→ Proceed to PLANNING; clarify details as they arise

**Score 4 = "Initial"**
- ✓ General direction clear
- ○ Many specifics undefined
- ○ User still thinking things through
→ Can proceed, but expect course corrections

**Score 1 = "Vague"**
- ○ Direction itself unclear
- ○ Major contradictions exist
- ○ Needs significant rework
→ Do more OFFICE-HOURS before PLANNING
