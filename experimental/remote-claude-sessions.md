# Remote Claude Code Sessions

Control Claude Code sessions from your phone, other devices, or bots like Clawdbot.

## Overview

There are three main approaches:

1. **tmux + SSH** - Attach to running Claude sessions from any device
2. **Headless Mode** - Run Claude programmatically via CLI flags
3. **Bot Integration** - Use Slack bots or Clawdbot to trigger Claude Code

---

## 1. tmux + SSH (Interactive Sessions)

### Prerequisites

- Mac/Linux machine running Claude Code
- tmux installed (`brew install tmux`)
- SSH access (local network or Tailscale/playit.gg for remote)
- Mobile SSH client (Blink Shell, Termius, etc.)

### Basic Setup

**On your dev machine:**

```bash
# Start a named tmux session
tmux new -s claude

# Run Claude Code inside
claude

# Detach without killing: Ctrl+B, then D
```

**From phone/other device:**

```bash
# SSH into your machine
ssh user@your-machine

# Attach to the session
tmux attach -t claude
```

### Enhanced Setup with Tailscale + Mosh

For reliable remote access that survives network changes:

**1. Install Tailscale on both devices**
- Mac: `brew install tailscale`
- Phone: Install Tailscale app

**2. Connect both to same Tailnet**

**3. Enable SSH on Mac**
- System Preferences > Sharing > Remote Login
- Add your SSH key to `~/.ssh/authorized_keys`

**4. Install Mosh for resilient connections**
```bash
brew install mosh
```

**5. Use Terminus on iPhone**
- Supports Mosh protocol
- Generate SSH key in app settings
- Connect via: `mosh user@mac-tailscale-name`

**6. Attach to Claude session**
```bash
tmux attach -t claude
```

> "Mosh should stay connected forever" across network changes - no more dropped SSH connections.

