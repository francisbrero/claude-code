# Claude Remote Session Helpers
# Source this file in your .zshrc: source ~/path/to/claude-remote.zsh
#
# Lightweight functions for controlling Claude Code sessions remotely.
# No external dependencies beyond tmux (already common).
#
# By default, sessions use --dangerously-skip-permissions for unattended work.
# Set CLAUDE_SAFE=1 to disable this behavior.

# Default flags for claude command
CLAUDE_DEFAULT_FLAGS="--dangerously-skip-permissions"

# ============================================================================
# Session Management
# ============================================================================

# Start or attach to a named Claude session
# Usage: claude-session [name] [options]
#   name    - Session name (default: "claude")
#   options - Additional options passed to claude command
#
# Examples:
#   claude-session                    # Default session (with skip-permissions)
#   claude-session myproject          # Named session
#   CLAUDE_SAFE=1 claude-session      # Without skip-permissions
claude-session() {
    local name="${1:-claude}"
    shift 2>/dev/null  # Remove name from args, ignore if no args
    local claude_opts="$@"

    # Add default flags unless CLAUDE_SAFE is set
    if [[ -z "$CLAUDE_SAFE" ]]; then
        claude_opts="$CLAUDE_DEFAULT_FLAGS $claude_opts"
    fi

    # Check if session exists
    if tmux has-session -t "$name" 2>/dev/null; then
        echo "Attaching to existing session: $name"
        tmux attach -t "$name"
    else
        echo "Creating new session: $name"
        tmux new-session -s "$name" "claude $claude_opts; exec zsh"
    fi
}

# Start Claude in background (for remote access later)
# Usage: claude-bg [name] [options]
claude-bg() {
    local name="${1:-claude}"
    shift 2>/dev/null
    local claude_opts="$@"

    # Add default flags unless CLAUDE_SAFE is set
    if [[ -z "$CLAUDE_SAFE" ]]; then
        claude_opts="$CLAUDE_DEFAULT_FLAGS $claude_opts"
    fi

    if tmux has-session -t "$name" 2>/dev/null; then
        echo "Session '$name' already exists. Use: tmux attach -t $name"
        return 1
    fi

    echo "Starting Claude in background session: $name"
    tmux new-session -d -s "$name" "claude $claude_opts; exec zsh"
    echo "Session started. Attach with: tmux attach -t $name"
}

# List all Claude sessions
# Usage: claude-ls
claude-ls() {
    echo "Claude sessions:"
    tmux ls 2>/dev/null | grep -E "^claude|^cc-" || echo "  (none)"
}

# Kill a Claude session
# Usage: claude-kill [name]
claude-kill() {
    local name="${1:-claude}"
    if tmux has-session -t "$name" 2>/dev/null; then
        tmux kill-session -t "$name"
        echo "Killed session: $name"
    else
        echo "No session named: $name"
        return 1
    fi
}

# ============================================================================
# Project Sessions
# ============================================================================

# Start Claude in current directory with project-based session name
# Usage: cc [options]
#   Creates session named "cc-<dirname>"
cc() {
    local project_name=$(basename "$(pwd)")
    local session_name="cc-${project_name}"
    local claude_opts="$@"

    # Add default flags unless CLAUDE_SAFE is set
    if [[ -z "$CLAUDE_SAFE" ]]; then
        claude_opts="$CLAUDE_DEFAULT_FLAGS $claude_opts"
    fi

    if tmux has-session -t "$session_name" 2>/dev/null; then
        echo "Attaching to: $session_name"
        tmux attach -t "$session_name"
    else
        echo "Starting Claude for project: $project_name"
        tmux new-session -s "$session_name" "claude $claude_opts; exec zsh"
    fi
}

# Start project Claude in background
# Usage: ccbg [options]
ccbg() {
    local project_name=$(basename "$(pwd)")
    local session_name="cc-${project_name}"
    local claude_opts="$@"

    # Add default flags unless CLAUDE_SAFE is set
    if [[ -z "$CLAUDE_SAFE" ]]; then
        claude_opts="$CLAUDE_DEFAULT_FLAGS $claude_opts"
    fi

    if tmux has-session -t "$session_name" 2>/dev/null; then
        echo "Session '$session_name' already exists"
        return 1
    fi

    echo "Starting background session: $session_name"
    tmux new-session -d -s "$session_name" "claude $claude_opts; exec zsh"
    echo "Attach with: tmux attach -t $session_name"
}

# ============================================================================
# Remote Access Helpers
# ============================================================================

# Quick attach - tries common session names
# Usage: cca
cca() {
    # Try project-based session first
    local project_name=$(basename "$(pwd)")
    local session_name="cc-${project_name}"

    if tmux has-session -t "$session_name" 2>/dev/null; then
        tmux attach -t "$session_name"
        return
    fi

    # Try default claude session
    if tmux has-session -t "claude" 2>/dev/null; then
        tmux attach -t "claude"
        return
    fi

    # Show available sessions
    echo "No Claude session found. Available sessions:"
    tmux ls 2>/dev/null || echo "  (none)"
}

# Send a prompt to a running Claude session (without attaching)
# Usage: claude-send [session] "prompt"
#
# Examples:
#   claude-send "What's the status?"
#   claude-send myproject "Run the tests"
claude-send() {
    local session="claude"
    local prompt=""

    if [[ $# -eq 1 ]]; then
        prompt="$1"
    elif [[ $# -eq 2 ]]; then
        session="$1"
        prompt="$2"
    else
        echo "Usage: claude-send [session] \"prompt\""
        return 1
    fi

    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo "No session named: $session"
        return 1
    fi

    # Send the prompt and Enter
    tmux send-keys -t "$session" "$prompt" Enter
    echo "Sent to $session: $prompt"
}

# Capture output from a Claude session
# Usage: claude-capture [session] [lines]
claude-capture() {
    local session="${1:-claude}"
    local lines="${2:-50}"

    if ! tmux has-session -t "$session" 2>/dev/null; then
        echo "No session named: $session"
        return 1
    fi

    tmux capture-pane -t "$session" -p -S "-$lines"
}

# ============================================================================
# Safe Mode (without skip-permissions)
# ============================================================================

# Start Claude WITHOUT skip-permissions (requires manual approval)
# Usage: cc-safe
cc-safe() {
    CLAUDE_SAFE=1 cc "$@"
}

# Background safe session
# Usage: ccbg-safe
ccbg-safe() {
    CLAUDE_SAFE=1 ccbg "$@"
}
