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

## Session isolation (repo A vs repo B)

By default, `ask` resolves sessions **only** for the current project via `.cq_config/` and will not talk to sessions from a different repository.

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
