#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${CODEX_INSTALL_PREFIX:-$HOME/.local/share/codex-dual}"
BIN_DIR="${CODEX_BIN_DIR:-$HOME/.local/bin}"
readonly REPO_ROOT INSTALL_PREFIX BIN_DIR

# Check for root/sudo - refuse to run as root
if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "ERROR: Do not run as root/sudo. Please run as a normal user." >&2
  exit 1
fi

SCRIPTS_TO_LINK=(
  bin/ask
  bin/ping
  bin/autonew
  ccb
)

CLAUDE_MARKDOWN=(
  # Old CCB commands removed - replaced by unified ask/ping skills
)

LEGACY_SCRIPTS=(
  cast
  cast-w
  codex-ask
  codex-pending
  codex-ping
  claude-codex-dual
  claude_codex
  claude_ai
  claude_bridge
  # Removed provider-specific CLIs (kept for uninstall/upgrade cleanup)
  cping
  lping
  cask
  lask
  gask
  oask
  dask
  pend
  cpend
  gpend
  opend
  dpend
  lpend
  ccb-completion-hook
  gping
  oping
  dping
  askd
  caskd
  gaskd
  oaskd
  laskd
  daskd
)

usage() {
  cat <<'USAGE'
Usage:
  ./install.sh install    # Install or update Codex dual-window tools
  ./install.sh uninstall  # Uninstall installed content

Optional environment variables:
  CODEX_INSTALL_PREFIX     Install directory (default: ~/.local/share/codex-dual)
  CODEX_BIN_DIR            Executable directory (default: ~/.local/bin)
  CODEX_CLAUDE_COMMAND_DIR Custom Claude commands directory (default: auto-detect)
USAGE
}

detect_claude_dir() {
  if [[ -n "${CODEX_CLAUDE_COMMAND_DIR:-}" ]]; then
    echo "$CODEX_CLAUDE_COMMAND_DIR"
    return
  fi

  local candidates=(
    "$HOME/.claude/commands"
    "$HOME/.config/claude/commands"
    "$HOME/.local/share/claude/commands"
  )

  for dir in "${candidates[@]}"; do
    if [[ -d "$dir" ]]; then
      echo "$dir"
      return
    fi
  done

  local fallback="$HOME/.claude/commands"
  mkdir -p "$fallback"
  echo "$fallback"
}

require_command() {
  local cmd="$1"
  local pkg="${2:-$1}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing dependency: $cmd"
    echo "   Please install $pkg first, then re-run install.sh"
    exit 1
  fi
}

PYTHON_BIN="${CCB_PYTHON_BIN:-}"

_python_check_310() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || return 1
  "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

pick_python_bin() {
  if [[ -n "${PYTHON_BIN}" ]] && _python_check_310 "${PYTHON_BIN}"; then
    return 0
  fi
  for cmd in python3 python; do
    if _python_check_310 "$cmd"; then
      PYTHON_BIN="$cmd"
      return 0
    fi
  done
  return 1
}

pick_any_python_bin() {
  if [[ -n "${PYTHON_BIN}" ]] && command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    return 0
  fi
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      PYTHON_BIN="$cmd"
      return 0
    fi
  done
  return 1
}

require_python_version() {
  # ccb requires Python 3.10+ (PEP 604 type unions: `str | None`, etc.)
  if ! pick_python_bin; then
    echo "ERROR: Missing dependency: python (3.10+ required)"
    echo "   Please install Python 3.10+ and ensure it is on PATH, then re-run install.sh"
    exit 1
  fi
  local version
  version="$("$PYTHON_BIN" -c 'import sys; print("{}.{}.{}".format(sys.version_info[0], sys.version_info[1], sys.version_info[2]))' 2>/dev/null || echo unknown)"
  if ! _python_check_310 "$PYTHON_BIN"; then
    echo "ERROR: Python version too old: $version"
    echo "   Requires Python 3.10+, please upgrade and retry"
    exit 1
  fi
  echo "OK: Python $version ($PYTHON_BIN)"
}

# Return linux / macos / unknown based on uname
detect_platform() {
  local name
  name="$(uname -s 2>/dev/null || echo unknown)"
  case "$name" in
    Linux) echo "linux" ;;
    Darwin) echo "macos" ;;
    *) echo "unknown" ;;
  esac
}


 
print_tmux_install_hint() {
  local platform
  platform="$(detect_platform)"
  case "$platform" in
    macos)
      if command -v brew >/dev/null 2>&1; then
        echo "   macOS: Run 'brew install tmux'"
      else
        echo "   macOS: Homebrew not detected, install from https://brew.sh then run 'brew install tmux'"
      fi
      ;;
    linux)
      if command -v apt-get >/dev/null 2>&1; then
        echo "   Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y tmux"
      elif command -v dnf >/dev/null 2>&1; then
        echo "   Fedora/CentOS/RHEL: sudo dnf install -y tmux"
      elif command -v yum >/dev/null 2>&1; then
        echo "   CentOS/RHEL: sudo yum install -y tmux"
      elif command -v pacman >/dev/null 2>&1; then
        echo "   Arch/Manjaro: sudo pacman -S tmux"
      elif command -v apk >/dev/null 2>&1; then
        echo "   Alpine: sudo apk add tmux"
      elif command -v zypper >/dev/null 2>&1; then
        echo "   openSUSE: sudo zypper install -y tmux"
      else
        echo "   Linux: Please use your distro's package manager to install tmux"
      fi
      ;;
    *)
      echo "   See https://github.com/tmux/tmux/wiki/Installing for tmux installation"
      ;;
  esac
}

