# CLAUDE.md

This file provides guidance to AI coding assistants working in this repository.
It is the single source of truth: `AGENTS.md` (Codex) and `GEMINI.md` (Gemini CLI)
are symlinks to this file, so edit only this one.

## Repository Purpose

Production-tested Claude Code configuration patterns, extracted from a large Next.js + TypeScript monorepo running these in production. This documents what's actually running, not theoretical ideas.

This repo is **public**. Do not name the private source repo, its internal URLs, or its infrastructure specifics in files, commit messages, or PR descriptions. Generalize patterns rather than copying project-specific names.

## Key Files

- **setup.md** - Per-repo Claude Code configuration (hooks, skills, slash commands, subagents, dev docs, review loops)
- **review-loops.md** - Production-hardened review loops (external-primary/in-model-fallback reviewers, the `MATERIAL_FINDINGS` contract, three review passes, credential-stripping wrapper, subagent scope hygiene)
- **sdlc-standards.md** - Repo-level engineering invariants an agent must respect (generated-file discipline, migration-as-deploy-gate, nightly→release gating, preview-env smoke tests, fail-fast env validation)
- **laptop-setup.md** - One-time machine setup (worktrees, status line, usage monitoring, keyboard shortcuts)
- **README.md** - Public-facing description of the repository

## This Repo's Own Configuration

The repo eats its own dog food, scoped to what a docs-only project can use:

```text
CLAUDE.md              # single source of truth
AGENTS.md -> CLAUDE.md # symlink (Codex CLI)
GEMINI.md -> CLAUDE.md # symlink (Gemini CLI)
.claude/
  settings.json        # permissions allow-list (committed)
  commands/create-pr.md
```

Deliberately absent: skills, `skill-rules.json`, and the hook suite. There's no
build, no test suite, and no dependencies here, so build-checkers and test gates
would be dead weight. Don't add them just because setup.md documents them —
setup.md describes what a *product* repo needs.

If you add a new instruction file for another assistant, symlink it to
`CLAUDE.md` rather than copying. Duplicated instruction files drift.

## Git Workflow

Always use feature branches and PRs for changes:

1. Create a branch: `git checkout -b feature/description`
2. Make commits on the branch
3. Push and create PR: `gh pr create`
4. Wait for approval before merging
5. Never push directly to master
