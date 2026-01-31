# Repository Guidelines

## Project Structure & Module Organization

- `ccb`: primary CLI entrypoint (launcher/orchestrator).
- `lib/`: Python implementation (terminal backends, daemons, provider comms, config/session utilities).
- `bin/`: small CLI tools and wrappers (e.g. `ask`, `ping`, `ccb-mounted`).
- `test/`: `pytest` suite (+ a few `test/system_*.sh` scripts).
- `*_skills/`: provider-specific skill bundles installed by `install.sh`.

## Build, Test, and Development Commands

- `python -m compileall -q lib bin ccb`: fast syntax/type-syntax sanity check (matches CI).
- `python -m pip install -U pip pytest`: install test runner.
- `python -m pytest test/ -v --tb=short`: run the full test suite locally.
- `./install.sh install` / `./install.sh uninstall`: install or remove local commands (see env vars in `install.sh` header).
- `./ccb -h`: run the launcher from the repo checkout (no install required).

## Coding Style & Naming Conventions

- Python: 4-space indentation, type hints where practical, keep modules small and focused.
- New Python files should start with `from __future__ import annotations` to match existing code.
- Naming: `snake_case` for functions/files, `CapWords` for classes, constants in `UPPER_SNAKE_CASE`.
- Shell scripts: prefer `bash` with `set -euo pipefail`; keep behavior cross-platform (macOS/Linux/WSL/Windows).

## Testing Guidelines

- Framework: `pytest` (tests live in `test/test_*.py`).
- Some tests require `tmux`; on Windows CI they’re skipped via `-k "not tmux"`.
- If you touch tmux behavior, validate on a system with tmux installed:
  `TERM=xterm-256color python -m pytest test/ -v --tb=short`.

## Commit & Pull Request Guidelines

- Commit messages follow a Conventional-Commits style seen in history: `feat: …`, `fix: …`, `refactor: …`, `chore: …`, `release: …` (optional scope like `fix(askd_client): …`).
- PRs should include: what changed, why, how to test, and any OS-specific notes (Windows/WSL/macOS/Linux).
- Update `README.md`/`CHANGELOG.md` when changing user-facing commands, flags, or defaults.

## Security & Configuration Tips

- Don’t commit local session/config artifacts under `.ccb_config/` or provider runtime/session files.
- Prefer configuration via `ccb.config` (`.ccb_config/ccb.config` or `~/.ccb/ccb.config`) and environment variables; avoid hardcoding paths or secrets.

## Beads (Issue Tracking)

- This repo uses Beads (`bd`) for issue tracking; project state lives under `.beads/`.
- Git tracking: `.beads/issues.jsonl` is committed. SQLite DBs and daemon runtime files under `.beads/` are ignored via `.beads/.gitignore`.
- Merge behavior: `.gitattributes` configures a custom merge driver for `.beads/issues.jsonl` (requires Beads tooling available for best results).
- Prefer using `bd` commands instead of editing `.beads/*.jsonl` by hand.