require_terminal_backend() {
  local wezterm_override="${CODEX_WEZTERM_BIN:-${WEZTERM_BIN:-}}"

  # ============================================
  # Prioritize detecting current environment
  # ============================================

  # 1. If running in WezTerm environment
  if [[ -n "${WEZTERM_PANE:-}" ]]; then
    if [[ -n "${wezterm_override}" ]] && { command -v "${wezterm_override}" >/dev/null 2>&1 || [[ -f "${wezterm_override}" ]]; }; then
      echo "OK: Detected WezTerm environment (${wezterm_override})"
      return
    fi
    if command -v wezterm >/dev/null 2>&1; then
      echo "OK: Detected WezTerm environment"
      return
    fi
  fi

  # 2. If running in tmux environment
  if [[ -n "${TMUX:-}" ]]; then
    echo "OK: Detected tmux environment"
    return
  fi

  # ============================================
  # Not in specific environment, detect by availability
  # ============================================

  # 3. Check WezTerm environment variable override
  if [[ -n "${wezterm_override}" ]]; then
    if command -v "${wezterm_override}" >/dev/null 2>&1 || [[ -f "${wezterm_override}" ]]; then
      echo "OK: Detected WezTerm (${wezterm_override})"
      return
    fi
  fi

  # 4. Check WezTerm command
  if command -v wezterm >/dev/null 2>&1; then
    echo "OK: Detected WezTerm"
    return
  fi

  # 5. Check tmux
  if command -v tmux >/dev/null 2>&1; then
    echo "OK: Detected tmux (recommend also installing WezTerm for better experience)"
    return
  fi

  # 6. No terminal multiplexer found
  echo "ERROR: Missing dependency: WezTerm or tmux (at least one required)"
  echo "   WezTerm website: https://wezfurlong.org/wezterm/"

  if [[ "$(uname)" == "Darwin" ]]; then
    echo
    echo "NOTE: macOS user recommended options:"
    echo "   - Install tmux: brew install tmux"
  fi

  print_tmux_install_hint
  exit 1
}

has_wezterm() {
  local wezterm_override="${CODEX_WEZTERM_BIN:-${WEZTERM_BIN:-}}"
  if [[ -n "${wezterm_override}" ]]; then
    command -v "${wezterm_override}" >/dev/null 2>&1 || [[ -f "${wezterm_override}" ]] && return 0
  fi
  command -v wezterm >/dev/null 2>&1 && return 0
  return 1
}

detect_wezterm_path() {
  local wezterm_override="${CODEX_WEZTERM_BIN:-${WEZTERM_BIN:-}}"
  if [[ -n "${wezterm_override}" ]] && [[ -f "${wezterm_override}" ]]; then
    echo "${wezterm_override}"
    return
  fi
  local found
  found="$(command -v wezterm 2>/dev/null)" && [[ -n "$found" ]] && echo "$found" && return
}

save_wezterm_config() {
  local wezterm_path
  wezterm_path="$(detect_wezterm_path)"
  if [[ -n "$wezterm_path" ]]; then
    local cfg_root="${XDG_CONFIG_HOME:-$HOME/.config}"
    mkdir -p "$cfg_root/ccb"
    echo "CODEX_WEZTERM_BIN=${wezterm_path}" > "$cfg_root/ccb/env"
    echo "OK: WezTerm path cached: $wezterm_path"
  fi
}

copy_project() {
  local staging
  staging="$(mktemp -d)"
  trap 'rm -rf "$staging"' EXIT

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git/' \
      --exclude '__pycache__/' \
      --exclude '.pytest_cache/' \
      --exclude '.mypy_cache/' \
      --exclude '.venv/' \
      "$REPO_ROOT"/ "$staging"/
  else
    tar -C "$REPO_ROOT" \
      --exclude '.git' \
      --exclude '__pycache__' \
      --exclude '.pytest_cache' \
      --exclude '.mypy_cache' \
      --exclude '.venv' \
      -cf - . | tar -C "$staging" -xf -
  fi

  rm -rf "$INSTALL_PREFIX"
  mkdir -p "$(dirname "$INSTALL_PREFIX")"
  mv "$staging" "$INSTALL_PREFIX"
  trap - EXIT

  # Update GIT_COMMIT and GIT_DATE in ccb file
  local git_commit="" git_date=""

  # Method 1: From git repo
  if command -v git >/dev/null 2>&1 && [[ -d "$REPO_ROOT/.git" ]]; then
    git_commit=$(git -C "$REPO_ROOT" log -1 --format='%h' 2>/dev/null || echo "")
    git_date=$(git -C "$REPO_ROOT" log -1 --format='%cs' 2>/dev/null || echo "")
  fi

  # Method 2: From environment variables (set by ccb update)
  if [[ -z "$git_commit" && -n "${CCB_GIT_COMMIT:-}" ]]; then
    git_commit="$CCB_GIT_COMMIT"
    git_date="${CCB_GIT_DATE:-}"
  fi

  # Method 3: From GitHub API (fallback)
  if [[ -z "$git_commit" ]] && command -v curl >/dev/null 2>&1; then
    local api_response
    api_response=$(curl -fsSL "https://api.github.com/repos/bfly123/claude_code_bridge/commits/main" 2>/dev/null || echo "")
    if [[ -n "$api_response" ]]; then
      git_commit=$(echo "$api_response" | grep -o '"sha": "[^"]*"' | head -1 | cut -d'"' -f4 | cut -c1-7)
      git_date=$(echo "$api_response" | grep -o '"date": "[^"]*"' | head -1 | cut -d'"' -f4 | cut -c1-10)
    fi
  fi

  if [[ -n "$git_commit" && -f "$INSTALL_PREFIX/ccb" ]]; then
    sed -i.bak "s/^GIT_COMMIT = .*/GIT_COMMIT = \"$git_commit\"/" "$INSTALL_PREFIX/ccb"
    sed -i.bak "s/^GIT_DATE = .*/GIT_DATE = \"$git_date\"/" "$INSTALL_PREFIX/ccb"
    rm -f "$INSTALL_PREFIX/ccb.bak"
  fi
}

