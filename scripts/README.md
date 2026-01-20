# Claude Code Shell Scripts

Lightweight shell functions for remote Claude Code session management.

## Installation

Add to your `.zshrc`:

```bash
source /path/to/scripts/claude-remote.zsh   # Session management
source /path/to/scripts/claude-headless.zsh  # Headless mode helpers
```

## Quick Reference

### Interactive Sessions (claude-remote.zsh)

```bash
claude-session myproject   # Start/attach to session
claude-bg myproject        # Start in background
cc                         # Project session (uses pwd)
cca                        # Quick attach
claude-ls                  # List sessions
claude-send "prompt"       # Send to running session
claude-auto                # Unattended mode (skip permissions)
```

### Headless Mode (claude-headless.zsh)

```bash
cq "question"              # Quick query
cqj "question"             # JSON output
cc-continue "follow up"    # Continue conversation
cc-readonly "analyze"      # Read-only tools
cc-diff                    # Review git diff
cc-pr-desc                 # Generate PR description
```

## See Also

- Full documentation: `setup.md` section 9 (Remote Session Control)
- Research notes: `experimental/remote-claude-sessions.md`
