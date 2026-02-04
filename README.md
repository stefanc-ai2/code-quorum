<div align="center">

# Code Quorum (`cq`)

Split-pane collaboration between **Claude** and **Codex** using **tmux** or **WezTerm**.

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg)]()

**This repo is intentionally simplified:** no background daemons, no polling commands, no delegation tooling.

</div>

---

## What it does

- `cq` starts **Claude** and/or **Codex** in separate panes and writes per-project session files under `.cq_config/`.
- `ask` sends a message directly to the target pane (send-only, always async).
- Replies come back **in the pane** via `ask --reply-to ...` (bidirectional “reply-via-ask”).

No log tailing/monitoring is required or used.

---

## Requirements

- Python **3.10+**
- Either:
  - tmux (run `tmux` first, then run `cq` inside tmux), or
  - WezTerm (recommended)
- The `claude` CLI and the `codex` CLI installed and on `PATH`

---

## Install

From a repo checkout:

```bash
./install.sh install
```

This installs:
- executables into `~/.local/bin` (or `$CQ_BIN_DIR`)
- project files into `~/.local/share/code-quorum` (or `$CQ_INSTALL_PREFIX`)
- skills into `~/.claude/skills` and `${CODEX_HOME:-~/.codex}/skills`

Uninstall:

```bash
./install.sh uninstall
```

---

## Quickstart

From your project directory (must contain `.cq_config/`):

```bash
mkdir -p .cq_config
cq codex,claude
```

Send a message to a provider:

```bash
ask codex "Review this diff and suggest improvements."
```

`ask` prints a request id (req_id) and exits immediately.

---

## Bidirectional ask (reply-via-ask)

If you want the recipient to reply back to the caller (useful for `/pair`, `/poll`, `/all-plan` flows), replies are sent as another `ask`:

```bash
# In the recipient pane (send back to the driver):
ask codex --reply-to <REQ_ID> --caller claude "Here are my notes..."
# (or)
ask claude --reply-to <REQ_ID> --caller codex "Here are my notes..."
```

Tip: when you *expect* reply-via-ask, set a stable id with `--req-id`. `ask` includes a `CQ_REQ_ID: <id>` line at the top automatically so the recipient can copy it.

```bash
REQ_ID="$(python -c 'import secrets; print(secrets.token_hex(16))')"
ask claude --req-id "$REQ_ID" <<EOF
Review this and reply via:
  ask codex --reply-to "$REQ_ID" --caller claude "<your notes>"
EOF
```

The reply is wrapped with protocol markers so the caller can identify it:

```
CQ_REPLY: <REQ_ID>
CQ_FROM: claude
[CQ_RESULT] No reply required.

...message...
```

---

## Skills (workflows)

These skills are installed for the providers and use the **reply-via-ask** pattern described above.

| Skill | Primary purpose | Code changes? | Interaction | Output | Use when |
|:------|------------------|--------------|------------|--------|----------|
| `all-plan` | Collaborative planning | No | Multi-turn: ask providers → synthesize | A concrete plan + decisions | You want agreement before coding |
| `pair` | Implement + review loop | Yes | Multi-turn: implement → review → merge (repeat) | Code changes + reviewer feedback | You want higher-quality changes fast |
| `poll` | “Ask the room” Q&A | No | Multi-turn: broadcast → collect replies → synthesize | A consensus answer (or split) | You want quick independent opinions |

---

## Session isolation (repo A vs repo B)

By default, `ask` resolves sessions **only** for the current project via `.cq_config/` and will not talk to sessions from a different repository.

## Multiple sessions (same repo)

Use `--session` to run multiple independent `cq` launchers in the same directory:

```bash
cq --session feature-a codex,claude
cq --session feature-b codex,claude
```

This namespaces the launcher lock per (cwd,session) and exports `CQ_SESSION` in managed panes.
Session-scoped provider session files are implemented in follow-up changes.

To check what is currently mounted:

```bash
cq-mounted --json
```

---

## Development

```bash
python -m compileall -q lib bin cq test
python -m pytest test/ -v --tb=short
```

---

## WezTerm notes

`ask` sends text to a pane and then injects **Enter** so the target TUI processes it. If you see text get pasted but not submitted, tune these env vars:

- `CQ_WEZTERM_ENTER_METHOD=auto|key|text` (default: `auto`)
  - `auto`: try `wezterm cli send-key Enter`, fall back to a raw CR byte
  - `key`: force `send-key` only (no fallback)
  - `text`: legacy mode (CR byte only)
- `CQ_WEZTERM_ENTER_DELAY` (seconds): delay before injecting Enter
- `CQ_WEZTERM_PASTE_DELAY` (seconds): delay between paste-mode send and Enter injection (multiline)
