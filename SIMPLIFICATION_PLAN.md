# CCB Simplification Plan: Claude + Codex Only (Unix-only, No MCP, No `pend`, No daemons)

## Goal

Simplify Claude Code Bridge from a 5-provider, multi-platform system to a minimal 2-provider (Claude + Codex) solution for **macOS + Linux only** (no Windows, no WSL), with **pure-async `ask`** and **no `pend`**.

Additionally: **remove MCP integration** (delegation server + droid setup commands) since it’s out of scope.

New architecture decision: `ask` sends directly to the target tmux/WezTerm pane (no `askd`/`caskd`/`laskd`), and results come back only via reply-via-ask (`--reply-to`).

**Estimated reduction:** ~4,500+ lines of code, 20+ files deleted (likely more once docs/tests/installers are pruned)

---

## Summary of Changes

| Category | What's Removed |
|----------|----------------|
| Providers | Gemini, OpenCode, Droid (3 of 5) |
| Terminal | Keep both tmux and WezTerm |
| Platform | Windows/WSL compatibility |
| Daemons | `askd`, `caskd`, `laskd` (direct pane send instead) |
| Commands | `pend`, `cask`, `lask` → replaced by bidirectional `ask` (pure async) |
| Integrations | MCP delegation server + droid setup commands |

---

## Non-Goals / Guardrails

- Keep repo green after each layer: `python -m compileall -q lib bin ccb` + targeted `pytest` runs.
- No Windows native support and no WSL-specific behaviors.
- No MCP server tooling; remove instead of maintaining.
- No “read results from logs” UX (`pend`, completion hook prompting `pend`, etc.).
- No daemon-based architecture (`askd`/`caskd`/`laskd`) and no blocking sleep/poll loops in the `ask` path.

---

## Beads (Issue Tracking)

Epic: `claude_code_bridge-s7t` - Simplify CCB to Claude+Codex Only

Note: Beads are the canonical work tracker. This markdown file is a high-level design/roadmap; treat details here as advisory.

### Dependency Graph

```
Layer 0 (Ready - can start in parallel):
├── s7t.4: Restrict providers to codex+claude     [P1]
├── s7t.8: Add --reply-to flag + markers          [P1]
├── s7t.5: Remove Windows/WSL from lib/           [P2]
└── s7t.7: Delete Windows install scripts         [P2]

Layer 1:
├── s7t.1: Delete Gemini provider files           [P1] ← blocked by s7t.4
├── s7t.2: Delete OpenCode provider files         [P1] ← blocked by s7t.4
├── s7t.3: Delete Droid provider files            [P1] ← blocked by s7t.4
└── s7t.6: Remove Windows/WSL from ccb/bin        [P2] ← blocked by s7t.5

Layer 2:
├── s7t.11: Update skills (no pend)               [P1] ← blocked by s7t.8
└── s7t.9: Make ask direct-send (no daemon)       [P1] ← blocked by s7t.8

Layer 3:
└── s7t.10: Delete pend + completion hook         [P1] ← blocked by s7t.9, s7t.11

Layer 4:
└── s7t.13: Remove MCP integration                [P2] ← blocked by s7t.3

Layer 5:
├── s7t.17: Delete askd                            [P1] ← blocked by s7t.9
└── s7t.18: Remove cask/lask + caskd/laskd         [P1] ← blocked by s7t.9

Layer 6:
├── s7t.14: Update docs/README/CLAUDE.md          [P2] ← blocked by s7t.4, s7t.7, s7t.10, s7t.13
└── s7t.15: Update/delete tests + system scripts  [P2] ← blocked by s7t.1, s7t.2, s7t.3, s7t.6, s7t.10

Layer 7:
└── s7t.16: Simplify install.sh (Unix-only)       [P2] ← blocked by s7t.1, s7t.2, s7t.3, s7t.7, s7t.10, s7t.13

Layer 8 (optional):
└── s7t.12: Consolidate registries                [P3] ← blocked by s7t.6
```

---

## Phase 1: Restrict Provider Surface (Claude + Codex only)

### s7t.4: Restrict supported providers to codex+claude

Make the public surface area (CLI + routing tables) only advertise/accept `codex` and `claude`.

**Files to MODIFY (minimum):**
- `lib/providers.py` - remove Gemini/OpenCode/Droid client specs
- `lib/ccb_start_config.py` - `DEFAULT_PROVIDERS = ["codex", "claude"]`, restrict allowed set
- `bin/ask` - provider list + error messages
- `bin/askd` - only register Codex + Claude adapters
- `bin/ping` - only support codex/claude
- `bin/ccb-mounted` - only support codex/claude
- `ccb` - remove all provider-specific codepaths for gemini/opencode/droid (and droid delegation commands)
- `lib/askd/adapters/base.py` docstrings/comments (remove references to removed providers)

