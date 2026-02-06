---
name: pair
description: "Driver-mode pair programming: you implement, other mounted providers review (ask + reply-via-ask); merge and repeat."
metadata:
  short-description: Pair-programming loop with review
---

# Pair Programming (Multi-Provider)

Use a driver/reviewer-style loop to get to a higher-quality implementation faster:

1. **Plan** (reuse prior `/all-plan` output if it exists)
2. **Implement** (make the code changes)
3. **Review** (ask other mounted providers; receive feedback via reply-via-ask)
4. **Merge** (apply the best feedback)
5. **Repeat** (one more implement→review→merge pass)

Arguments (parsed from `$ARGUMENTS`):
- Required: `requirement`
- Optional: `iterations=1|2` (default `2`)
- Optional: `review_focus=correctness|api|tests|security|perf` (default `correctness`)
- Optional: `skip_plan=0|1` (default `0`)
- Optional: `reviewers=<comma-separated providers>` (default: all mounted providers except the driver)

Note: After requesting review feedback via `ask`, stop and wait for replies via reply-via-ask (don’t continue to merge until feedback arrives).

For the exact workflow and review prompt templates, see `references/flow.md`.
