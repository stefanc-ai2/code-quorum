#!/usr/bin/env bash
set -euo pipefail

# CQ tmux UI restore helper (session-scoped).

if ! command -v tmux >/dev/null 2>&1; then
  exit 0
fi

session="${1:-}"
if [[ -z "$session" ]]; then
  session="$(tmux display-message -p '#{session_name}' 2>/dev/null || true)"
fi
if [[ -z "$session" ]]; then
  exit 0
fi

restore_sopt() {
  local opt="$1"
  local key="$2"
  local val=""
  val="$(tmux show-options -t "$session" -v "$key" 2>/dev/null || true)"
  tmux set-option -t "$session" "$opt" "$val" >/dev/null 2>&1 || true
  tmux set-option -t "$session" -u "$key" >/dev/null 2>&1 || true
}

restore_wopt() {
  local opt="$1"
  local key="$2"
  local val=""
  val="$(tmux show-options -t "$session" -v "$key" 2>/dev/null || true)"
  tmux set-window-option -t "$session" "$opt" "$val" >/dev/null 2>&1 || true
  tmux set-option -t "$session" -u "$key" >/dev/null 2>&1 || true
}

restore_hook() {
  local hook="$1"
  local key="$2"
  local cmd=""
  cmd="$(tmux show-options -t "$session" -v "$key" 2>/dev/null || true)"
  if [[ -z "$cmd" ]]; then
    tmux set-hook -t "$session" -u "$hook" >/dev/null 2>&1 || true
  else
    tmux set-hook -t "$session" "$hook" "$cmd" >/dev/null 2>&1 || true
  fi
  tmux set-option -t "$session" -u "$key" >/dev/null 2>&1 || true
}

restore_hook after-select-pane @cq_prev_hook_after_select_pane

restore_wopt pane-border-status @cq_prev_pane_border_status
restore_wopt pane-border-format @cq_prev_pane_border_format
restore_wopt pane-border-style @cq_prev_pane_border_style
restore_wopt pane-active-border-style @cq_prev_pane_active_border_style

restore_sopt status @cq_prev_status
restore_sopt status-position @cq_prev_status_position
restore_sopt status-justify @cq_prev_status_justify
restore_sopt status-interval @cq_prev_status_interval
restore_sopt status-style @cq_prev_status_style
restore_sopt 'status-format[0]' @cq_prev_status_format_0
restore_sopt 'status-format[1]' @cq_prev_status_format_1
restore_sopt status-left-length @cq_prev_status_left_length
restore_sopt status-right-length @cq_prev_status_right_length
restore_sopt status-left @cq_prev_status_left
restore_sopt status-right @cq_prev_status_right
restore_sopt window-status-format @cq_prev_window_status_format
restore_sopt window-status-current-format @cq_prev_window_status_current_format
restore_sopt window-status-separator @cq_prev_window_status_separator

tmux set-option -t "$session" -u @cq_active >/dev/null 2>&1 || true
tmux set-option -t "$session" -u @cq_version >/dev/null 2>&1 || true
