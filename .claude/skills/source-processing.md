---
description: Guidelines for processing and evaluating AI coding resources
globs:
  - "learnings/**/*.md"
  - "sources.md"
  - "setup.md"
alwaysApply: false
---

# Source Processing Skill

## Overview

Use this skill when reviewing resources about Claude Code, agentic coding, or AI-native development workflows. It provides context for evaluating whether learnings should be incorporated into setup.md.

## Evaluation Criteria

### High-Impact Patterns (Likely to Add)

- **Solves a real problem**: Addresses friction we've encountered or will encounter
- **Battle-tested**: Author reports using it in production, not just theory
- **Specific and actionable**: Can be implemented as concrete config/code
- **Fits our stack**: Compatible with our setup (hooks, skills, slash commands)

### Medium-Impact (Ask First)

- **Novel approach**: Different from what we have, but unclear if better
- **Partial fit**: Good idea but needs adaptation for our workflow
- **Unverified**: Sounds useful but no evidence of real-world usage

### Low-Impact (Usually Skip)

- **Generic advice**: "Write good prompts", "Be specific", etc.
- **Tool-specific**: Only works with specific editors/tools we don't use
- **Conflicts**: Contradicts patterns we've already validated
- **Over-engineered**: Adds complexity without clear benefit

## Source Type Handling

### Reddit Posts (r/ClaudeCode, etc.)

- Look for: workflow tips, hook examples, prompt patterns, pain points
- Watch for: anecdotal evidence, YMMV situations, outdated info
- Extract: specific configurations, command examples, before/after comparisons

### GitHub Repos

- Look for: .claude/ structure, CLAUDE.md patterns, hook implementations
- Watch for: over-engineering, project-specific configs that won't generalize
- Extract: reusable hooks, skill templates, command patterns

### Articles/Blogs

- Look for: Anthropic official guidance, case studies, architectural patterns
- Watch for: marketing fluff, outdated recommendations, vague advice
- Extract: concrete techniques, mental models, validated workflows

## Current setup.md Components

Reference these when evaluating new additions:

1. **Fix-Issue Command** - GitHub issue workflow
2. **Skills System** - Technical, runbooks, references with frontmatter
3. **Hooks** - UserPromptSubmit, PostToolUse, Stop
4. **Dev Docs** - Context persistence in webapp/dev/

## Questions to Ask Before Adding

1. Does this solve a problem we actually have?
2. Is this simpler than what we already have for the same purpose?
3. Can we test this before committing to it?
4. Does this conflict with existing patterns?
5. Is the maintenance burden worth the benefit?
