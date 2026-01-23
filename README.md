# Claude Code Best Practices

A curated collection of best practices for Claude Code and agentic coding workflows.

## Purpose

This repository tracks learnings and patterns for building an AI-native Software Development Lifecycle (SDLC). The goal is to distill insights from various sources—GitHub repos, Reddit discussions, X posts, and real-world experience—into actionable guidelines.

The output is a production-ready configuration (see [setup.md](setup.md)) that can be applied to active projects like [Phoenix](https://phoenix.hginsights.com/).

## What This Is

- A knowledge base for Claude Code configuration patterns
- Best practices for hooks, skills, and slash commands
- Curated resources from the agentic coding community
- Templates and guidelines ready for production use

## What This Is Not

- A collection of hype or theoretical ideas
- Untested configurations
- One-size-fits-all solutions

Everything here is evaluated for practical incorporation into real codebases.

## Repository Structure

```
.
├── README.md           # This file
├── setup.md            # Per-repo Claude Code configuration template
├── laptop-setup.md     # One-time machine setup (remote sessions, worktrees)
├── sources.md          # Curated resources and references
├── scripts/            # Shell helpers for remote session control
│   ├── claude-remote.zsh   # tmux session management
│   ├── claude-headless.zsh # Headless mode wrappers
│   └── SETUP.md            # Step-by-step remote access guide
└── experimental/       # Research and experimental features
    └── remote-claude-sessions.md
```

## Key Components

### Per-Repo Configuration ([setup.md](setup.md))

Configuration to add to each project:

1. **Fix-Issue Command** - Slash command for GitHub issue workflows
2. **Skills System** - Auto-activated documentation and runbooks
3. **Hooks** - Automatic skill activation, file tracking, build checking
4. **Dev Docs System** - Context persistence across sessions
5. **Context Window Management** - MCP guidelines, subagent patterns

### One-Time Laptop Setup ([laptop-setup.md](laptop-setup.md))

Machine-level configuration (run once):

1. **Git Worktrees** - Run multiple Claude instances without conflicts
2. **Remote Session Control** - Control Claude from your phone via Tailscale + Mosh
3. **Shell Helpers** - `cc`, `ccbg`, `cca` commands for session management
4. **Keyboard Shortcuts** - Quick reference for Claude Code

## Resources

See [sources.md](sources.md) for the curated list of references and inspirations.

## Target Projects

These practices are designed for and tested with:

- [Phoenix](https://phoenix.hginsights.com/) - HG Insights' data platform ([docs](https://phoenix.hginsights.com/docs))

## Contributing

Contributions are welcome! If you have:

- Useful Claude Code configurations
- Agentic coding patterns that work well
- Resources worth adding to the collection

Please open an issue or submit a PR.

## License

MIT
