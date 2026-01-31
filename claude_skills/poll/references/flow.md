# Poll (Multi-Provider Q&A) - Flow

This workflow simulates “ask the room”:
- **You** = Driver (the provider that invoked `/poll`; broadcasts first, answers too, then synthesizes)
- **Other mounted providers** = Respondents (answer independently; no code changes)

## Inputs

From `$ARGUMENTS`:
- `question`: the question to broadcast
- Optional: `respondents=<comma-separated providers>` (default: all mounted except `{self}`)
- Optional: `timeout_s=<seconds>` (default: `60`)
- Optional: `format=consensus|list|table` (default: `consensus`)

## Step 0: Detect which providers can respond

Run:
```bash
ccb-mounted
```

If `ccb-mounted` succeeds and returns a `mounted[]` list, define:
- For this skill, `{self} = claude`
- `respondents = mounted - {self}`
- If `respondents=...` is provided, use `respondents = (mounted ∩ requested_respondents) - {self}`

If `ccb-mounted` fails (non-zero) or returns invalid/empty output:
- If `respondents=...` is provided, use `respondents = requested_respondents - {self}`
- Otherwise proceed solo

If `respondents` is empty, proceed solo: answer the question yourself and clearly label it as a solo response.

Generate a fresh correlation id (32-hex) you can match against later. Use it as the `req_id` for all broadcast `ask` calls:
- `POLL_ID = <32-hex id>` (example: `66094bea382bbce94019e3ea9218ac81`)
  - Generate: `POLL_ID="$(python -c 'import secrets; print(secrets.token_hex(16))')"`
- `POLL_DRIVER = {self}` (the provider that invoked `/poll`)

## Step 1: Clarify if needed

If `question` is empty or missing, ask the user to provide a question before proceeding.

If the question is ambiguous, ask the user 1-2 clarifying questions (option-based if possible) before broadcasting.

## Step 2: Broadcast question (ask)

Send one request per respondent.

### Prompt template (use as-is)

Template:
```
CCB_REQ_ID: <paste id>

You are responding to a multi-provider poll. Provide an answer only — do not invoke `/poll`, `/pair`, or `/all-plan`, and do not implement changes.

When you're done, send your answer back to the poll driver via reply-via-ask:
1) Copy the `CCB_REQ_ID: <id>` line at the top of this message
2) Run:
   ask claude --reply-to <id> --caller <your provider> --no-wrap <<'EOF'
   <your answer>
   EOF
   # (or, using env vars)
   # CCB_CALLER=<your provider> ask claude --reply-to <id> --no-wrap <<'EOF'
   # <your answer>
   # EOF
Do not reply in your own pane; send your answer via `ask --reply-to` so it arrives in the driver's pane.

POLL_ID:
<paste id>

POLL_DRIVER:
claude

Question:
<paste question>

Reply with:
1) Answer (2-8 sentences)
2) Confidence: high|medium|low
3) Key assumptions / caveats (bullets)
```

Then run, once per respondent (sequentially; pause ~1s between providers):
```bash
CCB_CALLER=claude CCB_REQ_ID="$POLL_ID" ask <provider> --no-wrap <<'EOF'
<message>
EOF
```
Equivalent (flags):
```bash
ask <provider> --no-wrap --req-id "$POLL_ID" <<'EOF'
<message>
EOF
```

## Step 2.5: Driver answers (in parallel)

After broadcasting to respondents, answer the question yourself **while they work**.

Use the same structure as the respondent template so your answer can be synthesized consistently:
- Answer (2-8 sentences)
- Confidence: high|medium|low
- Key assumptions / caveats (bullets)

Notes:
- On Windows native, avoid heredocs; use the `/ask` skill’s Windows instructions.
  - PowerShell example: `$env:CCB_CALLER="claude"; $env:CCB_REQ_ID=$POLL_ID; Get-Content $msgFile -Raw | ask <provider> --no-wrap`
  - cmd.exe example: `set CCB_CALLER=claude && set CCB_REQ_ID=%POLL_ID% && type %MSG_FILE% | ask <provider> --no-wrap`

## Step 3: Collect answers (reply-via-ask)

Respondents send answers back to your pane via `ask --reply-to ... --no-wrap`.

Each reply payload should include:
- `CCB_REPLY: <POLL_ID>`
- `CCB_FROM: <provider>`

Do not block on polling/sleeps. Continue working and incorporate answers as they arrive. If nothing arrives within `timeout_s`, proceed with partial responses and note which respondents did not reply.
Do not scrape panes to collect answers (forbidden): no `wezterm cli get-text`, no `tmux capture-pane`, etc. The only supported mechanism is reply-via-ask.

## Step 4: Synthesize

Create a combined answer with:
- A “consensus” section (or “no consensus”)
- Disagreements/outliers (by provider)
- Caveats & assumptions (deduped)
- Action items / follow-ups (only if needed)

Synthesis heuristics:
- If a majority agrees on the core answer, report as consensus.
- If split, report vote counts and the main trade-off axes.
- Prefer high-confidence answers when weighing ambiguous splits.
- Include the driver answer when determining majority consensus (label it clearly as the driver).
- Synthesize objectively even if the driver’s answer differs from the consensus.

## Output

Use the requested format (default: `consensus`).

### Format: consensus (default)
```
## Poll Results

**POLL_ID:** <id>
**Question:** <question>
**Driver:** claude
**Respondents asked:** <list>
**Respondents replied:** <list>
**Respondents timed out/stale:** <list or "none">

### Driver Answer
<your answer> (confidence: <X>)

### Consensus
<synthesized answer (or “No clear consensus”)>

### Disagreements / Outliers
- <provider>: <summary> (confidence: <X>)

### Caveats & Assumptions
- <bullet>

### Action Items (optional)
- <bullet>
```

### Format: list
```
## Poll Results

**Question:** <question>

### Responses
0) claude (driver) (confidence: <X>)
   <answer>

1) <provider> (confidence: <X>)
   <answer>

### Synthesis
<1-3 sentence synthesis>
```

### Format: table
```
## Poll Results

| Provider | Answer (summary) | Confidence | Key caveat |
|----------|------------------|------------|------------|
| claude (driver) | ...        | ...        | ...        |
| ...      | ...              | ...        | ...        |

**Consensus:** <short>
```

Important: Do NOT make code changes, and do NOT commit or push unless the user explicitly asks.
