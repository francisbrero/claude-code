# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Production-tested Claude Code configuration patterns, extracted from a large Next.js + TypeScript monorepo running these in production. This documents what's actually running, not theoretical ideas.

This repo is **public**. Do not name the private source repo, its internal URLs, or its infrastructure specifics in files, commit messages, or PR descriptions. Generalize patterns rather than copying project-specific names.

## Key Files

- **setup.md** - Per-repo Claude Code configuration (hooks, skills, slash commands, dev docs, review loops)
- **laptop-setup.md** - One-time machine setup (worktrees, keyboard shortcuts)
- **README.md** - Public-facing description of the repository

## Git Workflow

Always use feature branches and PRs for changes:

1. Create a branch: `git checkout -b feature/description`
2. Make commits on the branch
3. Push and create PR: `gh pr create`
4. Wait for approval before merging
5. Never push directly to master
