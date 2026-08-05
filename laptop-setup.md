# Laptop Setup (One-Time)

One-time machine configuration for Claude Code workflows. Run these once per laptop, not per project.

---

## 1. Git Worktrees

Worktrees enable running multiple Claude instances on overlapping work without conflicts.

**Basic worktree creation:**
```bash
git worktree add ../feature-branch feature-branch
# Run separate Claude instance in each worktree
```

**Fast worktree function (recommended):**

Since worktrees don't include gitignored files, use a shell function that:
1. Creates the worktree with a new branch
2. Copies all `.env` files (including in subdirectories)
3. Copies hidden dev folders (`.claude`, `.github`, `.vscode`, `.idea`)
4. Opens the new worktree in your editor

Add to `~/.config/zsh/wt.zsh` (and source from `.zshrc`):

```zsh
# Git Worktree Setup Function
# Usage: wt <feature-name>
# Creates a worktree in adjacent -worktrees folder and opens in Cursor
wt() {
    if [ -z "$1" ]; then
        echo "Usage: wt <feature-name>"
        return 1
    fi

    local FEATURE_NAME="$1"
    local CURRENT_DIR=$(basename "$(pwd)")
    local PARENT_DIR=$(dirname "$(pwd)")
    local WORKTREES_DIR="$PARENT_DIR/${CURRENT_DIR}-worktrees"

    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "Error: Not in a git repository"
        return 1
    fi

    # Create worktrees directory if needed
    [ ! -d "$WORKTREES_DIR" ] && mkdir -p "$WORKTREES_DIR"

    local WORKTREE_PATH="$WORKTREES_DIR/$FEATURE_NAME"

    if [ -d "$WORKTREE_PATH" ]; then
        echo "Error: Worktree '$FEATURE_NAME' already exists"
        return 1
    fi

    # Create the git worktree with new branch
    if git worktree add -b "$FEATURE_NAME" "$WORKTREE_PATH"; then
        echo "Created worktree: $WORKTREE_PATH"

        # Copy all .env files (including subdirectories)
        while IFS= read -r -d '' env_file; do
            local rel_path="${env_file#$(pwd)/}"
            local target_dir="$WORKTREE_PATH/$(dirname "$rel_path")"
            mkdir -p "$target_dir"
            cp "$env_file" "$target_dir/"
            echo "  Copied: $rel_path"
        done < <(find "$(pwd)" -name ".env*" -type f -print0)

        # Copy hidden dev folders
        local hidden_folders=(".claude" ".github" ".vscode" ".idea")
        for folder_name in "${hidden_folders[@]}"; do
            while IFS= read -r -d '' hidden_folder; do
                local rel_path="${hidden_folder#$(pwd)/}"
                local target_dir="$WORKTREE_PATH/$(dirname "$rel_path")"
                mkdir -p "$target_dir"
                cp -r "$hidden_folder" "$target_dir/"
                echo "  Copied: $rel_path"
            done < <(find "$(pwd)" -name "$folder_name" -type d -print0)
        done

        # Open in editor (adjust for your editor: code, cursor, zed, etc.)
        cursor -n "$WORKTREE_PATH"

        echo "Done! Branch '$FEATURE_NAME' ready at $WORKTREE_PATH"
    else
        echo "Failed to create git worktree"
        return 1
    fi
}
```

**Key features:**
- Creates worktrees in `project-worktrees/` adjacent to your project
- Recursively finds and copies all `.env*` files
- Copies `.claude/` so your Claude config travels with the worktree
- Opens directly in your editor

---

## 2. Custom Status Line

The statusline replaces Claude Code's default with a single line showing git state, model, context budget, and running cost. The context bar is the part that earns its keep — it makes context pressure visible before quality degrades, so you can `/compact` deliberately instead of getting auto-compacted mid-task.

**Sections, left to right:**

| Section | Shows |
|---------|-------|
| Git | Branch name, `(worktree)` marker when in a worktree, `✓` clean / `●` dirty |
| Model | Active model display name |
| Context | 20-char progress bar + used %, green <80k tokens, yellow <120k, red above |
| Stats | Session cost in USD, API time, lines added/removed |

**Install:**

Save the script to `~/.claude/statusline-command.sh`, then register it in `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash /Users/<you>/.claude/statusline-command.sh"
  }
}
```

The script reads the session JSON payload on stdin and prints one line. Requires `jq`.

