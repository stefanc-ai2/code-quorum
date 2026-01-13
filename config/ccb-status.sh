#!/usr/bin/env bash
# CCB Status Bar Script for tmux
# Shows daemon status and active AI sessions

CCB_DIR="${CCB_DIR:-$HOME/.local/share/ccb}"
TMP_DIR="${TMPDIR:-/tmp}"

# Color codes for tmux status bar (Tokyo Night palette)
C_GREEN="#[fg=#9ece6a,bold]"
C_RED="#[fg=#f7768e,bold]"
C_YELLOW="#[fg=#e0af68,bold]"
C_BLUE="#[fg=#7aa2f7,bold]"
C_PURPLE="#[fg=#bb9af7,bold]"
C_ORANGE="#[fg=#ff9e64,bold]"
C_PINK="#[fg=#ff007c,bold]"
C_TEAL="#[fg=#7dcfff,bold]"
C_RESET="#[fg=default,nobold]"
C_DIM="#[fg=#565f89]"

# Check if a daemon is running by looking for its PID file or process
check_daemon() {
    local name="$1"
    local pid_file="$TMP_DIR/ccb-${name}d.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "on"
            return
        fi
    fi

    # Fallback: check if daemon process is running
    if pgrep -f "${name}d" >/dev/null 2>&1; then
        echo "on"
        return
    fi

    echo "off"
}

# Check if a session file exists and is recent (active session)
check_session() {
    local name="$1"
    local session_file

    case "$name" in
        claude)  session_file="$PWD/.ccb_config/.claude-session" ;;
        codex)   session_file="$PWD/.ccb_config/.codex-session" ;;
        gemini)  session_file="$PWD/.ccb_config/.gemini-session" ;;
        opencode) session_file="$PWD/.ccb_config/.opencode-session" ;;
    esac

    # Backwards compatibility: older versions stored session files in project root.
    if [[ -n "$session_file" && ! -f "$session_file" ]]; then
        local legacy="${session_file/.ccb_config\\//}"
        if [[ -f "$legacy" ]]; then
            session_file="$legacy"
        fi
    fi

    if [[ -f "$session_file" ]]; then
        echo "active"
    else
        echo "inactive"
    fi
}

# Get queue depth for a daemon (if available)
get_queue_depth() {
    local name="$1"
    local queue_file="$TMP_DIR/ccb-${name}d.queue"

    if [[ -f "$queue_file" ]]; then
        wc -l < "$queue_file" 2>/dev/null | tr -d ' '
    else
        echo "0"
    fi
}

# Format status for a single AI
format_ai_status() {
    local name="$1"
    local icon="$2"
    local color="$3"
    local daemon_status

    daemon_status=$(check_daemon "$name")

    if [[ "$daemon_status" == "on" ]]; then
        echo "${color}${icon}${C_RESET}"
    else
        echo "#[fg=colour240]${icon}${C_RESET}"
    fi
}

# Main status output
main() {
    local mode="${1:-full}"

    case "$mode" in
        full)
            # Full status with all AIs
            local claude_s=$(format_ai_status "cask" "C" "$C_ORANGE")
            local codex_s=$(format_ai_status "cask" "X" "$C_GREEN")
            local gemini_s=$(format_ai_status "gask" "G" "$C_BLUE")
            local opencode_s=$(format_ai_status "oask" "O" "$C_PURPLE")

            echo " ${claude_s}${codex_s}${gemini_s}${opencode_s} "
            ;;

        daemons)
            # Just daemon status icons
            local output=""

            if [[ $(check_daemon "cask") == "on" ]]; then
                output+="${C_GREEN}X${C_RESET}"
            fi
            if [[ $(check_daemon "gask") == "on" ]]; then
                output+="${C_BLUE}G${C_RESET}"
            fi
            if [[ $(check_daemon "oask") == "on" ]]; then
                output+="${C_PURPLE}O${C_RESET}"
            fi

            if [[ -n "$output" ]]; then
                echo " $output "
            fi
            ;;

        compact)
            # Compact colorful status with individual daemon icons
            local output="${C_PINK}CCB${C_RESET} "
            local icons=""

            # Use circles/dots for status
            if [[ $(check_daemon "cask") == "on" ]]; then
                icons+="${C_ORANGE}●${C_RESET} "
            else
                icons+="${C_DIM}○${C_RESET} "
            fi
            if [[ $(check_daemon "gask") == "on" ]]; then
                icons+="${C_TEAL}●${C_RESET} "
            else
                icons+="${C_DIM}○${C_RESET} "
            fi
            if [[ $(check_daemon "oask") == "on" ]]; then
                icons+="${C_PURPLE}●${C_RESET}"
            else
                icons+="${C_DIM}○${C_RESET}"
            fi

            echo "${output}${icons}"
            ;;

        pane)
            # Show pane-specific info (for status-left)
            local pane_title="${TMUX_PANE_TITLE:-}"
            if [[ "$pane_title" == CCB-* ]]; then
                local ai_name="${pane_title#CCB-}"
                case "$ai_name" in
                    claude|codex) echo "${C_ORANGE}[$ai_name]${C_RESET}" ;;
                    gemini)       echo "${C_BLUE}[$ai_name]${C_RESET}" ;;
                    opencode)     echo "${C_PURPLE}[$ai_name]${C_RESET}" ;;
                    *)            echo "[$ai_name]" ;;
                esac
            fi
            ;;
    esac
}

main "$@"