install_bin_links() {
  mkdir -p "$BIN_DIR"

  for path in "${SCRIPTS_TO_LINK[@]}"; do
    local name
    name="$(basename "$path")"
    if [[ ! -f "$INSTALL_PREFIX/$path" ]]; then
      echo "WARN: Script not found $INSTALL_PREFIX/$path, skipping link creation"
      continue
    fi
    chmod +x "$INSTALL_PREFIX/$path"
    if ln -sf "$INSTALL_PREFIX/$path" "$BIN_DIR/$name" 2>/dev/null; then
      :
    else
      # Restricted environments may not allow symlinks. Fall back to copying.
      cp -f "$INSTALL_PREFIX/$path" "$BIN_DIR/$name"
      chmod +x "$BIN_DIR/$name" 2>/dev/null || true
    fi
  done

  for legacy in "${LEGACY_SCRIPTS[@]}"; do
    rm -f "$BIN_DIR/$legacy"
  done

  echo "Created executable links in $BIN_DIR"
}

ensure_path_configured() {
  # Check if BIN_DIR is already in PATH
  if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
    return
  fi

  local shell_rc=""
  local current_shell
  current_shell="$(basename "${SHELL:-/bin/bash}")"

  case "$current_shell" in
    zsh)  shell_rc="$HOME/.zshrc" ;;
    bash)
      if [[ -f "$HOME/.bash_profile" ]]; then
        shell_rc="$HOME/.bash_profile"
      else
        shell_rc="$HOME/.bashrc"
      fi
      ;;
    *)    shell_rc="$HOME/.profile" ;;
  esac

  local path_line="export PATH=\"${BIN_DIR}:\$PATH\""

  # Check if already configured in shell rc
  if [[ -f "$shell_rc" ]] && grep -qF "$BIN_DIR" "$shell_rc" 2>/dev/null; then
    echo "PATH already configured in $shell_rc (restart terminal to apply)"
    return
  fi

  # Add to shell rc
  echo "" >> "$shell_rc"
  echo "# Added by ccb installer" >> "$shell_rc"
  echo "$path_line" >> "$shell_rc"
  echo "OK: Added $BIN_DIR to PATH in $shell_rc"
  echo "   Run: source $shell_rc  (or restart terminal)"
}

install_claude_commands() {
  local claude_dir
  claude_dir="$(detect_claude_dir)"
  mkdir -p "$claude_dir"

  # Clean up obsolete CCB commands (replaced by unified ask/ping)
  local obsolete_cmds="cask.md gask.md oask.md dask.md lask.md cpend.md gpend.md opend.md dpend.md lpend.md cping.md gping.md oping.md dping.md lping.md"
  for obs_cmd in $obsolete_cmds; do
    if [[ -f "$claude_dir/$obs_cmd" ]]; then
      rm -f "$claude_dir/$obs_cmd"
      echo "  Removed obsolete command: $obs_cmd"
    fi
  done

  for doc in "${CLAUDE_MARKDOWN[@]+"${CLAUDE_MARKDOWN[@]}"}"; do
    cp -f "$REPO_ROOT/commands/$doc" "$claude_dir/$doc"
    chmod 0644 "$claude_dir/$doc" 2>/dev/null || true
  done

  echo "Updated Claude commands directory: $claude_dir"
}

