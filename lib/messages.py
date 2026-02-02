from __future__ import annotations

_MESSAGES: dict[str, str] = {
    # Terminal detection
    "no_terminal_backend": "No terminal backend detected (WezTerm or tmux)",
    "solutions": "Solutions:",
    "install_wezterm": "Install WezTerm (recommended): https://wezfurlong.org/wezterm/",
    "or_install_tmux": "Or install tmux",
    "tmux_installed_not_inside": (
        "tmux is installed, but you're not inside a tmux session "
        "(run `tmux` first, then run `cq` inside tmux)"
    ),
    "or_set_cq_terminal": "Or set CQ_TERMINAL=wezterm and configure CODEX_WEZTERM_BIN",
    "tmux_not_installed": "tmux not installed and WezTerm unavailable",
    "install_wezterm_or_tmux": "Solution: Install WezTerm (recommended) or tmux",
    # Startup messages
    "starting_backend": "Starting {provider} backend ({terminal})...",
    "started_backend": "{provider} started ({terminal}: {pane_id})",
    "unknown_provider": "Unknown provider: {provider}",
    "resuming_session": "Resuming {provider} session: {session_id}...",
    "no_history_fresh": "No {provider} history found, starting fresh",
    # Claude
    "starting_claude": "Starting Claude...",
    "resuming_claude": "Resuming Claude session: {session_id}...",
    "no_claude_session": "No local Claude session found, starting fresh",
    "user_interrupted": "User interrupted",
    "cleaning_up": "Cleaning up session resources...",
    "cleanup_complete": "Cleanup complete",
    # Commands
    "sending_to": "Sending question to {provider}...",
    "waiting_for_reply": "Waiting for {provider} reply (no timeout, Ctrl-C to interrupt)...",
    "reply_from": "{provider} reply:",
    "timeout_no_reply": "Timeout: no reply from {provider}",
    # Connectivity
    "no_reply_available": "No {provider} reply available",
}


def t(key: str, **kwargs: object) -> str:
    msg = _MESSAGES.get(key, key)
    if not kwargs:
        return msg
    try:
        return msg.format(**kwargs)
    except (KeyError, ValueError):
        return msg
