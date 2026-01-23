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

## 2. Remote Session Control

Control Claude Code sessions from your phone or other devices.

See `remote-access/SETUP.md` for the full step-by-step guide.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR MAC                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  tmux session "claude"                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  Claude Code                                                  │  │   │
│  │  │  > Working on your code...                                    │  │   │
│  │  │  > (keeps running even when you disconnect)                   │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                              │
│                              │ mosh-server (UDP :60000-61000)              │
│                              │ survives network changes                     │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Tailscale VPN     │
                    │   (encrypted P2P)   │
                    │   no cloud routing  │
                    └──────────┬──────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────────────┐
│                              │                                YOUR PHONE    │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Termius (mosh client)                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  You see and control Claude Code here                         │  │   │
│  │  │  > Can switch WiFi ↔ cellular without disconnecting           │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prerequisites

- Mac with Claude Code installed
- tmux (`brew install tmux`)
- Mosh (`brew install mosh`)
- SSH enabled (System Settings > General > Sharing > Remote Login)
- Tailscale on Mac and phone
- Termius app on phone

### Quick Setup

**1. Install tools on Mac**
```bash
brew install tmux mosh
```

**2. Add mosh-server to PATH for SSH sessions**
```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshenv
```

**3. Add Tailscale alias**
```bash
echo 'alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"' >> ~/.zshrc
```

**4. Install shell helpers**
```bash
echo 'source ~/path/to/claude-code/scripts/claude-remote.zsh' >> ~/.zshrc
echo 'source ~/path/to/claude-code/scripts/claude-headless.zsh' >> ~/.zshrc
```

**5. Set up Tailscale**
- Install Tailscale app on both Mac and phone
- Sign in with same account on both
- Note your Mac's Tailscale name (e.g., `macbook-pro-9`)

**6. Set up SSH key from phone**
- In Termius: Keychain → Generate Key (Ed25519)
- Copy public key
- Add to Mac: `echo "YOUR_PUBLIC_KEY" >> ~/.ssh/authorized_keys`

**7. Connect from phone**
- Create host in Termius: hostname = Mac's Tailscale name
- Enable Mosh toggle
- Connect and run `cca` to attach to Claude session

### Session Helper Commands

| Command | Description |
|---------|-------------|
| `cc` | Start/attach to project session (with skip-permissions) |
| `ccbg` | Start project session in background |
| `cca` | Quick attach to any Claude session |
| `claude-ls` | List all Claude sessions |
| `claude-send "prompt"` | Send prompt without attaching |
| `claude-capture` | View recent session output |
| `cc-safe` | Start without skip-permissions |

### Headless Mode Commands

| Command | Description |
|---------|-------------|
| `cq "question"` | Quick text query |
| `cqj "question"` | JSON output |
| `cc-continue "follow up"` | Continue last conversation |
| `cc-readonly "analyze"` | Read-only tools only |
| `cc-diff` | Review git diff |
| `cc-pr-desc` | Generate PR description |

---

## 3. Keyboard Shortcuts Reference

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