install_claude_skills() {
  local skills_src="$REPO_ROOT/claude_skills"
  local skills_dst="$HOME/.claude/skills"

  if [[ ! -d "$skills_src" ]]; then
    return
  fi

  mkdir -p "$skills_dst"

  # Clean up obsolete CCB skills (replaced by unified ask/ping)
  local obsolete_skills="pend cask gask oask dask lask cpend gpend opend dpend lpend cping gping oping dping lping"
  for obs_skill in $obsolete_skills; do
    if [[ -d "$skills_dst/$obs_skill" ]]; then
      rm -rf "$skills_dst/$obs_skill"
      echo "  Removed obsolete skill: $obs_skill"
    fi
  done

  echo "Installing Claude skills (bash SKILL.md templates)..."
  for skill_dir in "$skills_src"/*/; do
    [[ -d "$skill_dir" ]] || continue
    local skill_name
    skill_name=$(basename "$skill_dir")
    [[ "$skill_name" == "docs" ]] && continue

    local src_skill_md=""
    if [[ -f "$skill_dir/SKILL.md.bash" ]]; then
      src_skill_md="$skill_dir/SKILL.md.bash"
    elif [[ -f "$skill_dir/SKILL.md" ]]; then
      src_skill_md="$skill_dir/SKILL.md"
    else
      continue
    fi

    local dst_dir="$skills_dst/$skill_name"
    local dst_skill_md="$dst_dir/SKILL.md"
    mkdir -p "$dst_dir"
    if [[ -e "$dst_skill_md" ]] && [[ "$src_skill_md" -ef "$dst_skill_md" ]]; then
      :
    else
      cp -f "$src_skill_md" "$dst_skill_md"
    fi

    # Copy additional subdirectories (e.g., references/) if they exist
    for subdir in "$skill_dir"*/; do
      if [[ -d "$subdir" ]]; then
        local subdir_name
        subdir_name=$(basename "$subdir")
        local dst_subdir="$dst_dir/$subdir_name"
        if [[ -e "$dst_subdir" ]] && [[ "$subdir" -ef "$dst_subdir" ]]; then
          continue
        fi
        cp -rf "$subdir" "$dst_subdir"
      fi
    done

    echo "  Updated skill: $skill_name"
  done

  # Shared docs live at skills/docs but are not a "skill directory". Install them as well.
  if [[ -d "$skills_src/docs" ]]; then
    rm -rf "$skills_dst/docs"
    cp -r "$skills_src/docs" "$skills_dst/docs"
    echo "  Installed skills docs: docs/"
  fi
  echo "Updated Claude skills directory: $skills_dst"
}

install_codex_skills() {
  local skills_src="$REPO_ROOT/codex_skills"
  local skills_dst="${CODEX_HOME:-$HOME/.codex}/skills"

  if [[ ! -d "$skills_src" ]]; then
    return
  fi

  mkdir -p "$skills_dst"

  # Clean up obsolete CCB skills (replaced by unified ask/ping)
  local obsolete_skills="pend cask gask oask dask lask cpend gpend opend dpend lpend cping gping oping dping lping"
  for obs_skill in $obsolete_skills; do
    if [[ -d "$skills_dst/$obs_skill" ]]; then
      rm -rf "$skills_dst/$obs_skill"
      echo "  Removed obsolete skill: $obs_skill"
    fi
  done

  echo "Installing Codex skills (bash SKILL.md templates)..."
  for skill_dir in "$skills_src"/*/; do
    [[ -d "$skill_dir" ]] || continue
    local skill_name
    skill_name=$(basename "$skill_dir")

    local src_skill_md=""
    if [[ -f "$skill_dir/SKILL.md.bash" ]]; then
      src_skill_md="$skill_dir/SKILL.md.bash"
    elif [[ -f "$skill_dir/SKILL.md" ]]; then
      src_skill_md="$skill_dir/SKILL.md"
    else
      continue
    fi

    local dst_dir="$skills_dst/$skill_name"
    local dst_skill_md="$dst_dir/SKILL.md"
    mkdir -p "$dst_dir"
    if [[ -e "$dst_skill_md" ]] && [[ "$src_skill_md" -ef "$dst_skill_md" ]]; then
      :
    else
      cp -f "$src_skill_md" "$dst_skill_md"
    fi

    # Copy additional subdirectories (e.g., references/) if they exist
    for subdir in "$skill_dir"*/; do
      if [[ -d "$subdir" ]]; then
        local subdir_name
        subdir_name=$(basename "$subdir")
        local dst_subdir="$dst_dir/$subdir_name"
        if [[ -e "$dst_subdir" ]] && [[ "$subdir" -ef "$dst_subdir" ]]; then
          continue
        fi
        cp -rf "$subdir" "$dst_subdir"
      fi
    done

    echo "  Updated Codex skill: $skill_name"
  done
  echo "Updated Codex skills directory: $skills_dst"
}

CCB_START_MARKER="<!-- CCB_CONFIG_START -->"
CCB_END_MARKER="<!-- CCB_CONFIG_END -->"
LEGACY_RULE_MARKER="## Codex Collaboration Rules"