**Verification:**
- `ask gemini ...` prints “unknown provider”
- `ping opencode` prints “unknown provider”
- `ccb codex,claude` works

---

## Phase 2: Remove Providers (Gemini, OpenCode, Droid)

### s7t.1: Delete Gemini provider files

**Files to DELETE:**
- `bin/gask`
- `bin/gaskd`
- `bin/gpend`
- `bin/gping`
- `lib/gaskd_daemon.py`
- `lib/gaskd_protocol.py`
- `lib/gaskd_session.py`
- `lib/gemini_comm.py`
- `lib/askd/adapters/gemini.py`

### s7t.2: Delete OpenCode provider files

**Files to DELETE:**
- `bin/oask`
- `bin/oaskd`
- `bin/opend`
- `bin/oping`
- `lib/oaskd_daemon.py`
- `lib/oaskd_protocol.py`
- `lib/oaskd_session.py`
- `lib/opencode_comm.py`
- `lib/askd/adapters/opencode.py`

### s7t.3: Delete Droid provider files

**Files to DELETE:**
- `bin/dask`
- `bin/daskd`
- `bin/dpend`
- `bin/dping`
- `lib/daskd_daemon.py`
- `lib/daskd_protocol.py`
- `lib/daskd_session.py`
- `lib/droid_comm.py`
- `lib/askd/adapters/droid.py`
- `droid_skills/` (entire directory)

---

## Phase 3: Remove Windows/WSL Compatibility

### s7t.5: Remove Windows/WSL compatibility from lib/

**Files to MODIFY:**

**`lib/terminal.py`:**
- Remove `_extract_wsl_path_from_unc_like_path()`
- Simplify `_default_shell()` to always return `("bash", "-c")`

**`lib/compat.py`** - Unix-only:
```python
def setup_windows_encoding() -> None:
    pass  # No-op on Unix

def decode_stdin_bytes(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")
```

**`lib/ccb_config.py`** - Remove WSL detection, simplify to minimal backend env setup

**`lib/project_id.py`** - Remove Windows drive path normalization:
- Delete `_WIN_DRIVE_RE`
- Delete `_MNT_DRIVE_RE`
- Delete `_MSYS_DRIVE_RE`

### s7t.6: Remove Windows/WSL from ccb and bin scripts

**Files to MODIFY:**
- `ccb` - Remove Windows-specific subprocess handling, PowerShell paths
- `bin/ask` - Remove Windows process creation flags

### s7t.7: Delete Windows install scripts

**Files to DELETE:**
- `install.ps1`
- `install.cmd`

**Also delete Windows-only artifacts:**
- `bin/ccb-ping.cmd`
- `**/SKILL.md.powershell` (all PowerShell skill variants)

---

## Phase 4: Replace pend with Bidirectional Async Ask

### Design: Pure Async Bidirectional (Direct Pane Send)

**New model:**
- `ask` = “send a message” (always async, prints `req_id` immediately, sends directly to tmux/WezTerm pane)
- The callee sends the *result* back to the caller by running another `ask` with `--reply-to=<req_id>`

**No daemon, no --foreground/--background flags, no await, no pend** - just `ask`.

### Protocol Enhancement

Use existing `CCB_REQ_ID` marker; add `CCB_REPLY` and `CCB_FROM` for correlation.

Important nuance: **a reply message should not solicit another reply.**
Make `--reply-to` imply `--no-wrap` (or otherwise send a “notification/result” style payload) so the recipient doesn’t treat it as a new task.

```
# Request (sent by ask)
CCB_REQ_ID: abc123

<question>

CCB_DONE: abc123

# Result/Reply (sent back by callee via: ask <caller> --reply-to=abc123 ...)
CCB_REPLY: abc123
CCB_FROM: codex
[CCB_RESULT] No reply required.

<answer>
```

**Response markers:**
- `CCB_REPLY: <req_id>` - identifies which request this responds to
- `CCB_FROM: <provider>` - identifies sender (codex or claude), distinguishes from user input

### s7t.8: Add --reply-to flag and response markers to protocol

**Files to MODIFY:**

**`bin/ask`:**
- Add `--reply-to=<req_id>` flag
- When `--reply-to` is set, include `CCB_REPLY: <req_id>` and `CCB_FROM: <caller>` markers
- Make `--reply-to` default to a “result/notification” send (i.e., do not wrap with “end with CCB_DONE” instructions)

