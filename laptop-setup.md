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

## 2. Keyboard Shortcuts Reference

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
