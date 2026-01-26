---
name: ask
description: Async via ask, end turn immediately; use when user explicitly delegates to any AI provider (gemini/codex/opencode/droid); NOT for questions about the providers themselves.
metadata:
  short-description: Ask AI provider asynchronously
---

# Ask AI Provider (Async)

Send the user's request to specified AI provider asynchronously.

## Usage

The first argument must be the provider name. The message MUST be provided via stdin
(heredoc or pipe), not as CLI arguments, to avoid shell globbing issues:
- `gemini` - Send to Gemini
- `codex` - Send to Codex
- `opencode` - Send to OpenCode
- `droid` - Send to Droid

## Execution (MANDATORY)

```bash
CCB_CALLER=droid ask $PROVIDER <<'EOF'
$MESSAGE
EOF
```

## Rules

- After running the command, say "[Provider] processing..." and immediately end your turn.
- Do not wait for results or check status in the same turn.
- The task ID and log file path will be displayed for tracking.

## Examples

- `/ask gemini What is 12+12?` (send via heredoc)
- `CCB_CALLER=droid ask gemini <<'EOF'`
  `What is 12+12?`
  `EOF`

## Notes

- If it fails, check backend health with the corresponding ping command (`ping <provider>` (e.g., `ping gemini`)).