install_claude_md_config() {
  local claude_md="$HOME/.claude/CLAUDE.md"
  mkdir -p "$HOME/.claude"
  if ! pick_python_bin; then
    echo "ERROR: python required to update CLAUDE.md"
    return 1
  fi

  # Use temp file to avoid Bash 3.2 heredoc parsing bug with single quotes
  local ccb_tmpfile=""
  ccb_tmpfile="$(mktemp)" || { echo "Failed to create temp file"; return 1; }
  cat > "$ccb_tmpfile" << 'AI_RULES'
<!-- CCB_CONFIG_START -->
## AI Collaboration
Use `/ask <provider>` to consult other AI assistants (codex/claude).
Use `/ping <provider>` to check connectivity.
Responses arrive in-pane via reply-via-ask.

Providers: `codex`, `claude`
<!-- CCB_CONFIG_END -->
AI_RULES
  local ccb_content
  ccb_content="$(cat "$ccb_tmpfile")"
  rm -f "$ccb_tmpfile" >/dev/null 2>&1 || true
  ccb_tmpfile=""

  if [[ -f "$claude_md" ]]; then
    if grep -q "$CCB_START_MARKER" "$claude_md" 2>/dev/null; then
      echo "Updating existing CCB config block..."
      "$PYTHON_BIN" -c "
import re

with open('$claude_md', 'r', encoding='utf-8') as f:
    content = f.read()
pattern = r'<!-- CCB_CONFIG_START -->.*?<!-- CCB_CONFIG_END -->'
new_block = '''$ccb_content'''
content = re.sub(pattern, new_block, content, flags=re.DOTALL)
with open('$claude_md', 'w', encoding='utf-8') as f:
    f.write(content)
"
    elif grep -qE "$LEGACY_RULE_MARKER|## Codex Collaboration Rules|## Gemini|## OpenCode" "$claude_md" 2>/dev/null; then
      echo "Removing legacy rules and adding new CCB config block..."
      "$PYTHON_BIN" -c "
	import re

	with open('$claude_md', 'r', encoding='utf-8') as f:
	    content = f.read()
	patterns = [
	    r'## Codex Collaboration Rules.*?(?=\\n## (?!Gemini)|\\Z)',
	    r'## Gemini Collaboration Rules.*?(?=\\n## |\\Z)',
	    r'## OpenCode Collaboration Rules.*?(?=\\n## |\\Z)',
	]
	for p in patterns:
	    content = re.sub(p, '', content, flags=re.DOTALL)
	content = content.rstrip() + '\\n'
with open('$claude_md', 'w', encoding='utf-8') as f:
    f.write(content)
"
      echo "$ccb_content" >> "$claude_md"
    else
      echo "$ccb_content" >> "$claude_md"
    fi
  else
    echo "$ccb_content" > "$claude_md"
  fi

  echo "Updated AI collaboration rules in $claude_md"
}

install_settings_permissions() {
  local settings_file="$HOME/.claude/settings.json"
  mkdir -p "$HOME/.claude"

  local perms_to_add=(
    'Bash(ask *)'
    'Bash(ping *)'
  )

  if [[ ! -f "$settings_file" ]]; then
    cat > "$settings_file" << 'SETTINGS'
{
	      "permissions": {
	    "allow": [
	      "Bash(ask *)",
	      "Bash(ping *)"
	    ],
    "deny": []
  }
}
SETTINGS
    echo "Created $settings_file with permissions"
    return
  fi

  local added=0
  for perm in "${perms_to_add[@]}"; do
    if ! grep -q "$perm" "$settings_file" 2>/dev/null; then
      if pick_python_bin; then
        "$PYTHON_BIN" -c "
import json
import sys

path = '$settings_file'
perm = '$perm'
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = {}
    perms = data.get('permissions')
    if not isinstance(perms, dict):
        perms = {'allow': [], 'deny': []}
        data['permissions'] = perms
    allow = perms.get('allow')
    if not isinstance(allow, list):
        allow = []
        perms['allow'] = allow
    if perm not in allow:
        allow.append(perm)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
except Exception as e:
    sys.stderr.write(f'WARN: failed updating {path}: {e}\\n')
    sys.exit(0)
"
        added=1
      fi
    fi
  done

  if [[ $added -eq 1 ]]; then
    echo "Updated $settings_file permissions"
  else
    echo "Permissions already exist in $settings_file"
  fi
}

CCB_TMUX_MARKER="# ============================================================================="
CCB_TMUX_MARKER_LEGACY="# CCB tmux configuration"

