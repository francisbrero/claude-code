# Claude Code is a Beast – Tips from 6 Months of Hardcore Use

**Source**: https://www.reddit.com/r/ClaudeCode/comments/1oivs81/claude_code_is_a_beast_tips_from_6_months_of/
**Mirror**: https://dev.to/diet-code103/claude-code-is-a-beast-tips-from-6-months-of-hardcore-use-572n
**Repo**: https://github.com/diet103/claude-code-infrastructure-showcase
**Type**: Reddit + GitHub
**Date Processed**: 2026-01-16

## Summary

A comprehensive guide from someone who rewrote 300k+ lines of code solo in 6 months using Claude Code. The core insight is that skills alone don't activate automatically—you need hooks to force activation. Introduces a complete infrastructure with skill auto-activation, dev docs for context persistence, and specialized agents.

## Key Learnings

### 1. Skills Don't Auto-Activate (Need Hooks)

The fundamental discovery: skills remain dormant without manual activation. Solution is TypeScript hooks that analyze prompts and inject skill reminders before Claude processes the message.

**Applicability**: High
**Confidence**: Tested (6 months, 300k+ lines)

### 2. The 500-Line Rule for Skills

Anthropic recommends keeping skill files under 500 lines. For complex topics, use progressive disclosure: one main file (overview + navigation) plus resource files for specific topics. Claude loads incrementally as needed.

**Applicability**: High
**Confidence**: Tested + Anthropic-recommended

### 3. CLAUDE.md Should Be Minimal (~200 lines)

Move detailed guidelines to skills. CLAUDE.md should only contain:
- Quick commands (build, test, start)
- Service-specific configuration
- Task management workflow basics
- Points to skills for details

**Applicability**: High
**Confidence**: Tested

### 4. Dev Docs System (Three-File Pattern)

For multi-session tasks, create three files in `dev/active/[task-name]/`:
- `[task]-plan.md` - Strategic overview/approved plan
- `[task]-context.md` - Key decisions, file locations, current state
- `[task]-tasks.md` - Checklist with status

Critical: Update these before session compaction. When resuming, read all three before proceeding.

**Applicability**: High
**Confidence**: Tested

### 5. Hook Pipeline (#NoMessLeftBehind)

Three-stage hook system on Stop event:
1. **File Edit Tracker** - Logs which files were edited
2. **Build Checker** - Runs TypeScript build, shows errors
3. **Error Handling Reminder** - Detects risky patterns (try-catch, async, DB calls)

**Applicability**: High
**Confidence**: Tested

### 6. Prettier Hook Warning

Automatic Prettier formatting consumes significant context tokens via `<system-reminder>` notifications. Better to run Prettier manually between sessions.

**Applicability**: Medium
**Confidence**: Tested

### 7. PM2 for Backend Debugging

Use PM2 process manager so Claude can autonomously read logs and diagnose issues without manual copy/paste. Configure `ecosystem.config.js` with log file paths.

**Applicability**: Medium (depends on backend setup)
**Confidence**: Tested

### 8. Specialized Agents for Specific Tasks

Create agents with very specific roles and clear return instructions:
- `code-architecture-reviewer` - Best practices
- `build-error-resolver` - Systematic TypeScript fixes
- `auth-route-tester` - Authenticated route testing
- `strategic-plan-architect` - Detailed implementation plans

**Applicability**: Medium
**Confidence**: Tested

### 9. Scripts Attached to Skills

Link utility scripts to relevant skills rather than generating from scratch. Example: `test-auth-route.js` for authentication testing, database reset scripts, etc.

**Applicability**: Medium
**Confidence**: Tested

### 10. Prompt Philosophy

"Ask not what Claude can do for you, ask what context you can give Claude."

Key practices:
- Be specific about desired results
- Research first: ask for options, not solutions
- Don't lead questions—ask neutrally
- Re-prompt often (double-ESC for history)
- Self-reflect on poor outputs before blaming model

**Applicability**: High
**Confidence**: Tested

## Relevant Code/Config

### skill-rules.json structure
```json
{
  "backend-dev-guidelines": {
    "type": "domain",
    "enforcement": "suggest",
    "priority": "high",
    "promptTriggers": {
      "keywords": ["backend", "controller", "service", "API", "endpoint"],
      "intentPatterns": ["(create|add).*(route|endpoint|controller)"],
      "pathPatterns": ["backend/src/**/*.ts"],
      "contentPatterns": ["router.", "export.*Controller"]
    }
  }
}
```

### Documentation hierarchy
```
Root CLAUDE.md (100-200 lines)
├── Critical universal rules
├── Points to repo-specific docs
└── References skills for details

Each Repo's CLAUDE.md (50-100 lines)
├── Quick Start section
├── PROJECT_KNOWLEDGE.md (architecture)
└── TROUBLESHOOTING.md (common issues)
```

## Assessment

### Recommended for setup.md

- [x] **Already have**: Dev docs system (plan.md, context.md, tasks.md) ✓
- [x] **Already have**: Skill auto-activation hooks ✓
- [x] **Already have**: skill-rules.json with keywords/patterns ✓
- [x] **Already have**: Build checker on Stop ✓
- [x] **Already have**: File edit tracker ✓

- [ ] **Add**: 500-line rule guidance for skills
- [ ] **Add**: Prettier hook warning
- [ ] **Add**: CLAUDE.md size guidance (~200 lines, minimal)
- [ ] **Add**: Documentation hierarchy recommendation
- [ ] **Add**: Prompt philosophy section

### Not recommended

- **PM2 setup** - Too specific to Node.js backend services, not universal
- **Specialized agents list** - Project-specific, users should create their own
- **BetterTouchTool/SuperWhisper** - External tools, out of scope

## Questions for Review

1. **Prompt philosophy section**: Should we add a section to setup.md about prompting best practices, or is that out of scope for a configuration guide?

2. **500-line rule**: Should we explicitly add this as a requirement in the skill file format section?

3. **CLAUDE.md guidance**: Our setup.md currently doesn't give size guidance. Should we add a recommendation to keep it under 200 lines?

4. **Documentation hierarchy**: Should we recommend the nested CLAUDE.md pattern (root + repo-specific) for monorepos?
