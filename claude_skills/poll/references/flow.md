# Poll (Multi-Provider Q&A) - Flow

This workflow simulates “ask the room”:
- **You** = Driver (the provider that invoked `/poll`; broadcasts first, drafts its own answer, then ends its turn to collect replies, then synthesizes)
- **Other mounted providers** = Respondents (answer independently; no code changes)

## Inputs

From `$ARGUMENTS`:
- `question`: the question to broadcast
- Optional: `respondents=<comma-separated providers>` (default: all mounted except `{self}`)
- Optional: `format=consensus|list|table` (default: `consensus`)

## Step 0: Detect which providers can respond

Run:
```bash
cq-mounted --session "${CQ_SESSION:-default}"
```

If `cq-mounted` succeeds and returns a `mounted[]` list, define:
- For this skill, `{self} = claude`
- `respondents = mounted - {self}`
- If `respondents=...` is provided, use `respondents = (mounted ∩ requested_respondents) - {self}`

If `cq-mounted` fails (non-zero) or returns invalid/empty output:
- If `respondents=...` is provided, use `respondents = requested_respondents - {self}`
- Otherwise proceed solo

If `respondents` is empty, proceed solo: answer the question yourself and clearly label it as a solo response.

Generate a fresh request id (32-hex) you can match against later. Use it as the `req_id` for all broadcast `ask` calls (the `CQ_REQ_ID: ...` line at the top of each prompt):
- `CQ_REQ_ID = <32-hex id>` (example: `66094bea382bbce94019e3ea9218ac81`)
  - Generate: `CQ_REQ_ID="$(python -c 'import secrets; print(secrets.token_hex(16))')"`

## Step 1: Clarify if needed

If `question` is empty or missing, ask the user to provide a question before proceeding.

If the question is ambiguous, ask the user 1-2 clarifying questions (option-based if possible) before broadcasting.

## Step 2: Broadcast question (ask)

Send one request per respondent.

### Prompt template (use as-is)

Template:
```
You are responding to a multi-provider poll. Provide an answer only — do not invoke `/poll`, `/pair`, or `/all-plan`, and do not implement changes.

When you're done, send your answer back to the poll driver via reply-via-ask:
1) Copy the `CQ_REQ_ID: ...` line at the top of this message (added automatically by `ask`)
2) Run:
   ask --session "${CQ_SESSION:-default}" claude --reply-to <CQ_REQ_ID> --caller <your provider> <<'EOF'
   <your answer>
   EOF
Do not reply in your own pane; send your answer via `ask --reply-to` so it arrives in the driver's pane.

Question:
<paste question>

Reply with:
1) Answer
2) Confidence: high|medium|low
3) Key assumptions / caveats (bullets)
```

Then run, once per respondent (sequentially; pause ~1s between providers):
```bash
ask --session "${CQ_SESSION:-default}" <provider> --req-id "$CQ_REQ_ID" <<'EOF'
<message>
EOF
```

Note: Don’t worry about how to get the reply yet — just send the request and continue. You’ll collect replies in Step 3 by ending your turn.

## Step 2.5: Driver answer (while waiting)

After broadcasting to respondents, write your own answer **independently** (don’t wait for anyone else, and don’t look at any replies yet):
- Answer
- Confidence: high|medium|low
- Key assumptions / caveats (bullets)

Do not send your driver answer to respondents; broadcast only the question.

## Step 3: Collect answers (reply-via-ask)

Respondents send answers back to your pane via `ask --reply-to ... --caller <provider>`.

Each reply payload should include:
- `CQ_REPLY: <CQ_REQ_ID>`
- `CQ_FROM: <provider>`

This flow is **multi-turn**. To collect replies: end your turn (do not run additional commands). Respondents will send messages back to your terminal (driver pane) via `ask --reply-to`.
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
- Include the driver answer (written independently, before receiving replies) when determining majority consensus (label it clearly as the driver).
- Synthesize objectively even if your own intuition differs from the consensus.

## Output

Use the requested format (default: `consensus`).

### Format: consensus (default)
```
## Poll Results

**CQ_REQ_ID:** <id>
**Question:** <question>
**Driver:** claude
**Respondents asked:** <list>
**Respondents replied:** <list>

### Driver Answer
<your answer> (confidence: <X>)

### Respondent Responses
- <provider>: <answer> (confidence: <X>)

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
