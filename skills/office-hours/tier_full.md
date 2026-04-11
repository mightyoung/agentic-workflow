<!-- tier: ~45% full methodology + commands -->

# OFFICE HOURS - Full Methodology

## False-Need Pattern Library

### 1. Over-Optimization
**Signal**: "System must support 1M concurrent", "needs elastic scaling", "must handle 10x growth"
**Reality check**: How many actual users? When is scale needed?
**Response**: "Let's start with real numbers. How many users do you have now? When do you expect to hit the scale challenge?"

### 2. Speculation Pattern
**Signal**: "Users might want...", "I think users will...", "We should support..."
**Reality check**: Data or feedback? Or assumption?
**Response**: "Do you have user feedback or data for this? Or is this an assumption we should validate first?"

### 3. Scope Creep Pattern
**Signal**: "Adding XX would make it better", "Competitor has XX", "We should also include..."
**Reality check**: Core value vs nice-to-have?
**Response**: "If we could only do ONE thing, what would have the biggest user impact? Let's call that P0."

### 4. Tech-Driven Pattern
**Signal**: "Use blockchain", "Must be microservices", "Need GraphQL"
**Reality check**: Business goal first, tech second?
**Response**: "What's the business goal? Tech is a means to achieve it. Let's start with the goal."

### 5. Perfectionism Pattern
**Signal**: "Want to build the best", "Perfect solution", "Complete feature"
**Reality check**: MVP vs perfection?
**Response**: "What if we built an MVP first, got user feedback, then iterated? Often better than building perfect in one shot."

### 6. Competition Anxiety Pattern
**Signal**: "Competitor has XX feature", "Need feature parity", "Everyone is doing..."
**Reality check**: Does user really need it, or is it FOMO?
**Response**: "What does YOUR user actually need? Let's focus on their real problems, not feature parity."

## Question Categories

### 1. Target Users
```
- Who is the primary user? (role/persona)
- Secondary users? (support team? admins?)
- Skill level? (technical? non-technical?)
- Company size? (startup? enterprise?)
- Geographic region? Industry?
```

### 2. Use Scenarios
```
- In what situation does user use this?
- Step-by-step: what's the main workflow?
- How often used? (daily? monthly?)
- What tools/systems does it connect with?
- Where (office? remote? field?)?
```

### 3. Success Metrics
```
- How do you measure success?
- Quantitative: revenue? adoption? engagement?
- Qualitative: user satisfaction? NPS?
- Timeline: when should success be achieved?
- Threshold: what counts as "success"?
```

### 4. Constraints & Risks
```
- Technical constraints? (compatibility? performance?)
- Budget constraint? Timeline constraint?
- Team skills? Existing infrastructure?
- What's the biggest risk? Failure mode?
- Regulatory/compliance issues?
```

### 5. MVP Thinking
```
- What's the simplest version that delivers value?
- If you could only build ONE feature, what is it?
- What's absolutely necessary vs nice-to-have?
- Can you launch with less and iterate?
- What would users be happy with v1?
```

## Deep-Dive Socratic Extensions (Step 4)

### Assumption Challenge
```
You mentioned [idea/approach]. This assumes [extracted assumption].

Questions:
- Is this assumption really true?
- What if this assumption was wrong?
- What would happen then?
- Has anyone disagreed with this assumption? Why?
```

### Boundary Testing
```
You described [approach] for [scenario].

But what if conditions changed:
- Users 100x larger?
- Timeline 1/10?
- Team completely different tech background?
- Budget 1/3 of current?

Would your approach still work?
```

### Contradiction Exploration
```
You said [view A], but I also heard [view B].

These seem to have tension. How do you reconcile?
- Which one is really true?
- Under what conditions would one vs other be true?
```

### Root Cause (5-Why)
```
Let's dig on [topic]:

Why1: [answer to first why]
Why2: [based on why1 answer]
Why3: [based on why2 answer]
Why4: [based on why3 answer]
Why5: [based on why4 answer]

Root cause: [pattern emerges]
```

### Creative Possibility
```
Based on our discussion, I see a potential direction: [direction].

Have you considered:
- Combining [A] and [B] together?
- Approaching from [completely different angle]?
- What would it look like if we...?
```

## Product Clarification Document Template