**`lib/ccb_protocol.py`:**
- Define `REPLY_PREFIX = "CCB_REPLY:"` and `FROM_PREFIX = "CCB_FROM:"` (single canonical place)

### s7t.9: Make ask/askd pure async (submit-only)

### s7t.9: Make ask direct-send (no daemon / no polling)

**Files to MODIFY (minimum):**
- `bin/ask`
  - Remove unified `askd` submission path and background/nohup script path
  - Resolve session + pane for `codex` and `claude` and `send_text()` directly
  - Always print `req_id`, exit immediately
- `bin/ccb-mounted`
  - Redefine “mounted” as: active session file exists + pane is alive/reachable (no daemon ping)

### s7t.10: Delete `pend` + completion hook

**Files to DELETE (minimum):**
- `bin/pend`, `bin/cpend`, `bin/lpend`
- `claude_skills/pend/`, `codex_skills/pend/`
- `bin/ccb-completion-hook`
- `lib/completion_hook.py`

### s7t.11: Update skills for async bidirectional model (no `pend`)

**Files to MODIFY (minimum):**

**`claude_skills/ask/SKILL.md`:**
- Explain that `ask` is always async, returns req_id immediately
- Explain that responses come back via `ask <caller> --reply-to=<req_id> "response"`
- Remove all references to `pend` and MCP

**`claude_skills/pair/SKILL.md` + references:**
- Replace “ask + pend” workflow with “ask + reply-via-ask” workflow (collect replies in-pane)

**`claude_skills/poll/SKILL.md` + references:**
- Same replacement (no polling `pend`; rely on replies)

**`codex_skills/ask/SKILL.md`:**
- Instruct Codex: "When you receive a question (CCB_REQ_ID), reply via `ask claude --reply-to=<req_id> 'your answer'`"

### Usage Examples

```bash
# Claude asks Codex
ask codex "review this code"
# Returns immediately with req_id, e.g. "abc123"
# Claude continues working...

# Codex processes, then replies:
ask claude --reply-to=abc123 --no-wrap "[CCB_RESULT] Here's my review: ..."
# Response appears in Claude's pane with CCB_FROM: codex marker

# Claude sees the response clearly marked as from Codex (not user)
```

### Bidirectional Flow Diagram

```
Claude                                    Codex
  │                                         │
  ├─ ask codex "question" ────────────────→ │
  │  (CCB_REQ_ID: abc123)                   │
  │  prints req_id, exits immediately       │
  │                                         ├─ sees question in pane
  │  Claude continues working...            ├─ processes question
  │                                         │
  │ ←── ask claude --reply-to=abc123 --no-wrap "4" ──┤
  │  (CCB_REPLY: abc123)                    │
  │  (CCB_FROM: codex)                      │
  │                                         │
  ├─ Claude sees response in pane           │
  │  (clearly marked as from Codex)         │
```

Both AIs can work in parallel. Neither blocks the other.
Responses are clearly distinguished from user input via CCB_FROM marker.

---

## Phase 5: Remove MCP Integration (Out of Scope)

### s7t.13: Remove MCP integration

Delete MCP delegation server and its CLI/install hooks.

**Files to DELETE / MODIFY (minimum):**
- Delete: `mcp/` (entire directory)
- Modify: `ccb` - remove droid delegation setup/test commands
- Modify: `install.sh` - remove droid MCP auto-install blocks
- Docs/plans: remove or archive `plans/droid-delegation-skills-plan.md` references

---

---

## Phase 6: Docs / Tests / Installer Cleanup

### s7t.14: Update docs/README/CLAUDE.md

**Files to MODIFY (minimum):**
- `README.md` - remove provider lists beyond codex/claude; remove Windows/WSL + MCP sections; remove `pend` usage
- `CLAUDE.md` - update architecture/entrypoints/provider list to match 2-provider + no pend + no MCP

**Verification:**
- No references to removed providers/pend/MCP in docs (except historical changelog files)

### s7t.15: Update/delete tests + system scripts

Goal: keep CI meaningful while deleting tests that only validate removed providers/platforms.

**Expected changes:**
- Delete provider-specific tests for removed providers (e.g. `test/test_gaskd_session_ensure_pane.py`, `test/test_oaskd_session.py`, droid-related tests)
- Delete/adjust system scripts that exercise removed providers and `pend` (e.g. `test/system_ccb_daemon.sh`, `test/system_pend_isolation.sh`, `test/system_comm_matrix.sh`)
- Update any remaining tests that enumerate provider lists or assume Windows/WSL paths

