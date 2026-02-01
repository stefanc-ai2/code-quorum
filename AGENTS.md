# Repository Guidelines

## Project Structure & Module Organization

- `cq`: primary CLI entrypoint (launcher/orchestrator).
- `ccb`: compatibility wrapper (for legacy workflows).
- `lib/`: Python implementation (terminal backends, protocol markers, config/session utilities).
- `bin/`: small CLI tools and wrappers (e.g. `ask`, `ping`, `cq-mounted`, `ccb-mounted`).
- `test/`: `pytest` suite (+ a few `test/system_*.sh` scripts).
- `claude_skills/`, `codex_skills/`: provider skill bundles installed by `install.sh`.

## Build, Test, and Development Commands

- `python -m compileall -q lib bin ccb cq`: fast syntax/type-syntax sanity check (matches CI).
- `python -m pip install -U pip pytest`: install test runner.
- `python -m pytest test/ -v --tb=short`: run the full test suite locally.
- `./install.sh install` / `./install.sh uninstall`: install or remove local commands (see env vars in `install.sh` header).
- `./cq -h`: run the launcher from the repo checkout (no install required). (`./ccb -h` works too.)

## Coding Style & Naming Conventions

- Python: 4-space indentation, type hints where practical, keep modules small and focused.
- New Python files should start with `from __future__ import annotations` to match existing code.
- Naming: `snake_case` for functions/files, `CapWords` for classes, constants in `UPPER_SNAKE_CASE`.
- Shell scripts: prefer `bash` with `set -euo pipefail`; keep behavior cross-platform (macOS/Linux).

## Testing Guidelines

- Framework: `pytest` (tests live in `test/test_*.py`).
- Some tests require `tmux`.
- If you touch tmux behavior, validate on a system with tmux installed:
  `TERM=xterm-256color python -m pytest test/ -v --tb=short`.

## Interaction / Protocol Rules

- **Do not scrape panes** to collect responses (forbidden): do not use `wezterm cli get-text`, `tmux capture-pane`, or similar.
- **Replies must arrive via reply-via-ask** (`ask --reply-to ... --caller <provider>`); treat `ask` as async send-only.

## Commit & Pull Request Guidelines

- Commit messages follow a Conventional-Commits style seen in history: `feat: …`, `fix: …`, `refactor: …`, `chore: …`, `release: …` (optional scope like `fix(askd_client): …`).
- PRs should include: what changed, why, how to test, and any OS-specific notes (macOS/Linux).
- Update `README.md` when changing user-facing commands, flags, or defaults.

## Security & Configuration Tips

- Don’t commit local session/config artifacts under `.ccb_config/` or provider runtime/session files.
- Prefer configuration via `ccb.config` (`.ccb_config/ccb.config` or `~/.ccb/ccb.config`) and environment variables; avoid hardcoding paths or secrets.

## Beads (Issue Tracking)

- This repo uses Beads (`bd`) for issue tracking; project state lives under `.beads/`.
- Git tracking: `.beads/issues.jsonl` is committed. SQLite DBs and daemon runtime files under `.beads/` are ignored via `.beads/.gitignore`.
- Merge behavior: `.gitattributes` configures a custom merge driver for `.beads/issues.jsonl` (requires Beads tooling available for best results).
- Prefer using `bd` commands instead of editing `.beads/*.jsonl` by hand.
