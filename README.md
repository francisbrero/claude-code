# Claude Code Best Practices

Production-tested Claude Code configuration patterns, extracted from a large Next.js + TypeScript monorepo running these in production. Everything here is in real use, not theoretical.

## What's in here

### [setup.md](setup.md) — Per-repo configuration

The main document. Covers everything you need to add Claude Code to a project:

- **`/fix-issue` command** — End-to-end GitHub issue workflow with session resume, automated plan/code review loops, and TaskCreate integration
- **`/create-pr` command** — PR creation that reads and fills your PR template
- **`/jira-to-github-issue`** — Jira ticket conversion
- **Skills system** — Auto-activated docs, runbooks, and guardrails via keyword matching
- **`/grill-me`** — Interrogate a design until every branch is resolved, before it becomes an issue
- **Skills system** — Auto-activated docs, runbooks, and guardrails via keyword matching
- **Hooks** — Across UserPromptSubmit, PostToolUse, and Stop events:
  - Skill activation, acceptance criteria validation, domain guardrails
  - Repeat error detection, preflight context loading
  - File edit tracking, formatting
  - Build checking, test reminders, derived-file drift detection, integration test gates
  - Hooks that read tool *output* and react to failure signals in-turn
- **Subagents** — Gating vs. descriptive reviewers, two-stage Haiku-reads/Opus-judges delegation, degrade paths
- **Dev docs** — Context persistence across sessions
- **CLAUDE.md patterns** — PR template enforcement, permissions allow-list, review loops
- **Context window management** — MCP guidelines, subagent patterns
- **Cost discipline** — Why no hook should call a model, and a grep to prove none does

### [laptop-setup.md](laptop-setup.md) — One-time machine setup

Run once per laptop:
- Git worktrees for parallel Claude instances
- Custom status line (git state, model, context budget, session cost)
- Usage and plan-limit monitoring
- Keyboard shortcuts reference

## License

MIT
