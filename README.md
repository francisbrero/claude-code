# Claude Code Best Practices — from hip-phoenix

Production-tested Claude Code configuration patterns extracted from [hip-phoenix](https://phoenix.hginsights.com/). Everything here is running in production, not theoretical.

## What's in here

### [setup.md](setup.md) — Per-repo configuration

The main document. Covers everything you need to add Claude Code to a project:

- **`/fix-issue` command** — End-to-end GitHub issue workflow with session resume, automated plan/code review loops, and TaskCreate integration
- **`/create-pr` command** — PR creation that reads and fills your PR template
- **`/jira-to-github-issue`** — Jira ticket conversion
- **Skills system** — Auto-activated docs, runbooks, and guardrails via keyword matching
- **Hooks** — 11 hooks across UserPromptSubmit, PostToolUse, and Stop events:
  - Skill activation, acceptance criteria validation, domain guardrails
  - Repeat error detection, preflight context loading
  - File edit tracking, formatting
  - Build checking, test reminders, derived-file drift detection, integration test gates
- **Dev docs** — Context persistence across sessions
- **CLAUDE.md patterns** — PR template enforcement, permissions allow-list, review loops
- **Context window management** — MCP guidelines, subagent patterns

### [laptop-setup.md](laptop-setup.md) — One-time machine setup

Run once per laptop:
- Git worktrees for parallel Claude instances
- Keyboard shortcuts reference

## License

MIT