install_tmux_config() {
  local tmux_conf="$HOME/.tmux.conf"
  local ccb_tmux_conf="$REPO_ROOT/config/tmux-ccb.conf"
  local ccb_status_script="$REPO_ROOT/config/ccb-status.sh"
  local status_install_path="$BIN_DIR/ccb-status.sh"

  if [[ ! -f "$ccb_tmux_conf" ]]; then
    return
  fi

  mkdir -p "$BIN_DIR"

  # Install ccb-status.sh script
  if [[ -f "$ccb_status_script" ]]; then
    cp "$ccb_status_script" "$status_install_path"
    chmod +x "$status_install_path"
    echo "Installed: $status_install_path"
  fi

  # Install ccb-border.sh script (dynamic pane border colors)
  local ccb_border_script="$REPO_ROOT/config/ccb-border.sh"
  local border_install_path="$BIN_DIR/ccb-border.sh"
  if [[ -f "$ccb_border_script" ]]; then
    cp "$ccb_border_script" "$border_install_path"
    chmod +x "$border_install_path"
    echo "Installed: $border_install_path"
  fi

  # Install ccb-git.sh script (cached git status for tmux status line)
  local ccb_git_script="$REPO_ROOT/config/ccb-git.sh"
  local git_install_path="$BIN_DIR/ccb-git.sh"
  if [[ -f "$ccb_git_script" ]]; then
    cp "$ccb_git_script" "$git_install_path"
    chmod +x "$git_install_path"
    echo "Installed: $git_install_path"
  fi

  # Install tmux UI toggle scripts (enable/disable CCB theming per-session)
  local ccb_tmux_on_script="$REPO_ROOT/config/ccb-tmux-on.sh"
  local ccb_tmux_off_script="$REPO_ROOT/config/ccb-tmux-off.sh"
  if [[ -f "$ccb_tmux_on_script" ]]; then
    cp "$ccb_tmux_on_script" "$BIN_DIR/ccb-tmux-on.sh"
    chmod +x "$BIN_DIR/ccb-tmux-on.sh"
    echo "Installed: $BIN_DIR/ccb-tmux-on.sh"
  fi
  if [[ -f "$ccb_tmux_off_script" ]]; then
    cp "$ccb_tmux_off_script" "$BIN_DIR/ccb-tmux-off.sh"
    chmod +x "$BIN_DIR/ccb-tmux-off.sh"
    echo "Installed: $BIN_DIR/ccb-tmux-off.sh"
  fi

  # Check if already configured (new or legacy marker)
  local already_configured=false
  if [[ -f "$tmux_conf" ]]; then
    if grep -q "$CCB_TMUX_MARKER" "$tmux_conf" 2>/dev/null || \
       grep -q "$CCB_TMUX_MARKER_LEGACY" "$tmux_conf" 2>/dev/null; then
      already_configured=true
    fi
  fi

  if $already_configured; then
    # Update existing config: remove old CCB block and re-add
    echo "Updating CCB tmux configuration..."
    if pick_any_python_bin; then
      "$PYTHON_BIN" -c "
import re
with open('$tmux_conf', 'r', encoding='utf-8') as f:
    content = f.read()
# Remove old CCB tmux config block (both new and legacy markers)
pattern = r'\n*# =+\n# CCB \(Claude Code Bridge\) tmux configuration.*?# =+\n# End of CCB tmux configuration\n# =+'
content = re.sub(pattern, '', content, flags=re.DOTALL)
pattern = r'\n*# CCB tmux configuration.*'
content = re.sub(pattern, '', content, flags=re.DOTALL)
with open('$tmux_conf', 'w', encoding='utf-8') as f:
    f.write(content.strip() + '\n' if content.strip() else '')
"
    fi
  else
    # Backup existing config if present
    if [[ -f "$tmux_conf" ]]; then
      cp "$tmux_conf" "$tmux_conf.bak.$(date +%Y%m%d%H%M%S)"
    fi
  fi

  # Append CCB tmux config (fill in BIN_DIR placeholders)
  {
    echo ""
    if pick_any_python_bin; then
      "$PYTHON_BIN" -c "
import sys

path = '$ccb_tmux_conf'
bin_dir = '$BIN_DIR'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
sys.stdout.write(content.replace('@CCB_BIN_DIR@', bin_dir))
" 2>/dev/null || cat "$ccb_tmux_conf"
    else
      cat "$ccb_tmux_conf"
    fi
  } >> "$tmux_conf"

  echo "Updated tmux configuration: $tmux_conf"
  echo "   - CCB tmux integration (copy mode, mouse, pane management)"
  echo "   - CCB theme is enabled only while CCB is running (auto restore on exit)"
  echo "   - Vi-style pane management with h/j/k/l"
  echo "   - Mouse support and better copy mode"
  echo "   - Run 'tmux source ~/.tmux.conf' to apply (or restart tmux)"

  # Best-effort: if a tmux server is already running, reload config automatically.
  # (Avoid spawning a new server when tmux isn't running.)
  if command -v tmux >/dev/null 2>&1; then
    if tmux list-sessions >/dev/null 2>&1; then
      if tmux source-file "$tmux_conf" >/dev/null 2>&1; then
        echo "Reloaded tmux configuration in running server."
      else
        echo "WARN: Failed to reload tmux configuration automatically; run: tmux source ~/.tmux.conf"
      fi
    fi
  fi
}

uninstall_tmux_config() {
  local tmux_conf="$HOME/.tmux.conf"
  local status_script="$BIN_DIR/ccb-status.sh"
  local border_script="$BIN_DIR/ccb-border.sh"
  local tmux_on_script="$BIN_DIR/ccb-tmux-on.sh"
  local tmux_off_script="$BIN_DIR/ccb-tmux-off.sh"

  # Remove ccb-status.sh script
  if [[ -f "$status_script" ]]; then
    rm -f "$status_script"
    echo "Removed: $status_script"
  fi

  # Remove ccb-border.sh script
  if [[ -f "$border_script" ]]; then
    rm -f "$border_script"
    echo "Removed: $border_script"
  fi

  # Remove tmux UI toggle scripts
  if [[ -f "$tmux_on_script" ]]; then
    rm -f "$tmux_on_script"
    echo "Removed: $tmux_on_script"
  fi
  if [[ -f "$tmux_off_script" ]]; then
    rm -f "$tmux_off_script"
    echo "Removed: $tmux_off_script"
  fi

  if [[ ! -f "$tmux_conf" ]]; then
    return
  fi

  # Check for both new and legacy markers
  if ! grep -q "$CCB_TMUX_MARKER" "$tmux_conf" 2>/dev/null && \
     ! grep -q "$CCB_TMUX_MARKER_LEGACY" "$tmux_conf" 2>/dev/null; then
    return
  fi

  echo "Removing CCB tmux configuration..."
  if pick_any_python_bin; then
    "$PYTHON_BIN" -c "
import re
with open('$tmux_conf', 'r', encoding='utf-8') as f:
    content = f.read()
# Remove CCB tmux config block (both new and legacy markers)
pattern = r'\n*# =+\n# CCB \(Claude Code Bridge\) tmux configuration.*?# =+\n# End of CCB tmux configuration\n# =+'
content = re.sub(pattern, '', content, flags=re.DOTALL)
pattern = r'\n*# CCB tmux configuration.*'
content = re.sub(pattern, '', content, flags=re.DOTALL)
with open('$tmux_conf', 'w', encoding='utf-8') as f:
    f.write(content.strip() + '\n' if content.strip() else '')
"
    echo "Removed CCB tmux configuration from $tmux_conf"
  fi
}

