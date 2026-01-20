# Claude Remote Session Helpers
# Source this file in your .zshrc: source ~/path/to/claude-remote.zsh
#
# Lightweight functions for controlling Claude Code sessions remotely.
# No external dependencies beyond tmux (already common).

# ============================================================================
# Session Management
# ============================================================================

# Start or attach to a named Claude session
# Usage: claude-session [name] [options]
#   name    - Session name (default: "claude")
#   options - Passed to claude command (e.g., --dangerously-skip-permissions)
#
# Examples:
#   claude-session                    # Default session
#   claude-session myproject          # Named session
#   claude-session auto --dangerously-skip-permissions  # Unattended mode
claude-session() {
    local name="${1:-claude}"
    shift 2>/dev/null  # Remove name from args, ignore if no args
    local claude_opts="$@"

    # Check if session exists
    if tmux has-session -t "$name" 2>/dev/null; then
        echo "Attaching to existing session: $name"
        tmux attach -t "$name"
    else
        echo "Creating new session: $name"
        if [[ -n "$claude_opts" ]]; then
            tmux new-session -s "$name" "claude $claude_opts; exec zsh"
        else
            tmux new-session -s "$name" "claude; exec zsh"
        fi
    fi
}

# Start Claude in background (for remote access later)
# Usage: claude-bg [name] [options]
claude-bg() {
    local name="${1:-claude}"
    shift 2>/dev/null
    local claude_opts="$@"

    if tmux has-session -t "$name" 2>/dev/null; then
        echo "Session '$name' already exists. Use: tmux attach -t $name"
        return 1
    fi

    echo "Starting Claude in background session: $name"
    if [[ -n "$claude_opts" ]]; then
        tmux new-session -d -s "$name" "claude $claude_opts; exec zsh"
    else
        tmux new-session -d -s "$name" "claude; exec zsh"
    fi
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

    if tmux has-session -t "$session_name" 2>/dev/null; then
        echo "Attaching to: $session_name"
        tmux attach -t "$session_name"
    else
        echo "Starting Claude for project: $project_name"
        tmux new-session -s "$session_name" "claude $@; exec zsh"
    fi
}

# Start project Claude in background
# Usage: ccbg [options]
ccbg() {
    local project_name=$(basename "$(pwd)")
    local session_name="cc-${project_name}"

    if tmux has-session -t "$session_name" 2>/dev/null; then
        echo "Session '$session_name' already exists"
        return 1
    fi

    echo "Starting background session: $session_name"
    tmux new-session -d -s "$session_name" "claude $@; exec zsh"
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
# Unattended Mode
# ============================================================================

# Start Claude with skip-permissions for unattended work
# Usage: claude-auto [name]
# WARNING: Only use in trusted environments
claude-auto() {
    local name="${1:-claude-auto}"

    echo "⚠️  Starting Claude with --dangerously-skip-permissions"
    echo "    Only use this in trusted environments!"
    echo ""

    claude-session "$name" --dangerously-skip-permissions
}

# Background auto session
# Usage: claude-auto-bg [name]
claude-auto-bg() {
    local name="${1:-claude-auto}"

    echo "⚠️  Starting unattended Claude session: $name"
    claude-bg "$name" --dangerously-skip-permissions
}
