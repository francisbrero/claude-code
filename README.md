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

### [review-loops.md](review-loops.md) — Automated review loops & external-agent safety

What the review loops in `setup.md` look like after months in production:

- **Codex-primary, Opus-fallback reviewers** — pin the external reviewer's model explicitly, fall back to an in-model review on credit exhaustion/auth failure/format-less output so the loop never silently stalls
- **The `MATERIAL_FINDINGS` convergence contract** — severity-gated stop condition the wrapper agent can't re-litigate
- **Three review passes** — plan (before code), code (`base master`, not `uncommitted`), and post-PR (what a human reviewer sees on GitHub)
- **`codex-safe.sh`** — strip `DATABASE_URL`/`AUTH_SECRET`/API keys from the env before shelling out to an external agent
- **Subagent scope hygiene & model-tiering** — the skip-list that stops review/explore subagents from burning budget on `node_modules`, plus matching the model tier to the work: Haiku for the high-volume retrieval phase (read the diff, grep callers, gather context), Opus only for the verdict
- **Stop-hook gates** — derived-doc drift and live integration-test gates that catch what diff-only reviewers miss

### [sdlc-standards.md](sdlc-standards.md) — Repo-level standards an agent must respect

Engineering invariants worth porting to any repo — the ones that produce confident-but-wrong agent edits when missing:

- **Generated-file discipline** — one editable source → N generated outputs, each with a `DO NOT EDIT` header, a guardrail skill, and a CI drift check (TypeSpec → models; shared JSON → TS + Python)
- **The migration *is* the deploy gate** — the load-bearing `context:` status string, trigger-coverage gaps that look like "the migration broke," and never `db:push` against deployed envs
- **Validation decoupled from deployment** — gate the release on a scheduled nightly, with a bypass that demands and records a justification
- **Preview-env smoke tests** — require `curl`-against-a-real-deploy evidence for REST/MCP/OAuth/webhook changes, in the PR template
- **Fail fast at `predev`** — env validation + a `doctor` command so a broken environment is a named error, not a runtime crash

### [laptop-setup.md](laptop-setup.md) — One-time machine setup

Run once per laptop:
- Git worktrees for parallel Claude instances
- Custom status line (git state, model, context budget, session cost)
- Usage and plan-limit monitoring
- Keyboard shortcuts reference

## License

MIT