install_requirements() {
  require_python_version
  require_terminal_backend
  if ! has_wezterm; then
    echo
    echo "================================================================"
    echo "NOTE: Recommend installing WezTerm as terminal frontend (better experience)"
    echo "   - Website: https://wezfurlong.org/wezterm/"
    echo "   - Benefits: Smoother split/scroll/font rendering, more stable bridging in WezTerm mode"
    echo "================================================================"
    echo
  fi
}

# Clean up legacy daemon files
cleanup_legacy_files() {
  echo "Cleaning up legacy files..."
  local cleaned=0

  # Legacy daemon scripts in bin/
  local legacy_daemons="askd caskd gaskd oaskd laskd daskd"
  for daemon in $legacy_daemons; do
    if [[ -f "$BIN_DIR/$daemon" ]]; then
      rm -f "$BIN_DIR/$daemon"
      echo "  Removed legacy daemon script: $BIN_DIR/$daemon"
      cleaned=$((cleaned + 1))
    fi
    # Also check install prefix bin
    if [[ -f "$INSTALL_PREFIX/bin/$daemon" ]]; then
      rm -f "$INSTALL_PREFIX/bin/$daemon"
      echo "  Removed legacy daemon script: $INSTALL_PREFIX/bin/$daemon"
      cleaned=$((cleaned + 1))
    fi
  done

  # Legacy daemon state files in ~/.cache/ccb/
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/ccb"
  local legacy_states="askd.json caskd.json gaskd.json oaskd.json laskd.json daskd.json"
  for state in $legacy_states; do
    if [[ -f "$cache_dir/$state" ]]; then
      rm -f "$cache_dir/$state"
      echo "  Removed legacy state file: $cache_dir/$state"
      cleaned=$((cleaned + 1))
    fi
  done

  # Legacy daemon module files in lib/
  local legacy_modules="caskd_daemon.py gaskd_daemon.py oaskd_daemon.py laskd_daemon.py daskd_daemon.py"
  for module in $legacy_modules; do
    if [[ -f "$INSTALL_PREFIX/lib/$module" ]]; then
      rm -f "$INSTALL_PREFIX/lib/$module"
      echo "  Removed legacy module: $INSTALL_PREFIX/lib/$module"
      cleaned=$((cleaned + 1))
    fi
  done

  if [[ $cleaned -eq 0 ]]; then
    echo "  No legacy files found"
  else
    echo "  Cleaned up $cleaned legacy file(s)"
  fi
}

install_all() {
  install_requirements
  cleanup_legacy_files
  save_wezterm_config
  copy_project
  install_bin_links
  ensure_path_configured
  install_claude_commands
  install_claude_skills
  install_codex_skills
  install_claude_md_config
  install_settings_permissions
  install_tmux_config
  echo "OK: Installation complete"
  echo "   Project dir    : $INSTALL_PREFIX"
  echo "   Executable dir : $BIN_DIR"
  echo "   Claude commands updated"
  echo "   Global CLAUDE.md configured with AI collaboration rules"
  echo "   Global settings.json permissions added"
}

uninstall_claude_md_config() {
  local claude_md="$HOME/.claude/CLAUDE.md"

  if [[ ! -f "$claude_md" ]]; then
    return
  fi

  if grep -q "$CCB_START_MARKER" "$claude_md" 2>/dev/null; then
    echo "Removing CCB config block from CLAUDE.md..."
    if pick_any_python_bin; then
      "$PYTHON_BIN" -c "
import re

with open('$claude_md', 'r', encoding='utf-8') as f:
    content = f.read()
pattern = r'\\n?<!-- CCB_CONFIG_START -->.*?<!-- CCB_CONFIG_END -->\\n?'
content = re.sub(pattern, '\\n', content, flags=re.DOTALL)
content = content.strip() + '\\n'
with open('$claude_md', 'w', encoding='utf-8') as f:
    f.write(content)
"
      echo "Removed CCB config from CLAUDE.md"
    else
      echo "WARN: python required to clean CLAUDE.md, please manually remove CCB_CONFIG block"
    fi
  elif grep -qE "$LEGACY_RULE_MARKER|## Codex Collaboration Rules|## Gemini|## OpenCode" "$claude_md" 2>/dev/null; then
    echo "Removing legacy collaboration rules from CLAUDE.md..."
    if pick_any_python_bin; then
      "$PYTHON_BIN" -c "
	import re

	with open('$claude_md', 'r', encoding='utf-8') as f:
	    content = f.read()
	patterns = [
	    r'## Codex Collaboration Rules.*?(?=\\n## (?!Gemini)|\\Z)',
	    r'## Gemini Collaboration Rules.*?(?=\\n## |\\Z)',
	    r'## OpenCode Collaboration Rules.*?(?=\\n## |\\Z)',
	]
	for p in patterns:
	    content = re.sub(p, '', content, flags=re.DOTALL)
	content = content.rstrip() + '\\n'
with open('$claude_md', 'w', encoding='utf-8') as f:
    f.write(content)
"
      echo "Removed collaboration rules from CLAUDE.md"
    else
      echo "WARN: python required to clean CLAUDE.md, please manually remove collaboration rules"
    fi
  fi
}

