<!-- tier: ~45% full methodology + commands -->

# EXPLORING - Full Methodology

## Entry Criteria (Expanded)

### Explicit Triggers
User says: "I want to explore this idea", "deep dive into", "analyze this", "I'm not sure about this"

### Implicit Triggers
- Fuzzy/incomplete thinking: "I kind of think...", "maybe...", unclear ideas
- Contradictory statements: conflicting views expressed
- Desire for understanding: "I want to understand why...", "what's really..."
- Creative exploration: "What if...", experimental mindset

### Router Keywords
"experiment", "analyze", "I have an idea", "figure out", "deep", "essence", "root cause", uncertainty phrases

## Socratic Question Library

### About "Why"
```markdown
- Why do you believe this?
- What's the foundation of this view?
- If the foundation changed, would your view change?
- What would it take to prove you wrong?
```

### About "Opposites"
```markdown
- When does this view NOT work?
- What's the strongest opposing argument?
- If you were an opponent, what would you point out?
- What are you trying to avoid?
```

### About "Assumptions"
```markdown
- What are you assuming here?
- Can this assumption be challenged?
- What if this assumption didn't hold?
- Would others disagree with this assumption? Why?
```

### About "Self"
```markdown
- What are you least certain about?
- What part worries you most?
- What possibility are you afraid of?
- What haven't you thought through clearly?
```

### About "Possibility"
```markdown
- What alternatives have you tried? Why abandon them?
- Starting from zero, how would you design it?
- What's possible but not yet attempted?
- What's constraining your imagination?
```

## State Management

### Conversation Tracking

```
## Dialogue State

- **Round**: N
- **Explored assumptions**: [list]
- **Found contradictions**: [list]
- **Identified potential**: [list]
- **Blind spots to explore**: [list]
```

### Termination Conditions

End exploring when:
1. **Saturation**: 2-3 consecutive rounds with no new discoveries
2. **User satisfaction**: User declares "I've figured it out"
3. **Depth achieved**: Found at least 1 falsehood, 1 limitation, 1 potential
4. **Max rounds reached**: Default limit of 10 rounds

### Round Depth Limits

| Depth | Max Rounds | Use Case |
|-------|-----------|----------|
| Quick scan | 3 rounds | Time-constrained |
| Standard | 5 rounds | General exploration |
| Deep dig | 10 rounds | Major decisions |

## Output Format

After exploring completes:

```markdown
## EXPLORING Results

### Exploration Summary
- **Rounds**: N
- **Core discoveries**: [list of major findings]

### Falsehoods Found
| Type | Content | User Response |
|------|---------|---|
| Falsehood | [desc] | confirmed/denied |

### Limitations Identified
| Type | Content | User Response |
|------|---------|---|
| Limitation | [desc] | confirmed/denied |

### Potential & Possibilities
| Type | Content | User Response |
|------|---------|---|
| Potential | [desc] | excited/cautious |

### Unconscious Constructs
[Things user hadn't explicitly thought about but emerged through questioning]

### User Confirmation
- [x] Falsehood identification accurate
- [x] Limitation identification accurate
- [ ] Potential findings valid
```

## Integration with Other Phases

### From OFFICE-HOURS → EXPLORING
```
OFFICE-HOURS clarifies requirement → discovers need for deep exploration → EXPLORING
```

### From THINKING → EXPLORING
```
THINKING analyzes options → discovers assumptions to challenge → EXPLORING
```

### From EXPLORING → Next Phase
```
EXPLORING complete + consensus → PLANNING
EXPLORING complete + new issues → REFINING
EXPLORING complete + mature idea → THINKING
```

## Completion Status Protocol

| Status | Meaning | Trigger |
|--------|---------|---------|
| **DONE** | Complete | Saturated or max rounds, user confirms findings |
| **SATURATED** | Saturated | 2-3 rounds no new discoveries |
| **USER_SATISFIED** | User done | User declares exploration complete |
| **BLOCKED** | Blocked | User unwilling to continue deep dive |

## Example: Exploring a Product Idea

```
Opening:
"I want to do an experiment. I'll ask you follow-up questions to uncover 
contradictions, limits, and hidden possibilities. Be as authentic as you can."

User: "I want to build a productivity app for remote teams."

Round 1:
Q1 (Assumptions): "You mentioned 'remote teams'. The assumption is that 
remote work has unique productivity problems. Is this really true? 
What problems specifically?"

Round 2:
Q2 (Boundaries): "You described 'real-time collaboration'. If you had 
100x more users, still works? If you had 1/10 budget, still works?"

Round 3:
Q3 (Contradiction): "You said 'simplicity is key', but you also want 
'rich features'. How do you reconcile?"

...continues until saturation...

Final:
Synthesis of: falsehoods, limitations, possibilities user hadn't considered
```
