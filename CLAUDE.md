# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Bridge (ccb) is a multi-model AI collaboration tool that manages Claude, Codex, Gemini, OpenCode, and Droid through split-pane terminal sessions. It supports tmux and WezTerm terminals across Linux, macOS, and Windows (including WSL).

**Pure Python** - No external dependencies; uses only stdlib.

## Build & Test Commands

```bash
# Syntax check
python -m compileall -q lib bin ccb

# Run all tests
pytest test/ -v --tb=short

# Run single test file
pytest test/test_integration.py -v

# Run single test
pytest test/test_integration.py::test_server_client_exchange -v

# Windows (exclude tmux tests)
pytest test/ -v --tb=short -k "not tmux"

# WSL
TERM=xterm-256color pytest test/ -v --tb=short
```

## Architecture

### Entry Points
- `ccb` - Main launcher that starts/manages terminal sessions and daemons
- `bin/ask` - Unified async request handler (routes to any provider)
- `bin/ping` - Connectivity test for providers
- `bin/pend` - View latest provider responses

### Core Modules (lib/)

**Terminal Layer:**
- `terminal.py` - Terminal backend abstraction (TmuxBackend, WeztermBackend)
- `compat.py` - Windows/WSL compatibility layer

**Unified Daemon Architecture:**
- `askd_server.py` - Socket server base class
- `askd_client.py` - Socket client wrapper
- `askd_rpc.py` - RPC protocol (JSON over sockets)
- `askd_runtime.py` - Daemon lifecycle and state management

**Provider Daemons (each has daemon/protocol/session/comm modules):**
- `caskd_*` - Codex
- `gaskd_*` - Gemini
- `oaskd_*` - OpenCode
- `daskd_*` - Droid
- `laskd_*` - Claude (unified)

**Session Management:**
- `pane_registry.py` - Maps project directories to pane IDs
- `session_utils.py` - Safe session file I/O
- `project_id.py` - Project-based session isolation

### Skills System
Located in `claude_skills/`, `codex_skills/`, `droid_skills/`. Each skill has:
- `SKILL.md` - Unix/Linux/macOS/WSL instructions
- `SKILL.md.powershell` - Windows PowerShell instructions

### Configuration
- `.ccb_config/ccb.config` (project) or `~/.ccb/ccb.config` (global)
- Simple format: `codex,gemini,opencode,claude`
- JSON format available for advanced options

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `CCB_BACKEND_ENV` | Force tmux or wezterm backend |
| `CCB_RUN_DIR` | Runtime state directory |
| `CCB_PARENT_PID` | Parent process tracking (daemon lifecycle) |
| `CCB_UNIFIED_ASKD` | Use unified daemon (default: true) |
| `CCB_CALLER` | Request caller identifier |
| `CCB_COMPLETION_HOOK_ENABLED` | Trigger completion hook (default: true) |

## Testing Notes

- Tests add `lib/` to `sys.path` via `conftest.py`
- Integration tests verify daemon server/client RPC communication
- Platform tests cover Ubuntu, macOS, Windows, and WSL
- tmux tests require tmux to be available; skipped on Windows native

## Beads (Issue Tracking)

This repo tracks issues using Beads (`bd`) in `.beads/`.

- Source of truth: `.beads/issues.jsonl` is committed.
- Local-only artifacts: SQLite databases and daemon runtime files inside `.beads/` are ignored via `.beads/.gitignore`.
- Merge behavior: `.gitattributes` configures `merge=beads` for `.beads/issues.jsonl` (install Beads to get the intended merge behavior).

Prefer using `bd` commands over manual edits to `.beads/*.jsonl`.