Source: [Remote controlling Claude Code](https://adim.in/p/remote-control-claude-code/)

### Session Management Tools

#### claunch

Project-based session manager with automatic tmux setup:

```bash
# Install
bash <(curl -s https://raw.githubusercontent.com/0xkaz/claunch/main/install.sh)

# Usage - creates tmux session named claude-<project>
cd myproject
claunch --tmux

# Attach from anywhere
tmux attach -t claude-myproject
```

Source: [claunch](https://github.com/0xkaz/claunch)

#### cld-tmux

Simple CLI for persistent Claude Code sessions:

```bash
# Install
curl -sSL https://raw.githubusercontent.com/terminalgravity/cld-tmux/main/install.sh | bash

# Start session
cld myproject

# List sessions
cld -l

# Interactive selector
cld -s
```

Source: [cld-tmux](https://github.com/TerminalGravity/cld-tmux)

### tmux Quick Reference

| Command | Action |
|---------|--------|
| `tmux new -s name` | Create named session |
| `tmux attach -t name` | Attach to session |
| `tmux ls` | List sessions |
| `Ctrl+B, D` | Detach from session |
| `Ctrl+B, [` | Scroll mode (q to exit) |
| `Ctrl+B, c` | New window |
| `Ctrl+B, n/p` | Next/previous window |

---

## 2. Headless Mode (Programmatic)

For automation, CI/CD, and bot integration, use Claude Code's `-p` (print) flag.

### Basic Usage

```bash
# Simple query
claude -p "What does the auth module do?"

# With JSON output
claude -p "Summarize this project" --output-format json

# Stream responses
claude -p "Review this code" --output-format stream-json
```

### Key Flags

| Flag | Purpose |
|------|---------|
| `-p` | Non-interactive mode |
| `--output-format json` | Structured output with metadata |
| `--output-format stream-json` | Real-time streaming |
| `--continue` | Continue most recent conversation |
| `--resume <session_id>` | Continue specific session |
| `--allowedTools "Bash,Read,Edit"` | Auto-approve tools |
| `--append-system-prompt "..."` | Add to system prompt |

### Session Continuation

```bash
# Start a session, capture ID
session_id=$(claude -p "Review this codebase" --output-format json | jq -r '.session_id')

# Continue that session later
claude -p "Now focus on the database queries" --resume "$session_id"
```

### CI/CD Example

```bash
# PR review automation
gh pr diff "$PR_NUMBER" | claude -p \
  --append-system-prompt "You are a code reviewer. Be concise." \
  --output-format json \
  --allowedTools "Read"
```

### Limitations

- Slash commands (`/commit`, `/review`) only work in interactive mode
- Describe the task instead: `claude -p "Create a commit for staged changes"`
- No custom output styles in `-p` mode currently

Source: [Claude Code Headless Docs](https://code.claude.com/docs/en/headless)

---

## 3. Bot Integration

### Clawdbot

Self-hosted AI assistant that routes to Claude across multiple channels.

**Supported channels:** WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, Matrix

**Install:**
```bash
npm install -g clawdbot@latest
clawdbot onboard --install-daemon
```

**Configure Slack:**
Set `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN` in environment or config.

**Architecture:**
- Local Gateway runs as control plane
- Connects to your Claude credentials (Pro/Max)
- Routes messages from any channel to Claude
- Supports voice, canvas, and tool execution

**Key features:**
- Multi-channel inbox
- Per-session sandboxing for security
- Tailscale integration for remote access
- Cron and webhook automation

Source: [Clawdbot](https://github.com/clawdbot/clawdbot)

### Claude Code Slack Bot (mpociot)

Connects local Claude Code agent to Slack:

```bash
git clone https://github.com/mpociot/claude-code-slack-bot
cd claude-code-slack-bot
npm install
```

**Setup:**
1. Create Slack app at api.slack.com/apps
2. Get Bot Token (xoxb-), App Token (xapp-), Signing Secret
3. Create `.env` with credentials
4. Run the bot

**Usage:**
- DM the bot for private conversations
- Mention in channels (set working directory first)
- Thread conversations maintain context

Source: [claude-code-slack-bot](https://github.com/mpociot/claude-code-slack-bot)

### Official Claude Code in Slack

Anthropic's native integration that routes coding tasks to Claude Code web sessions.

Source: [Claude Code in Slack](https://code.claude.com/docs/en/slack)

---

## 4. tmux Automation (Advanced)

### Sending Commands Programmatically

```bash
# Send a prompt to a running Claude session
tmux send-keys -t claude "Review the auth module" Enter

# Read the pane content
tmux capture-pane -t claude -p
```

### claude-code-tools (tmux-cli)

"Playwright for terminals" - enables programmatic terminal control:

```bash
# Install
uv tool install claude-code-tools

# Use as Claude Code skill
/tmux-cli
```

This allows Claude to:
- Control other terminal panes
- Automate multi-pane workflows
- Test interactive CLI applications

Source: [claude-code-tools](https://github.com/pchalasani/claude-code-tools)

---

## 5. Remote Access Without VPN

If you don't have Tailscale, use playit.gg for public tunneling:

1. Install Bitvise SSH Server (Windows) or enable SSH (Mac/Linux)
2. Create TCP tunnel on port 22 at playit.gg
3. Get public hostname from dashboard
4. Connect: `ssh user@your-playit-hostname`
5. Attach to tmux session

Source: [Claude Code Mobile Setup](https://gist.github.com/ChrisColeTech/aecf3ddf7e80b5d03040177b4913323e)

---

## Recommended Setup

For personal use from phone:

1. **Tailscale** - Zero-config VPN between devices
2. **Mosh** - Resilient mobile connections
3. **Terminus** - iOS SSH/Mosh client
4. **tmux** - Session persistence
5. **Simple shell functions** - See `scripts/claude-remote.zsh` (no external deps)

For bot/automation:

1. **Headless mode** (`-p` flag) for simple tasks - See `scripts/claude-headless.zsh`
2. **Clawdbot** for multi-channel personal assistant (see evaluation below)
3. **claude-code-slack-bot** for team Slack integration

---

## Clawdbot Evaluation

**What it is:** Self-hosted AI gateway that routes messages from multiple channels (WhatsApp, Telegram, Slack, etc.) to Claude.

**Pros:**
- Multi-channel access from a single bot
- Works with Claude Pro/Max subscription
- Tailscale integration for secure remote access
- Voice support, canvas, tool execution

**Cons:**
- Adds complexity (Node.js daemon, channel configuration)
- Requires managing tokens/credentials for each channel
- Another moving part to maintain

**Verdict:** For personal use, direct tmux + SSH/Mosh is simpler and more reliable. Clawdbot is worth considering if you need:
- WhatsApp/Telegram access (no native SSH clients)
- Voice interaction
- Multiple people accessing the same Claude instance

**Skip Clawdbot if:**
- You have a good SSH client on your phone (Terminus)
- You're the only user
- You prefer minimal dependencies

For most solo developers, the lightweight approach (Tailscale + Mosh + tmux + shell functions) covers all needs without additional complexity

---

## Security Considerations

- Use SSH keys, not passwords
- Tailscale provides encrypted mesh network
- Consider `--dangerously-skip-permissions` implications
- Clawdbot defaults to "pairing" mode requiring approval for unknown senders
- Use sandboxing for group/channel sessions in Clawdbot

---

## Resources

- [Remote controlling Claude Code](https://adim.in/p/remote-control-claude-code/)
- [claunch](https://github.com/0xkaz/claunch)
- [cld-tmux](https://github.com/TerminalGravity/cld-tmux)
- [claude-code-tools](https://github.com/pchalasani/claude-code-tools)
- [Clawdbot](https://github.com/clawdbot/clawdbot)
- [Claude Code Slack Bot](https://github.com/mpociot/claude-code-slack-bot)
- [Claude Code Headless Docs](https://code.claude.com/docs/en/headless)
- [Claude Code in Slack](https://code.claude.com/docs/en/slack)
- [Claude Code + tmux workflow](https://www.blle.co/blog/claude-code-tmux-beautiful-terminal)
