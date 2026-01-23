# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a knowledge repository for Claude Code best practices and agentic coding patterns. It collects learnings from community resources (GitHub, Reddit, X) and distills them into production-ready configurations for use in real projects like Phoenix.

## Key Files

- **setup.md** - Per-repo Claude Code configuration (hooks, skills, slash commands, dev docs)
- **laptop-setup.md** - One-time machine setup (remote sessions, worktrees, shell helpers)
- **sources.md** - Curated list of resources to review and incorporate
- **scripts/** - Shell helpers for remote session control
  - `claude-remote.zsh` - tmux session management (`cc`, `ccbg`, `cca`)
  - `claude-headless.zsh` - Headless mode wrappers (`cq`, `cc-diff`)
  - `SETUP.md` - Step-by-step remote access guide
- **experimental/** - Research and experimental features
- **README.md** - Public-facing description of the repository

## Workflow

1. Resources are added to `sources.md` under "To Review"
2. After reviewing, move them to "Reviewed sources" with key takeaways
3. Actionable patterns get incorporated into:
   - `setup.md` for per-repo configuration
   - `laptop-setup.md` for one-time machine setup
4. The goal is practical, tested configurations—not theoretical ideas

## Target Project

Phoenix (https://phoenix.hginsights.com/) - The primary project where these configurations will be applied.

## Git Workflow

Always use feature branches and PRs for changes:

1. Create a branch: `git checkout -b feature/description`
2. Make commits on the branch
3. Push and create PR: `gh pr create`
4. Wait for approval before merging
5. Never push directly to master
