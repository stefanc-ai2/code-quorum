---
name: ask
description: Send via ask, end turn immediately; use when user explicitly delegates to Codex; NOT for questions about the providers themselves.
metadata:
  short-description: Ask AI provider asynchronously
---

# Ask Provider (Async, Send-Only)

Send a request to a provider via `ask`. This is **send-only**: it prints a `req_id` and exits immediately.

## Usage

The first argument must be the provider name, followed by the message:
- `codex` - Send to Codex
- `claude` - Send to Claude (rare; usually you are Claude)

## Execution (MANDATORY)

```bash
Bash(CCB_CALLER=claude ask $PROVIDER <<'EOF'
$MESSAGE
EOF)
```

## Rules

- After running the command, say "[Provider] processing..." and immediately end your turn.
- Do not wait for results or check status in the same turn.
- The command prints a `req_id` for correlation.

## Reply-via-ask (Bidirectional)

If you receive a request that begins with `CCB_REQ_ID: <req_id>`, treat it as a task from **Codex**.

When done, reply back to Codex via `ask`:
```bash
Bash(ask codex --reply-to "$REQ_ID" --caller claude --no-wrap <<'EOF'
<your result here>
EOF)
```

## Examples

- `/ask codex Refactor this code`

## Notes

- If it fails, check backend health with `ping <provider>` (e.g., `ping codex`).
