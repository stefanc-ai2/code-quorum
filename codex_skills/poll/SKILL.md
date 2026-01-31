---
name: poll
description: "Broadcast a question to all mounted providers, collect answers, synthesize consensus."
metadata:
  short-description: Multi-provider Q&A synthesis
---

# Poll (Multi-Provider Q&A)

Broadcast the same question to all mounted providers, collect their independent answers, then synthesize a unified response highlighting consensus and disagreements.

How this differs:
- `/poll`: single-round Q&A + synthesis; **no code changes**
- `/pair`: implement + review + merge loop; code changes expected
- `/all-plan`: collaborative planning/clarification to produce a plan (not a single question)

Arguments (parsed from `$ARGUMENTS`):
- Required: `question`
- Optional: `respondents=<comma-separated providers>` (default: all mounted except the driver)
- Optional: `format=consensus|list|table` (default: `consensus`)

Note: `/poll` is intentionally multi-turn. The driver writes its own answer first, then broadcasts to respondents, then stops and waits for replies via reply-via-ask.

Examples:
- `/poll "Should we use Redis or Memcached for sessions?"`
- `/poll "Is this API design idiomatic in Python?" respondents=claude format=list`

For the exact workflow and prompt templates, see `references/flow.md`.