uninstall_settings_permissions() {
  local settings_file="$HOME/.claude/settings.json"

  if [[ ! -f "$settings_file" ]]; then
    return
  fi

  local perms_to_remove=(
    'Bash(ask *)'
    'Bash(ping *)'
    'Bash(pend *)'
    'Bash(cask:*)'
    'Bash(cpend)'
    'Bash(cping)'
    'Bash(gask:*)'
    'Bash(gpend)'
    'Bash(gping)'
    'Bash(oask:*)'
    'Bash(opend)'
    'Bash(oping)'
  )

  if pick_any_python_bin; then
    local has_perms=0
    for perm in "${perms_to_remove[@]}"; do
      if grep -q "$perm" "$settings_file" 2>/dev/null; then
        has_perms=1
        break
      fi
    done

    if [[ $has_perms -eq 1 ]]; then
      echo "Removing permission configuration from settings.json..."
      "$PYTHON_BIN" -c "
import json
import sys

path = '$settings_file'
perms_to_remove = [
    'Bash(ask *)',
    'Bash(ping *)',
    'Bash(pend *)',
    'Bash(cask:*)',
    'Bash(cpend)',
    'Bash(cping)',
    'Bash(gask:*)',
    'Bash(gpend)',
    'Bash(gping)',
    'Bash(oask:*)',
    'Bash(opend)',
    'Bash(oping)',
]
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        sys.exit(0)
    perms = data.get('permissions')
    if not isinstance(perms, dict):
        sys.exit(0)
    allow = perms.get('allow')
    if not isinstance(allow, list):
        sys.exit(0)
    perms['allow'] = [p for p in allow if p not in perms_to_remove]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
except Exception:
    sys.exit(0)
"
      echo "Removed permission configuration from settings.json"
    fi
  else
    echo "WARN: python required to clean settings.json, please manually remove related permissions"
  fi
}

uninstall_claude_skills() {
  local skills_dst="$HOME/.claude/skills"
  local ccb_skills="ask ping autonew mounted all-plan"

  if [[ ! -d "$skills_dst" ]]; then
    return
  fi

  echo "Removing CCB Claude skills..."
  for skill in $ccb_skills; do
    if [[ -d "$skills_dst/$skill" ]]; then
      rm -rf "$skills_dst/$skill"
      echo "  Removed skill: $skill"
    fi
  done
}

uninstall_codex_skills() {
  local skills_dst="${CODEX_HOME:-$HOME/.codex}/skills"
  local ccb_skills="ask ping mounted all-plan"

  if [[ ! -d "$skills_dst" ]]; then
    return
  fi

  echo "Removing CCB Codex skills..."
  for skill in $ccb_skills; do
    if [[ -d "$skills_dst/$skill" ]]; then
      rm -rf "$skills_dst/$skill"
      echo "  Removed skill: $skill"
    fi
  done
}

uninstall_all() {
  echo "INFO: Starting ccb uninstall..."

  # 1. Remove project directory
  if [[ -d "$INSTALL_PREFIX" ]]; then
    rm -rf "$INSTALL_PREFIX"
    echo "Removed project directory: $INSTALL_PREFIX"
  fi

  # 2. Remove bin links
  for path in "${SCRIPTS_TO_LINK[@]}"; do
    local name
    name="$(basename "$path")"
    if [[ -L "$BIN_DIR/$name" || -f "$BIN_DIR/$name" ]]; then
      rm -f "$BIN_DIR/$name"
    fi
  done
  for legacy in "${LEGACY_SCRIPTS[@]}"; do
    rm -f "$BIN_DIR/$legacy"
  done
  echo "Removed bin links: $BIN_DIR"

  # 3. Remove Claude command files (clean all possible locations)
  local cmd_dirs=(
    "$HOME/.claude/commands"
    "$HOME/.config/claude/commands"
    "$HOME/.local/share/claude/commands"
  )
  for dir in "${cmd_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
      for doc in "${CLAUDE_MARKDOWN[@]+"${CLAUDE_MARKDOWN[@]}"}"; do
        rm -f "$dir/$doc"
      done
      echo "Cleaned commands directory: $dir"
    fi
  done

  # 4. Remove collaboration rules from CLAUDE.md
  uninstall_claude_md_config

  # 5. Remove permission configuration from settings.json
  uninstall_settings_permissions

  # 6. Remove tmux configuration
  uninstall_tmux_config

  # 7. Remove Claude skills
  uninstall_claude_skills

  # 8. Remove Codex skills
  uninstall_codex_skills

  echo "OK: Uninstall complete"
  echo "   NOTE: Dependencies (python, tmux, wezterm) were not removed"
}

main() {
  if [[ $# -ne 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    install)
      install_all
      ;;
    uninstall)
      uninstall_all
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