```bash
#!/bin/bash
input=$(cat)

# Colors
RESET='\033[0m'
DIM='\033[2m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
SEP="${DIM} | ${RESET}"

# 1. Git branch and status
cwd=$(echo "$input" | jq -r '.cwd // empty')
if [ -n "$cwd" ]; then
  git_branch=$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null)
  git_dir=$(git -C "$cwd" rev-parse --git-dir 2>/dev/null)
  git_dirty=$(git -C "$cwd" status --porcelain 2>/dev/null | head -1)
else
  git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  git_dir=$(git rev-parse --git-dir 2>/dev/null)
  git_dirty=$(git status --porcelain 2>/dev/null | head -1)
fi

worktree_label=""
case "$git_dir" in
  */.git/worktrees/*) worktree_label=" (worktree)" ;;
esac

if [ -n "$git_branch" ]; then
  if [ -z "$git_dirty" ]; then
    status_indicator="${GREEN}✓${RESET}"
  else
    status_indicator="${YELLOW}●${RESET}"
  fi
  git_section="${CYAN}${git_branch}${worktree_label}${RESET} ${status_indicator}"
else
  git_section="${DIM}no git${RESET}"
fi

model=$(echo "$input" | jq -r '.model.display_name // "Claude"')
model_section="${CYAN}${model}${RESET}"

# 2. Context window progress bar with color thresholds
input_tokens=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

if [ "$input_tokens" -lt 80000 ] 2>/dev/null; then
  bar_color="$GREEN"
elif [ "$input_tokens" -lt 120000 ] 2>/dev/null; then
  bar_color="$YELLOW"
else
  bar_color="$RED"
fi

if [ -n "$used_pct" ]; then
  used_int=$(printf "%.0f" "$used_pct")
else
  used_int=0
fi

bar_filled=$((used_int / 5))
bar_empty=$((20 - bar_filled))
[ "$bar_filled" -gt 20 ] && bar_filled=20
[ "$bar_empty" -lt 0 ] && bar_empty=0

bar=""
i=0
while [ "$i" -lt "$bar_filled" ]; do
  bar="${bar}█"
  i=$((i + 1))
done
i=0
while [ "$i" -lt "$bar_empty" ]; do
  bar="${bar}░"
  i=$((i + 1))
done

ctx_section="${bar_color}[${bar}] ${used_int}%${RESET}"

# 3. Stats: cost, duration, api time, lines changed
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
api_ms=$(echo "$input" | jq -r '.cost.total_api_duration_ms // 0')
lines_added=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_removed=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')

cost_display=$(printf "\$%.2f" "$cost")

fmt_duration() {
  local total_s=$(( $1 / 1000 ))
  local d=$(( total_s / 86400 ))
  local h=$(( (total_s % 86400) / 3600 ))
  local m=$(( (total_s % 3600) / 60 ))
  local s=$(( total_s % 60 ))
  if [ "$d" -gt 0 ]; then
    printf "%dd %dh %02dm" "$d" "$h" "$m"
  elif [ "$h" -gt 0 ]; then
    printf "%dh %02dm %02ds" "$h" "$m" "$s"
  else
    printf "%dm %02ds" "$m" "$s"
  fi
}

api_display=$(fmt_duration "$api_ms")

lines_display="${GREEN}+${lines_added}${RESET} ${RED}-${lines_removed}${RESET}"

stats_section="${cost_display} · ${api_display} · ${lines_display}"

# Output
printf '%b\n' "${git_section}${SEP}${model_section}${SEP}${ctx_section}${SEP}${stats_section}"
```

**Cost guidance:** the statusline runs on every render. Keep it to shell and `jq` — never have it call a Claude model. If a statusline genuinely needs a model call, pin it to Haiku explicitly. This is the same rule that applies to hooks (see `setup.md` § Cost guidance).

`/statusline` can also generate one interactively if you'd rather start from scratch.

---

## 3. Usage & Cost Monitoring (AI Meter)

The statusline shows *per-session* cost. It says nothing about how close you are to your **plan limits** — that's what [claude-meter](https://github.com/francisbrero/claude-meter) covers.

AI Meter is a lightweight macOS menu bar app that shows AI usage limits at a glance, for both Claude and Codex.

**What it gives you:**
- Session (5-hour) and weekly limits, per provider
- Color-coded status: green <70%, yellow 70–90%, red >90%
- Countdown to the next session and weekly reset
- Notifications at 80% and 90% usage
- Auto-refresh every 2 minutes

**Install:**
1. Download `AIMeter.zip` from [Releases](https://github.com/francisbrero/claude-meter/releases)
2. Unzip and move `AI Meter.app` to `/Applications`
3. **Right-click → Open** the first time (unsigned app; Gatekeeper blocks a double-click)

Or build from source:
```bash
git clone https://github.com/francisbrero/claude-meter.git
cd claude-meter/ClaudeMeter
brew install xcodegen
xcodegen generate
open AIMeter.xcodeproj   # ⌘B to build, ⌘R to run
```

**Requirements:** macOS 13+, and Claude Code and/or Codex CLI installed and logged in. It reads OAuth credentials from the macOS Keychain — credentials never leave the machine, and providers you haven't configured simply don't appear.

**Gotcha:** if you see "Token missing required scope," your OAuth token predates the usage API. Re-authenticate:
```bash
claude logout && claude
```

**Why both:** the statusline tells you what this session is costing; AI Meter tells you whether you're about to hit a wall. Together they cover the two questions worth asking mid-task.

---

## 4. Keyboard Shortcuts Reference

| Shortcut | Action |
|----------|--------|
| `Ctrl+U` | Delete entire line (faster than backspace) |
| `!` | Quick bash command prefix |
| `@` | Search for files |
| `/` | Initiate slash commands |
| `Shift+Enter` | Multi-line input |
| `Tab` | Toggle thinking display |
| `Esc Esc` | Interrupt Claude / restore code |

### Useful Commands

| Command | Action |
|---------|--------|
| `/fork` | Fork conversation for parallel work |
| `/rewind` | Go back to a previous state |
| `/statusline` | Customize status display |
| `/checkpoints` | File-level undo points |
| `/compact` | Manually trigger context compaction |
| `/plugins` | View and manage MCPs and plugins |
