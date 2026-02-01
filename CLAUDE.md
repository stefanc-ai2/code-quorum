# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Code Quorum (`cq`) is a split-pane collaboration tool for **Claude** and **Codex**.

Compatibility: legacy `ccb` / `ccb-mounted` are kept as aliases during transition.

Current design constraints:
- Providers: `claude`, `codex` only
- Platforms: macOS/Linux only
- No background daemons
- No polling commands; replies are delivered via reply-via-ask (`ask --reply-to ...`)
- Do not scrape panes to collect replies (forbidden): no `wezterm cli get-text`, no `tmux capture-pane`, etc.

**Pure Python**: no external runtime dependencies beyond the provider CLIs and a terminal backend.

## Build & Test Commands

```bash
# Syntax check
python -m compileall -q lib bin ccb cq test

# Run all tests
python -m pytest test/ -v --tb=short

# If validating tmux behavior locally:
TERM=xterm-256color python -m pytest test/ -v --tb=short
```

## Architecture

### Entry points

- `cq`: launcher/orchestrator (starts panes, writes `.ccb_config/.{provider}-session`)
- `bin/ask`: send-only message delivery into a provider pane (async; prints req_id)
- `bin/ping`: provider connectivity check
- `bin/cq-mounted`: report mounted providers for the current directory
- `ccb` / `bin/ccb-mounted`: legacy compatibility wrappers

### Key modules

- `lib/terminal.py`: terminal backend abstraction (`TmuxBackend`, `WeztermBackend`)
- `lib/*_session.py`: loads per-project session bindings and ensures pane liveness
- `lib/ccb_protocol.py`: protocol markers (`CCB_REQ_ID`, `CCB_REPLY`, `CCB_FROM`) + wrapping helpers
- `lib/project_id.py`, `lib/session_utils.py`, `lib/session_registry.py`: project isolation and session lookup

### Session isolation

Session resolution is scoped to the current project via `.ccb_config/`.
This enables running multiple repositories (repo A and repo B) without cross-talk.

## Beads (Issue Tracking)

This repo tracks issues using Beads (`bd`) in `.beads/`.
Prefer `bd` commands over manual edits to `.beads/issues.jsonl`.
