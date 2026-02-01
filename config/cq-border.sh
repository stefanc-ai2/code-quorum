#!/usr/bin/env bash
# CQ Border Color Script - sets active pane border based on pane title

arg="$1"
pane_id=""
title=""
agent=""

if [[ "$arg" == %* ]]; then
  pane_id="$arg"
  agent="$(tmux display-message -p -t "$pane_id" "#{@ccb_agent}" 2>/dev/null | tr -d '\r')"
  title="$(tmux display-message -p -t "$pane_id" "#{pane_title}" 2>/dev/null | tr -d '\r')"
else
  title="$arg"
fi

key="$(echo "${agent:-}" | tr -d '\n')"

set_border() {
  local style="$1"
  if [[ -n "$pane_id" ]]; then
    # Use set-option -p for pane-level option with pane_id target
    tmux set-option -p -t "$pane_id" pane-active-border-style "$style" 2>/dev/null || \
    tmux set-window-option pane-active-border-style "$style" 2>/dev/null || true
  else
    tmux set-window-option pane-active-border-style "$style" 2>/dev/null || true
  fi
}

case "$key" in
    Codex)
        set_border "fg=#ff9e64,bold" # Orange
        ;;
    Gemini)
        set_border "fg=#7dcfff,bold" # Cyan
        ;;
    Claude)
        set_border "fg=#bb9af7,bold" # Purple
        ;;
    OpenCode)
        set_border "fg=#9ece6a,bold" # Green
        ;;
    Droid)
        set_border "fg=#e0af68,bold" # Yellow
        ;;
    Cmd)
        set_border "fg=#7dcfff,bold" # Teal
        ;;
    *)
        case "$title" in
            CCB-Codex*)
                set_border "fg=#ff9e64,bold"
                ;;
            CQ-Codex*)
                set_border "fg=#ff9e64,bold"
                ;;
            CCB-Gemini*)
                set_border "fg=#7dcfff,bold"
                ;;
            CQ-Gemini*)
                set_border "fg=#7dcfff,bold"
                ;;
            Claude*)
                set_border "fg=#bb9af7,bold"
                ;;
            CCB-OpenCode*)
                set_border "fg=#9ece6a,bold"
                ;;
            CQ-OpenCode*)
                set_border "fg=#9ece6a,bold"
                ;;
            CCB-Droid*)
                set_border "fg=#e0af68,bold"
                ;;
            CQ-Droid*)
                set_border "fg=#e0af68,bold"
                ;;
            CCB-Cmd*)
                set_border "fg=#7dcfff,bold"
                ;;
            CQ-Cmd*)
                set_border "fg=#7dcfff,bold"
                ;;
            *)
                set_border "fg=#7aa2f7,bold" # Blue (default)
                ;;
        esac
        ;;
esac
