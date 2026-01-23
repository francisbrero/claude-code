# Claude Headless Mode Helpers
# Source this file in your .zshrc: source ~/path/to/claude-headless.zsh
#
# Wrapper functions for Claude Code's -p (print/headless) mode.
# Useful for automation, CI/CD, and programmatic access.

# ============================================================================
# Basic Queries
# ============================================================================

# Simple query with text output
# Usage: cq "question"
cq() {
    if [[ -z "$1" ]]; then
        echo "Usage: cq \"question\""
        return 1
    fi
    claude -p "$1"
}

# Query with JSON output (includes metadata, session_id)
# Usage: cqj "question"
cqj() {
    if [[ -z "$1" ]]; then
        echo "Usage: cqj \"question\""
        return 1
    fi
    claude -p "$1" --output-format json
}

# Query with streaming JSON (real-time output)
# Usage: cqs "question"
cqs() {
    if [[ -z "$1" ]]; then
        echo "Usage: cqs \"question\""
        return 1
    fi
    claude -p "$1" --output-format stream-json
}

# ============================================================================
# Session Management
# ============================================================================

# Continue most recent conversation
# Usage: cc-continue "follow up question"
cc-continue() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-continue \"follow up question\""
        return 1
    fi
    claude -p "$1" --continue
}

# Resume specific session
# Usage: cc-resume <session_id> "question"
cc-resume() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: cc-resume <session_id> \"question\""
        return 1
    fi
    local session_id="$1"
    shift
    claude -p "$*" --resume "$session_id"
}

# Start a session and return session_id for later continuation
# Usage: session_id=$(cc-start "initial prompt")
cc-start() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-start \"initial prompt\"" >&2
        return 1
    fi
    claude -p "$1" --output-format json | jq -r '.session_id'
}

# ============================================================================
# Tool Control
# ============================================================================

# Query with specific tools allowed (auto-approved)
# Usage: cc-with-tools "Bash,Read,Edit" "question"
cc-with-tools() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: cc-with-tools \"Tool1,Tool2\" \"question\""
        return 1
    fi
    local tools="$1"
    shift
    claude -p "$*" --allowedTools "$tools"
}

# Read-only query (only Read tool allowed)
# Usage: cc-readonly "analyze this codebase"
cc-readonly() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-readonly \"question\""
        return 1
    fi
    claude -p "$1" --allowedTools "Read,Glob,Grep"
}

# Query with edit capability
# Usage: cc-edit "refactor this function"
cc-edit() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-edit \"question\""
        return 1
    fi
    claude -p "$1" --allowedTools "Read,Glob,Grep,Edit,Write"
}

# Query with full capabilities (careful!)
# Usage: cc-full "implement this feature"
cc-full() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-full \"question\""
        return 1
    fi
    claude -p "$1" --allowedTools "Read,Glob,Grep,Edit,Write,Bash"
}

# ============================================================================
# Custom System Prompts
# ============================================================================

# Query with custom system prompt addition
# Usage: cc-prompt "You are a code reviewer. Be concise." "review this PR"
cc-prompt() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: cc-prompt \"system prompt addition\" \"question\""
        return 1
    fi
    local system_prompt="$1"
    shift
    claude -p "$*" --append-system-prompt "$system_prompt"
}

# Code review mode
# Usage: cc-review "review the auth module"
cc-review() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-review \"what to review\""
        return 1
    fi
    claude -p "$1" \
        --append-system-prompt "You are a code reviewer. Focus on bugs, security issues, and maintainability. Be specific and concise." \
        --allowedTools "Read,Glob,Grep"
}

# Explanation mode
# Usage: cc-explain "explain the auth flow"
cc-explain() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-explain \"what to explain\""
        return 1
    fi
    claude -p "$1" \
        --append-system-prompt "Explain clearly and concisely. Use code examples where helpful. Avoid unnecessary detail." \
        --allowedTools "Read,Glob,Grep"
}

# ============================================================================
# Pipeline Helpers
# ============================================================================

# Pipe input to Claude
# Usage: cat file.ts | cc-pipe "summarize this code"
cc-pipe() {
    local prompt="${1:-Analyze the following input:}"
    local input=$(cat)
    claude -p "$prompt

$input"
}

# Process file with Claude
# Usage: cc-file myfile.ts "explain this code"
cc-file() {
    if [[ $# -lt 2 ]]; then
        echo "Usage: cc-file <file> \"question\""
        return 1
    fi
    local file="$1"
    shift
    if [[ ! -f "$file" ]]; then
        echo "File not found: $file"
        return 1
    fi
    cat "$file" | cc-pipe "$*"
}

# Git diff review
# Usage: cc-diff           # Review staged changes
# Usage: cc-diff HEAD~3    # Review last 3 commits
cc-diff() {
    local ref="${1:-}"
    local diff=""

    if [[ -n "$ref" ]]; then
        diff=$(git diff "$ref")
    else
        diff=$(git diff --cached)
        if [[ -z "$diff" ]]; then
            diff=$(git diff)
        fi
    fi

    if [[ -z "$diff" ]]; then
        echo "No changes to review"
        return 1
    fi

    echo "$diff" | cc-pipe "Review this git diff. Focus on potential issues, bugs, or improvements. Be concise."
}

# PR description generator
# Usage: cc-pr-desc [base-branch]
cc-pr-desc() {
    local base="${1:-main}"
    local diff=$(git diff "$base"...HEAD)
    local commits=$(git log "$base"..HEAD --oneline)

    if [[ -z "$diff" ]]; then
        echo "No changes found vs $base"
        return 1
    fi

    claude -p "Generate a PR description for these changes.

Commits:
$commits

Diff:
$diff

Format:
## Summary
Brief description of what changed and why.

## Changes
- Bullet points of key changes

## Testing
How to test these changes." --output-format json | jq -r '.result'
}

# ============================================================================
# JSON Output Helpers
# ============================================================================

# Extract just the result text from JSON output
# Usage: cc-result "question"
cc-result() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-result \"question\""
        return 1
    fi
    claude -p "$1" --output-format json | jq -r '.result'
}

# Get session ID from last query
# Usage: session=$(cc-session "start a task")
cc-session() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-session \"question\"" >&2
        return 1
    fi
    claude -p "$1" --output-format json | jq -r '.session_id'
}

# Get cost info from query
# Usage: cc-cost "question"
cc-cost() {
    if [[ -z "$1" ]]; then
        echo "Usage: cc-cost \"question\""
        return 1
    fi
    claude -p "$1" --output-format json | jq '{
        input_tokens: .usage.input_tokens,
        output_tokens: .usage.output_tokens,
        total_cost: .cost_usd
    }'
}
