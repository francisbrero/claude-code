# Effective Harnesses for Long-Running Agents

**Source**: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
**Type**: Article (Anthropic Engineering)
**Date Processed**: 2026-01-16

## Summary

Anthropic's engineering team shares patterns for building harnesses that enable agents to make progress across multiple sessions/context windows. Core insight: use a two-agent system (initializer + coding agent) with structured artifacts that persist across sessions. This is official Anthropic guidance.

## Key Learnings

### 1. Two-Agent Architecture

- **Initializer Agent**: Runs once to set up environment with comprehensive context
- **Coding Agent**: Handles all subsequent sessions, making incremental progress

**Applicability**: Medium (more relevant for autonomous/headless agents)
**Confidence**: Anthropic-recommended

### 2. Feature List as JSON with Status Tracking

Create a comprehensive JSON file listing all features/requirements, each with a `passes` field. Agents only modify the status field, preventing unintended changes to requirements.

```json
{
  "features": [
    { "id": 1, "description": "User login", "passes": false },
    { "id": 2, "description": "Dashboard view", "passes": true }
  ]
}
```

**Applicability**: High
**Confidence**: Anthropic-recommended

### 3. Progress Documentation File

Maintain a `claude-progress.txt` (or similar) logging what agents have accomplished between sessions. Read this at session start.

**Applicability**: High (aligns with our dev docs system)
**Confidence**: Anthropic-recommended

### 4. One Feature Per Session

Work on one feature per session to avoid context exhaustion mid-implementation. Commit each feature with descriptive messages before ending.

**Applicability**: High
**Confidence**: Anthropic-recommended

### 5. Session Initialization Routine

Every agent session should:
1. Check working directory (`pwd`)
2. Read git logs and progress files
3. Review feature list, select highest-priority incomplete item
4. Start dev server using provided script
5. Run basic smoke tests

**Applicability**: High
**Confidence**: Anthropic-recommended

### 6. Clean State Between Sessions

No half-implemented features. Each session should end with:
- Well-documented code ready for main branch
- No accumulated technical debt
- Clear handoff information for next session

**Applicability**: High (aligns with our dev docs system)
**Confidence**: Anthropic-recommended

### 7. Explicit Testing Requirement

Without explicit prompting, agents skip proper testing. Solutions:
- Provide browser automation tools for E2E verification
- Require testing as a human user would
- Only mark features complete after verification

**Applicability**: High
**Confidence**: Anthropic-recommended

### 8. Init Script for Environment Setup

Provide an `init.sh` script enabling quick environment startup without manual configuration. Saves tokens and time each session.

**Applicability**: Medium
**Confidence**: Anthropic-recommended

## Relevant Patterns

### Failure modes to prevent

| Problem | Prevention |
|---------|-----------|
| Premature "done" declarations | Explicit feature list with status tracking |
| Context exhaustion mid-task | One feature per session + progress tracking |
| Undocumented progress | Git commits + progress files |
| Incomplete testing | Mandate E2E verification |
| Setup overhead | Pre-written init scripts |

## Assessment

### Recommended for setup.md

- [ ] **Consider**: Session initialization checklist (read progress, check git, run tests)
- [ ] **Consider**: Explicit testing requirement before marking tasks complete
- [ ] **Reinforce**: Clean state principle (no half-implemented features)

### Already covered

- Progress documentation → Our dev docs system (context.md, tasks.md)
- Clean handoff → Our dev docs system
- Feature list with status tracking → **GitHub Issues + Jira sync + milestones** (better approach for teams—issue tracking belongs outside the code)
- One feature per session → **fix-issue command** already enforces this pattern

### Not recommended

- Two-agent architecture — More relevant for autonomous/headless setups, adds complexity for interactive use
- Init script — Too project-specific
- JSON feature list in code — We use GitHub Issues instead, which integrates with Jira and provides better visibility

## Questions for Review

1. **Session initialization checklist**: Should we add explicit guidance about what to do when resuming work (read progress, check git, run smoke tests)?

2. **Explicit testing requirement**: Should we add guidance that tests must pass before marking a task complete?