**Verification:**
- `pytest test/ -v --tb=short` passes on macOS/Linux

### s7t.16: Simplify install.sh (Unix-only)

**Files to MODIFY (minimum):**
- `install.sh`:
  - remove Windows/WSL prompts and WSL-specific checks
  - stop installing provider-specific scripts for removed providers
  - remove droid MCP auto-install blocks
  - stop linking `pend` and completion-hook scripts

**Verification:**
- Fresh install links only: `ccb`, `ask`, `ping`, `askd` (and any remaining codex/claude shims you keep)

---

## Phase 7: Session Registry Consolidation (Optional)

### s7t.12: Consolidate session registries

Lower priority, can be done later. Would merge:
- `lib/pane_registry.py` (363 lines)
- `lib/laskd_registry.py` (659 lines)
- `lib/claude_session_resolver.py` (358 lines)

Into single `lib/session_registry.py` (~400 lines).

---

## Files Summary

### DELETE (27+ files)

```
# Gemini
bin/gask, bin/gaskd, bin/gpend, bin/gping
lib/gaskd_daemon.py, lib/gaskd_protocol.py, lib/gaskd_session.py, lib/gemini_comm.py
lib/askd/adapters/gemini.py

# OpenCode
bin/oask, bin/oaskd, bin/opend, bin/oping
lib/oaskd_daemon.py, lib/oaskd_protocol.py, lib/oaskd_session.py, lib/opencode_comm.py
lib/askd/adapters/opencode.py

# Droid
bin/dask, bin/daskd, bin/dpend, bin/dping
lib/daskd_daemon.py, lib/daskd_protocol.py, lib/daskd_session.py, lib/droid_comm.py
lib/askd/adapters/droid.py
droid_skills/

# Pend
bin/pend, bin/cpend, bin/lpend
claude_skills/pend/
codex_skills/pend/

# Windows
install.ps1, install.cmd

# MCP
mcp/

# Completion hook
bin/ccb-completion-hook
lib/completion_hook.py
```

### MODIFY (key files)

```
lib/providers.py        - Remove 3 provider specs
lib/compat.py           - Simplify to Unix-only
lib/ccb_config.py       - Remove WSL detection
lib/project_id.py       - Remove Windows path handling
lib/ccb_start_config.py - Update DEFAULT_PROVIDERS
bin/ask                 - Pure async, 2 providers, add --reply-to flag
bin/askd                - 2 adapters only, simplified (no polling)
lib/askd/daemon.py      - Remove polling, just send and return
lib/ccb_protocol.py     - Add CCB_REPLY, CCB_FROM markers
lib/askd/adapters/codex.py  - Remove response waiting
lib/askd/adapters/claude.py - Remove response waiting
ccb                     - Remove 3 providers, Windows compat
install.sh              - Simplify provider list
claude_skills/ask/      - Update for async bidirectional model
codex_skills/ask/       - Add reply instructions
```

---

## Verification Plan

1. **Unit tests:** `pytest test/ -v --tb=short`

2. **Integration test:**
   ```bash
   ccb codex,claude                        # Start session

   # Test async ask (from Claude's pane)
   ask codex "What is 2+2?"                # Returns req_id immediately, e.g. "abc123"

   # Codex sees question, processes, replies:
   ask claude --reply-to=abc123 --no-wrap "4"        # Response appears in Claude's pane

   # Verify response has correct markers (CCB_REPLY, CCB_FROM)
   ```

3. **Verify removed commands fail gracefully:**
   ```bash
   pend codex   # Should say "command not found" (or a helpful stub)
   ask gemini   # Should say "unknown provider"
   ```

---

## Design Decisions

1. **Pure async:** `ask` always returns immediately, response comes via bidirectional `ask`
2. **Response format:** `CCB_REPLY: <req_id>` + `CCB_FROM: <provider>` markers; `--reply-to` sends a result payload by default (no wrap)
3. **No await/pend:** Responses arrive in caller's pane, clearly marked as from AI (not user)
4. **History recall:** Not needed (users can grep session logs if needed)
5. **Keep WezTerm:** Both tmux and WezTerm backends retained
6. **Unix-only:** macOS and Linux only, no Windows/WSL support
7. **No MCP:** delete MCP server and droid delegation commands

---

## Search-and-Kill Checklist (expected → zero)

- Providers: `gemini|opencode|droid` (outside this plan / archived notes)
- Commands: `pend\\b` (outside this plan / archived notes)
- Platforms: `win32|powershell|WSL|wsl\\.localhost` (outside archived notes)
- MCP: legacy droid delegation server + setup command references
