<!-- tier: remaining reference + implementation notes -->

# EXPLORING - Reference & Implementation

## Relationship to OFFICE-HOURS

OFFICE-HOURS is structured product clarification (targeting requirement structure).
EXPLORING is open-ended discovery (targeting deep thinking).

They can sequence:
- OFFICE-HOURS first to clarify surface needs
- Then EXPLORING to dig into why those needs matter

Or EXPLORING can be triggered directly if user has fuzzy/contradictory thinking from the start.

## Question Type Selection Framework

Choose question type based on user's last answer:

| User Said | Question Type | Why |
|-----------|--------------|-----|
| "Definitely yes" / "Absolutely" | Assumptions | Challenge certainty |
| Plan sounds perfect/complete | Boundaries | Test limits |
| Two conflicting views expressed | Contradictions | Resolve tension |
| "Because...so..." logic | 5-Why | Dig deeper into reasoning |
| Staying in old patterns | Creative possibility | Break constraints |

## Special Case: Exploring a Technical Approach

```
User: "I think we should use microservices"

Round 1 (Assumptions):
"You assume monolith won't work at scale. Is this tested? What if 
we could optimize monolith?"

Round 2 (Boundaries):
"Microservices assume you have DevOps capability. What if team 
is 2 people? Still the right choice?"

Round 3 (Possibilities):
"What if we started monolithic and evolved? Would that change 
your thinking?"
```

## Special Case: Exploring Creativity/Innovation

```
User: "I want to create something revolutionary in education tech"

Round 1 (Essence):
"Why education specifically? Not healthcare, not finance?"

Round 2 (Assumptions):
"You assume current education is broken in X ways. Verified? 
Where's the pain?"

Round 3 (Possibilities):
"What if you combined education with [adjacent domain]? 
Never been tried?"

Round 4 (Potential):
"I notice you keep returning to [theme]. Is this your real passion 
or the idea you think you should pursue?"
```

## Managing Difficult Users

### User resists deep questions
- Acknowledge: "This is deep questioning; it can be uncomfortable"
- Respect boundaries: "We can go lighter if you prefer"
- Option to exit: "Or we can stop here and move forward"

### User keeps surface-level answers
- Gently push: "I'm asking for deeper here. What's the real reason?"
- Offer scaffolding: "Many people have this assumption. Do you?"
- Explicit invitation: "I'm sensing there's more here. Want to go there?"

### User gets defensive
- Reframe: "Not criticizing; I'm curious about your real thinking"
- Normalize: "These questions help surface blind spots; everyone has them"
- Autonomy: "Your call how deep to go"

## Integration with Memory System

If exploring multiple sessions on same topic:
- Store synthesis from previous explorations
- Build on prior discoveries in new sessions
- Avoid re-exploring same ground

## How EXPLORING Feeds Into PLANNING

After EXPLORING completes:
- PLANNING uses refined understanding of core problem
- PLANNING avoids solutions that violate discovered constraints
- PLANNING targets the potential/possibilities uncovered

## Distinction: EXPLORING vs REFINING

- **EXPLORING**: User's thinking is fuzzy/incomplete → uncover real thinking
- **REFINING**: Completed work has bugs/problems → fix the implementation

They're different loops with different purposes.

## Unconscious Constructs: What to Look For

Patterns indicating unconscious thinking:
- User says "I never thought about it that way"
- Contradiction surfaces during questioning
- User discovers they were avoiding something
- User realizes alternative approach suddenly seems viable
- Hidden fear or assumption emerges

These are gold — they're the deep discoveries.

## Example: Exploring a Career Decision

```
User: "I'm thinking about leaving tech to start a non-profit"

Round 1 (Why): "What specifically attracted you to non-profit work?"
→ "Helping people, not just profit"

Round 2 (Assumptions): "You're assuming tech = not helping people. 
But tech can help billions. Is your assumption really true?"
→ [User pauses, realizes tech helped their family]

Round 3 (Boundaries): "If you could help people AND stay in tech, 
would that change your decision?"
→ [New realization about what they really want]

Round 4 (Potential): "What if you built tech FOR non-profits instead 
of leaving tech?"
→ [User sees new possibility: tech founder for social good]

Result: Discovered assumption (tech ≠ helping), limitation (either/or thinking), 
and potential (new career path)
```

## Related Concepts

- **Socratic Method**: See shared preamble for philosophical context
- **Boil the Lake**: Iterative question pattern in shared preamble
- **OFFICE-HOURS**: Structured clarification (complements EXPLORING)
- **THINKING**: Uses insights from EXPLORING to make smarter decisions