```markdown
# Product Clarification - [Project Name]

## Original Idea
> [User's original description]

## Real Problem
> [Core problem you identified]

## Target Users
- Primary: [description]
- Secondary: [description]
- Key characteristics: [list]

## Use Scenarios
- Scenario 1: [detailed description]
- Scenario 2: [detailed description]
- Main workflow: [step-by-step]

## Success Metrics
- Quantitative: [metric + threshold]
- Qualitative: [satisfaction metric]
- Timeline: [when?]

## MVP Scope

### Must Have (P0)
- [ ] Feature/capability 1
- [ ] Feature/capability 2

### Nice to Have (P1)
- [ ] Feature/capability 3
- [ ] Feature/capability 4

### YAGNI (Skip for Now)
- [ ] Feature/capability 5
- [ ] Feature/capability 6

## Risks & Constraints
- Risk 1: [description, mitigation]
- Constraint 1: [description]
- Technical challenge: [description]

## Open Questions
- [ ] Question 1: [if not yet answered]
- [ ] Question 2: [if not yet answered]

## Completeness Score
[1-10 scale: 1=vague, 4=initial direction, 7=sufficient, 10=complete]
```

## AskUserQuestion Format

After generating clarification, use AskUserQuestion to confirm:

```markdown
## Re-ground
- **Original idea**: [user's description]
- **Identified problem**: [core problem]
- **Proposed clarifications**: [main points]

## Simplify
Your idea is: [simple 1-sentence description].

Before coding, I need to confirm a few key points:

**Question A**: [Key question]
- If yes → [implication]
- If no → [implication]

**Question B**: [Key question]
- Analogy: [comparison]

## Recommend
**Recommend**: Clarify [most important question] first.
**Why**: It's the foundation for all subsequent decisions.
**Completeness**: 6/10 — need user input to proceed.

## Options
A) Answer questions, then continue
   - Pro: ensure right direction
   - Con: takes time

B) Skip clarification, tell me specifics, jump to PLANNING
   - Pro: fast start
   - Con: may build wrong thing

C) Cancel, I need more time
   - Reason: need to think more
```

## Relationship to Other Phases

| Transition | When | Why |
|-----------|------|-----|
| OFFICE-HOURS → PLANNING | User confirms product direction | Ready to build plan |
| OFFICE-HOURS → EXPLORING | Need deeper dive into thinking | Fuzzy/contradictory requirements |
| OFFICE-HOURS → ROUTER | Requirements unclear | Need expert routing |
| User needs more time | BLOCKED | User can't decide yet |

## Completeness Scoring

| Score | Meaning | Example |
|-------|---------|---------|
| 10 | Complete | Users, scenarios, metrics, MVP, risks all clear |
| 7 | Sufficient | Main elements defined, minor details pending |
| 4 | Initial | Core direction clear, many details undefined |
| 1 | Vague | Direction unclear, major rework needed |

## Example: Product Idea → Office Hours

```
User: "I want to build a project management tool for remote teams"

STEP 1: Identify Real Problem
→ Expert POV: "Remote teams" is too broad. What's the REAL problem?
→ Questioning: "Are teams struggling with visibility? Async communication? 
   Timezone coordination? Which is the biggest pain?"
→ Discovery: "Main pain is timezone meetings — 6am for someone, 10pm for someone"

STEP 2: Detect Patterns
→ User says: "Should support 1000 users, scale infinitely"
→ Pattern detected: Over-optimization
→ Challenge: "How many users do you have NOW? When expect to scale?"
→ Answer: "20 users in beta, expecting 200 in 6 months"
→ Action: Design for 200 now, build scalability when needed

STEP 3: Ask Questions
→ Users: Remote engineering teams (2-10 people), distributed globally
→ Scenarios: Daily standup (async), sprint planning (live), retrospectives (async)
→ Success: 80% of sync meetings eliminated, standup time cut in half
→ Constraints: Budget $10k, timeline 3 months
→ MVP: Focus on async standup + meeting scheduler, skip notification system

STEP 4: Socratic Deep-Dive
→ Assumption: "You assume teams WANT async more. Is that true?"
→ Answer: "Actually, they want OPTIONS. Some like sync, some like async"
→ Boundary: "If budget cut to $5k, still possible?"
→ Answer: "We'd drop the video chat, just text + calendar"

STEP 5: Product Clarification Document
→ Generated with user input incorporated

STEP 6: Confirmation
→ User confirms: Core problem (timezone friction), MVP (async standup + scheduler), scope clear
→ Status: DONE → Ready for PLANNING
```
