---
name: ask
description: Send via ask, end turn immediately; use when user explicitly delegates to Claude or Codex; NOT for questions about the providers themselves.
metadata:
  short-description: Ask AI provider asynchronously
---

# Ask Provider (Async, Send-Only)

Send the user's request to the specified provider via `ask`. This is **send-only**: it prints a `req_id` and exits immediately.

## Usage

The first argument must be the provider name:
- `codex`
- `claude`

## Execution (MANDATORY)

```bash
ask --session "${CQ_SESSION:-default}" $PROVIDER <<'EOF'
$MESSAGE
EOF
```

## Rules

- After running the command, say "[Provider] processing..." and immediately end your turn.
- Do not wait for results or check status in the same turn.
- The command prints a `req_id` for correlation.

## Reply-via-ask (Bidirectional)

If you receive a request that begins with `CQ_REQ_ID: <req_id>`, treat it as a task from **Claude**.

When done, reply back to Claude via `ask`:
```bash
ask --session "${CQ_SESSION:-default}" claude --reply-to "$REQ_ID" --caller codex <<'EOF'
<your result here>
EOF
```

## Examples

`/ask claude <message>`

## Notes

- If it fails, check backend health with `ping <provider>`.
