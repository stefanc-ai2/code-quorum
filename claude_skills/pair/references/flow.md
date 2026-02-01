# Pair Programming (Multi-Provider) - Flow

This workflow simulates pair programming with:
- **You** = Driver (the provider that invoked `/pair`; edits code, runs tests, writes the final summary)
- **Other mounted providers** = Navigators (critique, edge cases, alternative designs)

## Inputs

From `$ARGUMENTS`:
- `requirement`: what to build/fix/refactor
- Optional: `iterations=1|2` (default: `2`)
- Optional: `review_focus=correctness|api|tests|security|perf` (default: `correctness`)
- Optional: `skip_plan=0|1` (default: `0`)
- Optional: `reviewers=<comma-separated providers>` (default: all mounted providers except `{self}`)

## Step 0: Detect which providers can review

Run:
```bash
cq-mounted
```

If `cq-mounted` succeeds and returns a `mounted[]` list, define:
- For this skill, `{self} = claude`
- `reviewers = mounted - {self}` (skip yourself)
- If `reviewers=...` is provided, use `reviewers = (mounted ∩ requested_reviewers) - {self}`

If `cq-mounted` fails (non-zero) or returns invalid/empty output:
- If `reviewers=...` is provided, use `reviewers = requested_reviewers - {self}`
- Otherwise proceed solo

If `reviewers` is empty, proceed solo but still do the same internal checklist.
If `reviewers` is non-empty, generate a stable 32-hex `req_id` per reviewer (e.g. `PAIR_REVIEW_REQ_ID_<provider>`) and use it as the `ask` request id (`--req-id ...` or `CQ_REQ_ID=...`). `ask` will include a `CQ_REQ_ID: <id>` line at the top automatically so the reviewer can reply via reply-via-ask.

## Step 1: Plan

If the conversation already contains a plan/design brief (e.g. after `/all-plan`), reuse it.
If `skip_plan=1`, skip this step and proceed to implementation.
Otherwise produce a compact plan:

- Goal / non-goals
- Implementation sketch (key files/modules)
- Risks / assumptions
- Test plan (what to run / what to add)

Proceed with reasonable assumptions when required, but call them out explicitly.

## Step 2: Implementation (Driver pass)

Implement the plan with a bias toward:
- Small, reviewable changes
- Clear errors and edge-case handling
- Minimal scope (fix root cause; avoid drive-by refactors)

Run the most relevant local validations available (tests and/or build checks).

## Step 3: Request navigator feedback (ask)

Send one request per reviewer.

### Review prompt template (use as-is)

Provide reviewers with:
- The requirement
- A short change summary (3-6 bullets)
- Key files touched (paths)
- Any open questions / tradeoffs

Template:
```
You are my pair-programming navigator (reviewer).
Provide feedback only — do not invoke `/pair` and do not implement changes.

When you're done, send your feedback back to me via reply-via-ask:
1) Copy the `CQ_REQ_ID: ...` line at the top of this message
2) Run:
   ask claude --reply-to <id> --caller <your provider> <<'EOF'
   <your feedback>
   EOF
Do not reply in your own pane; send feedback via `ask --reply-to` so it arrives in my pane.

PAIR_DRIVER:
claude

Requirement:
<paste requirement>

What I changed:
- <bullet>
- <bullet>

Key files:
- <path>
- <path>

Please review for:
1) correctness/edge cases
2) API/UX clarity (errors/messages)
3) tests (what’s missing?)
4) maintainability (simpler alternatives)

Reply with:
- Must-fix issues
- Should-fix improvements
- Nice-to-have ideas
```

Then run `ask <provider> --req-id "<id>"` (using the platform-appropriate invocation for your environment).
Reviewers should use `--caller <your provider>` on `--reply-to` so reply payloads include the correct `CQ_FROM`.

If you need a raw example for Linux/macOS:
```bash
ask <provider> --req-id "<id>" <<'EOF'
<message>
EOF
```

After sending review requests to all reviewers: **stop immediately**. Do not continue implementation or merging until feedback arrives via reply-via-ask.

## Step 4: Collect feedback (reply-via-ask)

Reviewers will send feedback back to your pane via `ask --reply-to ... --caller <provider>`.

Each reply payload should include:
- `CQ_REPLY: <req_id>` (the req_id from the original `ask`)
- `CQ_FROM: <provider>`

This step is multi-turn. To get the feedback: end your turn and wait (do not run additional commands). Reviewers will send messages back to your terminal (driver pane) via `ask --reply-to`.
Do not scrape panes to collect feedback (forbidden): no `wezterm cli get-text`, no `tmux capture-pane`, etc. The only supported mechanism is reply-via-ask.

## Step 5: Digest and merge

Convert feedback into an actionable list:

| Category | Action | Criteria |
|---|---|---|
| **Must-fix** | Always apply | Bugs, security/correctness, data integrity, broken tests/builds, backwards-compat breaks |
| **Should-fix** | Apply if quick | Clear improvement, low risk, doesn’t expand scope |
| **Nice-to-have** | Defer | Preference-only, refactors, optional ergonomics, future work |

Rules:
- Apply all Must-fix items.
- Apply Should-fix items if cost is low and they don’t expand scope.
- Record Nice-to-have items as follow-ups; don’t expand scope mid-task.
If reviewers disagree, default to the more conservative change or ask the user to pick.

After merging, re-run the relevant validations.

## Step 6: Repeat once (iteration 2)

Do a second pass with a different emphasis:
- If iteration 1 focused on correctness, ask iteration 2 reviewers to focus on tests and maintainability (or vice-versa).

Use a shorter prompt that highlights what changed since the first review.

### Iteration 2 quick review template

```
You are my pair-programming navigator (iteration 2).
Provide feedback only — do not invoke `/pair` and do not implement changes.

When you're done, send your feedback back to me via reply-via-ask:
1) Copy the `CQ_REQ_ID: ...` line at the top of this message
2) Run:
   ask claude --reply-to <id> --caller <your provider> <<'EOF'
   <your feedback>
   EOF

PAIR_DRIVER:
claude

What changed since iteration 1:
- <bullet>
- <bullet>

Please focus on:
1) tests/coverage gaps
2) maintainability/simpler alternatives

Reply with Must-fix / Should-fix / Nice-to-have.
```

## Output

At the end:
- Driver: `claude`
- Reviewers: list providers you actually asked (mounted/filtered)
- Summarize what changed
- Summarize feedback incorporated
- Note any remaining risks / follow-ups
- Provide exact test commands run

**Important:** Do NOT commit or push unless the user explicitly asks. Leave git operations to the user by default.
