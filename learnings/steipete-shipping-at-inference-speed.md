# Shipping at Inference Speed

**Source**: https://steipete.me/posts/2025/shipping-at-inference-speed
**Type**: Article/Blog
**Author**: Peter Steinberger
**Date Processed**: 2026-01-16

## Summary

Peter Steinberger (creator of PSPDFKit) shares his workflow for AI-assisted development. Focus is on mindset shifts and workflow patterns rather than specific configurations. Key theme: engineer your codebase for agent efficiency, not just human readability.

## Key Learnings

### 1. Engineer Codebases for Agent Efficiency

Design codebases so agents can navigate and modify them effectively—this matters more than traditional human readability concerns. Consistent patterns, clear structure, good documentation.

**Applicability**: High
**Confidence**: Tested (author's production workflow)

### 2. Use Images for UI Iteration

Instead of lengthy text descriptions for UI changes, capture screenshots and add brief notes like "fix padding" or "redesign." Reduces token waste, improves accuracy.

**Applicability**: High
**Confidence**: Tested

### 3. CLI-First Architecture

Build command-line tools first to verify core functionality, then layer on extensions (web, UI). Makes verification easier and agent iteration faster.

**Applicability**: Medium
**Confidence**: Tested

### 4. Ask Questions Before Building

Start with conversation—let the model explore, research, and propose plans collaboratively before final implementation. Don't jump straight to "build this."

**Applicability**: High
**Confidence**: Tested

### 5. Structured Documentation in docs/

Maintain `docs/` folders with subsystem descriptions. Use scripts to force models to reference relevant docs during tasks, reducing hallucination.

**Applicability**: High
**Confidence**: Tested

### 6. Cross-Reference Existing Solutions

When tackling similar problems, direct the model to review prior implementations: "Look at ../project-folder and do the same for X." Leverages pattern completion.

**Applicability**: Medium
**Confidence**: Tested

### 7. Global Instructions File (AGENTS.md)

Keep a global instructions file with network topology, automation skills, and cross-project patterns.

**Applicability**: Medium
**Confidence**: Tested

### 8. Refactor Ad-Hoc, Not Scheduled

Address code quality during development rather than scheduling dedicated refactor days. When prompts slow down or ugliness appears, improve immediately.

**Applicability**: Medium
**Confidence**: Tested

### 9. Avoid Unnecessary Tooling

Slash commands, issue trackers, and complex state management often create overhead rather than value. Build immediately rather than documenting tasks.

**Applicability**: Low (conflicts with our approach)
**Confidence**: Tested but context-specific

### 10. Don't Revert, Modify

Ask the model to modify or adjust rather than reverting. Code evolves non-linearly—"walking up a mountain"—taking turns, sometimes backtracking slightly, but progressing overall.

**Applicability**: Medium
**Confidence**: Tested

### 11. Context Windows Are Capacity

Avoid restarting sessions unnecessarily. Full context windows enable better solutions—models can read more files before suggesting changes, reducing errors.

**Applicability**: High
**Confidence**: Tested

### 12. Stop Reading All Code

Monitor streams selectively; trust model output while remaining aware of component locations and system design. Expect working code on first attempt as baseline.

**Applicability**: Medium (mindset, not configuration)
**Confidence**: Tested

## Relevant Config

### Token limits mentioned
```
tool_output_token_limit = 25000
model_auto_compact_token_limit = 233000
```

### Features to enable
- `unified_exec`
- `web_search_request`
- `skills`
- `shell_snapshot`

## Assessment

### Recommended for setup.md

- [ ] **Add**: Guidance on using screenshots/images for UI iteration
- [ ] **Add**: Note about maintaining `docs/` folder for complex subsystems
- [ ] **Consider**: Cross-referencing pattern ("look at X and do the same")

### Not recommended

- **"Avoid tooling like slash commands"** - Conflicts with our approach. His workflow is more ad-hoc, ours is more structured. Both valid, different contexts.
- **Commit to main linearly** - Works for solo projects, not for teams
- **Global AGENTS.md** - Our skill system handles this differently
- **Token limit configs** - Too model/tool specific, may change

### Observations

This is a high-velocity solo developer workflow. Some patterns conflict with our more structured approach (dev docs, slash commands, planning). Neither is wrong—they optimize for different things:

- **Steinberger**: Speed, minimal overhead, trust the model
- **Our setup.md**: Consistency, quality gates, context persistence

The image-for-UI-iteration tip is universally applicable and worth adding.

## Questions for Review

1. **Screenshots for UI work**: Should we add guidance about using images instead of text descriptions for UI changes? This seems universally useful.

2. **docs/ folder pattern**: Should we add a recommendation to maintain structured documentation in a `docs/` folder that skills can reference?

3. **Philosophical alignment**: This source advocates for less tooling/structure. Do we want to note anywhere that our setup.md is optimized for consistency over raw speed?
