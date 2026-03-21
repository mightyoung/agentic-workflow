---
name: Contributor Mode
description: User feedback mechanism for improving agentic-workflow
version: 1.0
tags: [contributor, feedback, quality]
---

# Contributor Mode

Contributor Mode is a feedback mechanism that allows users to report issues with agentic-workflow itself, helping improve the core system rather than user applications.

## Trigger Conditions

- Configuration `gstack_contributor` is set to `true`
- Triggered at the end of each major workflow step
- User can opt-in to provide structured feedback

## Timing

Feedback is collected after:
- Task completion (success or failure)
- Workflow step transitions
- Agent execution cycles
- Any significant system interaction

## Scoring Criteria

Rate the experience from 0-10:

| Score | Meaning |
|-------|---------|
| 10 | Perfect - worked exactly as expected |
| 7-9 | Good - minor issues, not blocking |
| 4-6 | Fair - noticeable problems, partially usable |
| 1-3 | Poor - major issues, barely usable |
| 0 | Failed completely - did not work at all |

**Scores below 10 require a reason.**

## Feedback Format Template

```markdown
## Contributor Feedback

**Timestamp:** [ISO 8601 timestamp]
**Workflow/Step:** [Which workflow or step]
**Score:** [0-10]
**Reason (if < 10):** [Explanation of the issue]

### What happened:
[Clear description of the issue]

### What should have happened:
[Expected behavior]

### Severity:
- [ ] Critical - blocks all work
- [ ] High - significantly impacts usability
- [ ] Medium - minor inconvenience
- [ ] Low - cosmetic issue

### Category:
- [ ] Bug - gstack behavior is wrong
- [ ] Docs - documentation doesn't match reality
- [ ] UX - confusing or unintuitive behavior
- [ ] Performance - too slow or resource intensive
- [ ] Feature - missing needed functionality
```

## Worth Submitting

- gstack command failed but should have succeeded
- Documentation contradicts actual behavior
- User input was reasonable but gstack mishandled it
- System behaved inconsistently across similar operations
- Error messages were unclear or misleading
- Workflow steps took excessive time without good reason

## NOT Worth Submitting

- User's application bugs (that's what the app's repo is for)
- Network errors (unless gstack should handle them gracefully)
- Authentication failures on user's external services
- Issues caused by invalid user input that gstack correctly rejected
- Feature requests (use GitHub issues for these)

## Log Location

Feedback is saved to: `~/.gstack/contributor-logs/`

Each submission is stored as a dated log file with the pattern:
`contributor-[YYYY-MM-DD]-[timestamp].md`
