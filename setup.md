Overview

I want to set up a production-quality Claude Code configuration for my project. This should include:

1. Fix-issue command - A slash command to fetch and implement GitHub issues
2. Additional commands - PR creation, Jira conversion, instance setup, design interrogation
3. Skills system - Auto-activated documentation, runbooks, and technical references
4. Hooks - Skill activation, edit tracking, build checking, guardrails, context pre-loading, and failure-signal nudges
5. Dev docs system - Context persistence across sessions
6. CLAUDE.md patterns - PR templates, review loops, permissions, guardrails
7. Committed subagents - Reviewers versioned with the repo, not the laptop

### Core Principle: Subagent Delegation

The dominant cost of a long Claude Code session is cache-read at Opus rates (~$1.50/MTok). At a typical 800K-token context, every broad inline grep re-reads the full cache — open-ended exploration in the main session is the most expensive shape of work you can do. The slash commands and hooks below are written around three rules:

1. **Targeted lookups stay in the main context.** When you know the file path or exact symbol, use `Read` or `Bash grep` directly.
2. **Open-ended exploration goes to an `Explore` subagent on Haiku** ("where does X live", "find callers of Y", "what implements Z"). Sidechain context is independent and Haiku is ~1/15 the input cost of Opus.
3. **Hooks that invoke a model pin to Haiku.** Hooks fire on every prompt — defaulting to inherited Opus is a quiet, recurring cost.

This is why the patterns below delegate exploration aggressively and reserve Opus for reasoning that needs the full context.

Directory Structure

Create this structure:

.claude/
├── agents/                    # Subagents, committed with the repo
│   ├── code-reviewer.md       # Gating quality review (MATERIAL_FINDINGS)
│   ├── plan-reviewer.md       # Gating plan review (MATERIAL_FINDINGS)
│   └── pr-impact-reviewer.md  # Descriptive blast-radius readout (never gates)
├── commands/
│   ├── fix-issue.md           # /fix-issue slash command
│   ├── create-pr.md           # /create-pr slash command
│   ├── jira-to-github-issue.md # /jira-to-github-issue command
│   ├── setup-instance.md      # /setup-instance command
│   └── grill-me.md            # /grill-me design interrogation
├── hooks/
│   ├── skill-activation-prompt.sh   # Shell wrapper
│   ├── skill-activation-prompt.ts   # TypeScript skill matcher
│   ├── file-edit-tracker.sh         # Track edited files
│   ├── post-tool-use-tracker.sh     # Track all tool usage
│   ├── build-checker.sh             # Run build check on Stop
│   ├── test-reminder.sh             # Remind about tests
│   ├── validate-acceptance-criteria.sh  # Issue readiness scoring
│   ├── domain-guardrail.sh          # Domain-specific pattern reminders
│   ├── repeat-error-detector.sh     # Detect repeated errors
│   ├── preflight-context.sh         # Pre-load relevant files on keywords
│   ├── derived-file-drift-checker.sh # Check derived files stay in sync
│   ├── test-gate-by-category.sh     # Remind integration tests by file category
│   ├── instrumentation-nudge.sh     # In-turn reminder to instrument new source files
│   ├── review-nudge.sh              # Nudge review after gh pr create / git push
│   ├── auth-expired-nudge.sh        # Self-heal expired cloud auth sessions
│   ├── __tests__/                   # Shell tests for the non-trivial hooks
│   ├── package.json                 # tsx dependency
│   └── tsconfig.json
├── skills/
│   ├── README.md
│   ├── skill-rules.json             # Keyword-to-skill mappings
│   ├── technical/                   # Domain knowledge skills
│   │   └── [framework].md
│   ├── runbooks/                    # Step-by-step guides
│   │   └── [procedure].md
│   └── reference/                   # Architecture docs
│       └── [system].md
└── settings.local.json              # Hook configuration + permissions

1. Fix-Issue Command (.claude/commands/fix-issue.md)

Create a slash command that:
- Fetches GitHub issue with gh issue view $ARGUMENTS
- Creates branch based on issue labels (feature/, bugfix/, etc.)
- Creates dev docs folder for context persistence
- Plans implementation in phases
- Waits for user approval before implementing
- Runs tests and checks before finalizing — **tests must pass before marking complete**
- Creates commit and PR when done

### Detailed Workflow

**Step 0: Session Resume Detection**
Before starting fresh, check if dev docs already exist for this issue:
```
if webapp/dev/active/issue-{number}/ exists:
  Read context.md for last checkpoint
  Resume from the last completed step
  Skip steps already done
```

**Step 1: Fetch Issue and Create Branch**
- `gh issue view $ARGUMENTS --json title,body,labels,assignees`
- Parse labels to determine branch prefix (feature/, bugfix/, chore/)
- `git checkout -b {prefix}/issue-{number}-{slug}`

**Step 2: Requirement Clarification**
- Parse the issue body for ambiguous requirements
- Use `AskUserQuestion` to clarify anything unclear before planning
- Document clarifications in context.md

**Step 3: Create Dev Docs**
- Create `webapp/dev/active/issue-{number}/`
- Write plan.md, context.md, tasks.md from templates

**Step 4: Install Dependencies (worktrees)**
- If in a worktree, run `pnpm install` to ensure node_modules are present
- Worktrees don't inherit gitignored files from the main tree

**Step 5: Plan Implementation**
- Break the issue into phases
- Use `TaskCreate` to create tasks with dependencies for progress tracking
- Each task gets: subject, description, activeForm, blockedBy relationships

**Search delegation rules (apply throughout planning and implementation):**
- **Targeted lookups stay in the main context.** If the issue names a file path or specific symbol, use `Read` or `Bash grep` directly. Example: the issue says "fix the bug in `src/lib/auth.ts:parseToken`" — read that file inline.
- **Open-ended exploration goes to an `Explore` subagent on Haiku.** Spawn `Explore` (model: `haiku`) for prompts like "where does feature X live," "find callers of Y," "what files implement Z." Use `sonnet` only when the search needs medium-thoroughness reasoning (e.g., classifying matches, comparing candidate files). Do not grep broadly in the main session.
- **Dividing-line example:** "Read `src/db/schema.ts` and add a `last_login` column" → main context. "Find every place we call the auth middleware and list which ones still use the legacy session shape" → `Explore` subagent on Haiku.

**Step 6: Implement with Plan Review**
- Implement each phase
- After planning, run automated plan review loop (see Section 8)
- Review continues until `MATERIAL_FINDINGS: false` or max 10 rounds
- Track review rounds in context.md

**Step 7: Test and Code Review**
- Run tests: `pnpm test`
- Run automated code review loop (see Section 8)
- Same convergence pattern: repeat until no material findings
- Fix any issues found

**Step 8: Create PR**
- Use `/create-pr` command (reads PR template, fills from context)
- Link to the original issue

**Step 9: Post Impact Readout (non-gating)**
- Run the `pr-impact-reviewer` subagent against the new PR
- Post its output as a sticky comment via the marker-scoped helper script
- This step **never blocks**: on any failure, note it and finish anyway (see Section 8)

### Dev Docs Templates

plan.md:
```markdown
# Plan: [Issue Title]

## Issue
[Link to GitHub issue]

## Approach
[High-level strategy]

## Phases
1. [Phase 1]
2. [Phase 2]

## Key Decisions
- [Decision and rationale]
```

context.md:
```markdown
# Context: [Issue Title]

## Current Step
Step N: [description]

## Key Files
- path/to/file.ts — [why it matters]

## Review Rounds
- Round 1: [findings summary]
- Round 2: MATERIAL_FINDINGS: false

## Next Steps
- [what to do next]
```

tasks.md:
```markdown
# Tasks

- [ ] Phase 1: [description]
- [ ] Phase 2: [description]
- [ ] Tests pass
- [ ] PR created
```

2. Additional Commands

### /create-pr (.claude/commands/create-pr.md)

Structured PR creation that respects the project's PR template:

```markdown
Create a pull request for the current branch.

Steps:
1. Read `.github/pull_request_template.md` if it exists
2. Run `git log main..HEAD --oneline` to get commit history
3. Run `git diff main..HEAD --stat` to get changed files summary
4. Fill in each section of the PR template using the git context
5. Use `gh pr create --title "..." --body "..."` to create the PR

IMPORTANT: `gh pr create --body` overrides GitHub's template auto-fill.
You MUST read and reproduce the template manually in the --body argument.
```

### /jira-to-github-issue (.claude/commands/jira-to-github-issue.md)

Convert Jira tickets to GitHub issues:

```markdown
Convert a Jira ticket to a GitHub issue.

Input: $ARGUMENTS (Jira ticket URL or key)

Steps:
1. Fetch the Jira ticket details (use the Jira MCP or curl the API).
2. Gather repo context via a single `Explore` subagent (model: `haiku`).
   Pass the Jira summary and ask the subagent to return:
   - related specs under `docs/specs/`
   - related knowledge / runbook files under `.claude/skills/`
   - related GitHub issues (`gh issue list --search ...`, `gh search code ...`)
   Do NOT run `find docs/specs/`, `gh search code`, or broad grep inline —
   that work belongs in the subagent so the main Opus context stays clean.
3. PM-coach gap analysis (stays in the main session — this is the part that
   benefits from Opus reasoning):
   - Compare the Jira ticket against the Explore findings.
   - Flag missing acceptance criteria, ambiguous scope, or unstated dependencies.
   - Propose concrete additions before filing.
4. Map Jira fields to GitHub issue format:
   - Summary → Title
   - Description → Body (convert Jira markup to GitHub markdown)
   - Priority → Labels
   - Story points → Labels (e.g., "points:3")
   - Acceptance criteria → Checklist in body
5. Create the issue: `gh issue create --title "..." --body "..." --label "..."`
6. Output the new issue URL.
```

### /setup-instance (.claude/commands/setup-instance.md)

Set up a new development instance:

```markdown
Set up a new development instance.

Steps:
1. Check prerequisites (Node.js version, pnpm, required CLIs)
2. Copy .env.example to .env if needed
3. Run `pnpm install`
4. Run database migrations if applicable
5. Verify the setup with a health check or build
6. Report any issues found
```

### /grill-me (.claude/commands/grill-me.md)

Interrogate a plan or design until every branch of the decision tree is resolved. This is the front half of `/fix-issue` — use it *before* filing an issue, when the thinking is still fuzzy.

```markdown
Interview me relentlessly about a plan, design, or idea until we reach
shared understanding. Topic: $ARGUMENTS (ask if empty).

Step 1: Get a detailed description — the problem, solutions considered,
        known constraints, what they're unsure about.

Step 2: Explore the codebase FIRST. Never ask the user something the code
        already answers. Verify claims about current state, find existing
        patterns, identify constraints they didn't mention.
        Delegate broad exploration to an `Explore` subagent on Haiku.

Step 3: Systematic interrogation. For each topic area:
  - Ask ONE question at a time — never dump a batch
  - Provide a recommended answer with each question
  - Resolve dependencies first (nail down A before asking about B)
  - Challenge assumptions; play devil's advocate even on reasonable answers
  - Be specific: "How will you handle X?" beats "What about error handling?"

  Cover: problem framing, solution alternatives and what was ruled out,
  architecture fit and failure modes, explicit scope boundaries, edge cases
  and rollback, validation and success metrics, sequencing and blockers.

Step 4: Synthesize — shared understanding, decisions and rationale,
        remaining risks, next steps. Offer to write it to
        `dev/active/[topic]/plan.md`.

Rules:
- Always recommend; never just ask "What do you think?"
- Read the code before asking
- Know when to stop — consistent, specific, confident answers means done
```

**Why this pairs with `/fix-issue`:** `validate-acceptance-criteria.sh` scores an issue and warns when it's underspecified. `/grill-me` is how you fix that upstream, so the issue arrives already specified. Feeding a 5/5 issue into `/fix-issue` is dramatically cheaper than discovering the ambiguity mid-implementation.

3. Skills System

Skill File Guidelines

- **Keep skills under 500 lines** (Anthropic recommendation)
- For complex topics, use progressive disclosure: one main file (overview + navigation) plus resource files for specific subtopics
- Each resource file should also stay under 500 lines

Skill File Format

Each skill uses Anthropic's frontmatter format:

---
description: Brief description for matching
globs:
  - "src/db/**/*.ts"
alwaysApply: false
---

# Skill Name

## Overview
When to use this skill.

## Key Patterns
Code examples and conventions.

## Commands
Relevant CLI commands.

## Resources
Links to detailed docs.

Skill Categories

Technical skills (.claude/skills/technical/):
- Framework-specific patterns (Next.js, React, etc.)
- ORM patterns (Drizzle, Prisma, etc.)
- Component library usage
- Testing patterns
- API development

Runbooks (.claude/skills/runbooks/):
- How to add a new component
- How to modify database schema
- How to add environment variables
- How to run tests
- How to deploy

References (.claude/skills/reference/):
- Architecture documentation
- API references
- Testing guidelines
- Integration guides

### Cross-Tool Skill Compatibility

Skills follow the [Agent Skills standard](https://developers.openai.com/codex/skills/), so the same directory serves multiple assistants. Symlink rather than duplicate:

```text
.claude/skills/     # Primary
.codex/skills/      # Symlink → .claude/skills/
.gemini/skills/     # Reads .claude/skills/
```

| Tool | Instructions File | Skills Directory |
|------|-------------------|------------------|
| Claude Code | `CLAUDE.md` | `.claude/skills/` |
| OpenAI Codex CLI | `AGENTS.md` | `.codex/skills/` |
| Google Gemini CLI | `GEMINI.md` | `.gemini/skills/` |
| GitHub Copilot | `.github/copilot-instructions.md` | N/A |

Keep `CLAUDE.md` as the single source of truth and derive the others from it. Duplicated instruction files drift, and drift between assistants is worse than having one assistant.

### Progressive Disclosure (Three Levels)

Skills load in tiers, which is why the 500-line guidance matters:

- **Level 1** — name + description, always in context (~100 words each)
- **Level 2** — full skill body, loaded when activated
- **Level 3** — referenced documentation, loaded on demand

Every skill you add taxes Level 1 for every session, whether it activates or not. Write descriptions that discriminate, and push detail down to Level 3.

### File Triggers vs. Prompt Triggers

`skill-rules.json` supports both, and they have different timing:

- `promptTriggers` (keywords, `intentPatterns`) — fire on `UserPromptSubmit`, i.e. *before* work starts
- `fileTriggers` (`pathPatterns`, `pathExclusions`) — describe which files the skill governs

The gap: a file trigger matched by the `UserPromptSubmit` hook can only fire on the *next* prompt, so a file written this turn escapes it. That's exactly the gap `instrumentation-nudge.sh` closes by reading the same `pathPatterns` from a `PostToolUse` hook. Declaring paths once in `skill-rules.json` and consuming them from both hooks keeps one source of truth.

### Guardrail Skills

Skills can also enforce critical invariants. In `skill-rules.json`, use:

```json
{
  "blueprint-versioning": {
    "type": "guardrail",
    "enforcement": "warn",
    "priority": "critical",
    "file": ".claude/skills/reference/blueprint-versioning.md",
    "description": "Blueprint files require version bumps on modification",
    "promptTriggers": {
      "keywords": ["blueprint", "schema version"],
      "intentPatterns": ["modify.*blueprint", "update.*schema"]
    }
  }
}
```

**Enforcement levels:**
- `"enforcement": "warn"` — Hook outputs a warning but does not block. Used for guardrails (critical invariants that need human awareness).
- `"enforcement": "suggest"` — Hook outputs a suggestion. Used for optional best practices.

**Skill types in skill-rules.json:**
- `"type": "domain"` — Domain knowledge (frameworks, ORMs, etc.)
- `"type": "runbook"` — Step-by-step procedures
- `"type": "guardrail"` — Critical invariants that must not be violated

4. Hooks Configuration

### Cost guidance

Any hook or status-line script that invokes a Claude model must pin to Haiku. Hooks run frequently — on every prompt, every tool use, every Stop — so defaulting to inherited Opus is a quiet, recurring cost. Pinning to Haiku is ~1/15 the input cost with negligible quality impact for classification, keyword matching, or one-shot summarization tasks. If a hook genuinely needs Opus-level reasoning, that's a sign the work belongs in the main session or an `Explore` subagent, not a hook.

**The strongest version of this rule is that hooks call no model at all.** Keyword matching, path globbing, and signature detection are all shell and `jq` work. Keep them there. Verify with a grep you can run in CI:

```bash
grep -rn -E '(anthropic|@anthropic-ai|claude-(opus|sonnet|haiku)|model[[:space:]]*[:=][[:space:]]*["'"'"']?(opus|sonnet|haiku))' .claude/hooks/ --exclude=README.md
# expected: zero hits
```

The pattern catches full model IDs (`claude-opus-5`), package names (`@anthropic-ai/sdk`), and shorthand aliases (`model: "opus"`). `--exclude=README.md` skips the doc that legitimately names those strings while describing the rule. If you do add a model-calling hook, set the Haiku model ID explicitly — never rely on the inherited default.

settings.local.json

```json
{
  "permissions": {
    "allow": [
      "Bash(pnpm dev:*)",
      "Bash(pnpm test:*)",
      "Bash(pnpm check)",
      "Bash(pnpm install)",
      "Bash(pnpm lint:*)",
      "Bash(gh issue view:*)",
      "Bash(gh issue list:*)",
      "Bash(gh pr create:*)",
      "Bash(gh pr view:*)",
      "Bash(git checkout:*)",
      "Bash(git branch:*)",
      "Bash(git log:*)",
      "Bash(git diff:*)",
      "Bash(git status)",
      "Bash(git stash:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git push:*)"
    ]
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation-prompt.sh",
            "statusMessage": "Checking relevant skills..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/validate-acceptance-criteria.sh",
            "statusMessage": "Scoring issue readiness..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/domain-guardrail.sh",
            "statusMessage": "Checking domain patterns..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/repeat-error-detector.sh",
            "statusMessage": "Checking error patterns..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/preflight-context.sh",
            "statusMessage": "Pre-loading context..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/file-edit-tracker.sh",
            "statusMessage": "Tracking file changes..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-tool-use-tracker.sh",
            "statusMessage": "Tracking tool usage..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/instrumentation-nudge.sh",
            "statusMessage": "Checking for instrumentation triggers..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/review-nudge.sh",
            "statusMessage": "Checking for review trigger..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/auth-expired-nudge.sh",
            "statusMessage": "Checking for expired auth session..."
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if [[ \"$TOOL_INPUT\" =~ \\.(ts|tsx|js|jsx)$ ]]; then npx prettier --write \"$(echo $TOOL_INPUT | jq -r '.file_path')\" 2>/dev/null; fi",
            "statusMessage": "Formatting..."
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/build-checker.sh",
            "statusMessage": "Running build check..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/test-reminder.sh",
            "statusMessage": "Checking test coverage..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/derived-file-drift-checker.sh",
            "statusMessage": "Checking derived file drift..."
          },
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/test-gate-by-category.sh",
            "statusMessage": "Checking integration test requirements..."
          }
        ]
      }
    ]
  }
}
```

### Hook Descriptions

#### Existing Hooks (from original setup)

**skill-activation-prompt.ts** — A TypeScript hook that:
1. Reads prompt from stdin (JSON with prompt field)
2. Loads skill rules from skill-rules.json
3. Matches keywords and regex patterns against the prompt
4. Groups matches by priority (critical/high/medium/low)
5. Outputs formatted skill suggestions with file paths
6. Tells Claude to "Read referenced files before responding"

**file-edit-tracker.sh** — A bash script that:
1. Reads tool info from stdin (JSON with tool_name, tool_input.file_path)
2. Logs edits to a JSON file with timestamp, file path, operation type
3. Used by build-checker and test-reminder hooks

**post-tool-use-tracker.sh** — A bash script that:
1. Runs alongside file-edit-tracker on PostToolUse
2. Tracks all tool usage (not just file edits) for session analytics
3. Logs tool name, arguments, and timestamp

**build-checker.sh** — A bash script that:
1. Reads the edit log on Stop
2. Checks if TypeScript files were edited
3. Runs pnpm check (or your build command)
4. Displays errors or success message
5. Clears edit log on success

**test-reminder.sh** — A bash script that:
1. Reads the edit log on Stop
2. Checks if service/API files were edited
3. Suggests corresponding test files
4. Links to testing guidelines

#### Additional Hooks

**validate-acceptance-criteria.sh** (UserPromptSubmit)

Scores GitHub issues on readiness before `/fix-issue` proceeds. Checks for:
- Acceptance criteria present and specific
- Scope is well-defined (not "improve everything")
- Test requirements mentioned
- Key files or components identified
- Checklist or task breakdown included

Output: A readiness score (e.g., 3/5). If below threshold, warns Claude that the issue is underspecified and suggests asking the user for clarification before proceeding.

```bash
#!/bin/bash
# Read prompt from stdin
PROMPT=$(cat | jq -r '.prompt // empty')

# Only run when /fix-issue is detected
if [[ "$PROMPT" =~ /fix-issue ]]; then
  ISSUE_NUM=$(echo "$PROMPT" | grep -oE '[0-9]+')
  if [ -n "$ISSUE_NUM" ]; then
    BODY=$(gh issue view "$ISSUE_NUM" --json body -q '.body' 2>/dev/null)
    SCORE=0
    [[ "$BODY" =~ [Aa]cceptance ]] && ((SCORE++))
    [[ "$BODY" =~ [Tt]est ]] && ((SCORE++))
    [[ "$BODY" =~ "- [" ]] && ((SCORE++))  # Has checklist
    [[ "$BODY" =~ [Ff]ile|[Cc]omponent ]] && ((SCORE++))
    [[ ${#BODY} -gt 200 ]] && ((SCORE++))  # Sufficient detail

    if [ "$SCORE" -lt 3 ]; then
      echo "WARNING: Issue #$ISSUE_NUM scores $SCORE/5 on readiness."
      echo "Missing areas may include: acceptance criteria, test requirements, file references, or task breakdown."
      echo "Consider asking the user to flesh out the issue before proceeding."
    fi
  fi
fi
```

**domain-guardrail.sh** (UserPromptSubmit)

A project-specific pattern reminder. When certain keywords are detected in the prompt, reminds Claude about domain invariants. For example, if your project has dual execution paths for the same business logic, detecting the relevant keywords can remind Claude that a change may need to be applied in both.

Generalize this as a keyword-to-reminder mapping:

```bash
#!/bin/bash
PROMPT=$(cat | jq -r '.prompt // empty')
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Define your domain guardrails as keyword → reminder pairs
# Customize these for your project
if [[ "$PROMPT_LOWER" =~ agent|mcp|tool.?use ]]; then
  echo "REMINDER: This project has dual execution paths (server actions + MCP handlers)."
  echo "Changes to business logic may need to be applied in both paths."
fi

if [[ "$PROMPT_LOWER" =~ api|endpoint|route ]]; then
  echo "REMINDER: API changes require updating the OpenAPI spec and client types."
fi
```

**repeat-error-detector.sh** (UserPromptSubmit)

Tracks error patterns across a session. After 3 occurrences of the same normalized error, warns Claude to step back and analyze the root cause instead of retrying.

```bash
#!/bin/bash
PROMPT=$(cat | jq -r '.prompt // empty')
ERROR_LOG="/tmp/claude-error-patterns-$$"

# Normalize: strip line numbers, hashes, timestamps
NORMALIZED=$(echo "$PROMPT" | sed 's/:[0-9]*//g; s/0x[0-9a-f]*//g; s/[0-9]\{10,\}//g')
HASH=$(echo "$NORMALIZED" | md5sum | cut -d' ' -f1)

# Count occurrences
echo "$HASH" >> "$ERROR_LOG"
COUNT=$(grep -c "$HASH" "$ERROR_LOG" 2>/dev/null)

if [ "$COUNT" -ge 3 ]; then
  echo "WARNING: This error pattern has appeared $COUNT times this session."
  echo "Stop retrying the same approach. Step back and analyze the root cause."
  echo "Consider: Is this a configuration issue? A missing dependency? A wrong assumption?"
fi
```

**preflight-context.sh** (UserPromptSubmit)

Keyword-to-file mapping that pre-loads relevant files, recent git commits, and related GitHub issues when implementation prompts are detected.

```bash
#!/bin/bash
PROMPT=$(cat | jq -r '.prompt // empty')
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')
OUTPUT=""

# Keyword-to-file mapping (customize for your project)
declare -A CONTEXT_FILES
CONTEXT_FILES[database]="src/db/schema.ts src/db/migrations/"
CONTEXT_FILES[auth]="src/lib/auth.ts src/middleware.ts"
CONTEXT_FILES[api]="src/app/api/ src/lib/api-client.ts"

for keyword in "${!CONTEXT_FILES[@]}"; do
  if [[ "$PROMPT_LOWER" =~ $keyword ]]; then
    OUTPUT+="Relevant files for '$keyword': ${CONTEXT_FILES[$keyword]}\n"
  fi
done

# Recent git context for implementation prompts
if [[ "$PROMPT_LOWER" =~ implement|add|create|build|fix ]]; then
  RECENT=$(git log --oneline -5 2>/dev/null)
  if [ -n "$RECENT" ]; then
    OUTPUT+="Recent commits:\n$RECENT\n"
  fi
fi

if [ -n "$OUTPUT" ]; then
  echo -e "CONTEXT PRE-LOAD:\n$OUTPUT"
  echo "Read the listed files before starting implementation."
fi
```

**derived-file-drift-checker.sh** (Stop)

Checks if documentation or source files were modified without updating dependent/derived files. Generalized as a "derived-file drift checker" pattern.

```bash
#!/bin/bash
EDIT_LOG="$CLAUDE_PROJECT_DIR/.claude/edit-log.json"
[ ! -f "$EDIT_LOG" ] && exit 0

# Define source → derived file relationships (customize for your project)
# Format: "source-pattern:derived-file"
RELATIONSHIPS=(
  "llms.txt:llms-full.txt"
  "src/db/schema.ts:src/db/types.ts"
  "openapi.yaml:src/lib/api-client.ts"
)

EDITED_FILES=$(jq -r '.[].file' "$EDIT_LOG" 2>/dev/null)

for rel in "${RELATIONSHIPS[@]}"; do
  SOURCE="${rel%%:*}"
  DERIVED="${rel##*:}"
  if echo "$EDITED_FILES" | grep -q "$SOURCE"; then
    if ! echo "$EDITED_FILES" | grep -q "$DERIVED"; then
      echo "WARNING: $SOURCE was modified but $DERIVED was not updated."
      echo "These files should stay in sync. Please verify."
    fi
  fi
done
```

**test-gate-by-category.sh** (Stop)

Reminds about integration tests when specific file categories are modified. Generalized as a "test gate by file category" pattern.

```bash
#!/bin/bash
EDIT_LOG="$CLAUDE_PROJECT_DIR/.claude/edit-log.json"
[ ! -f "$EDIT_LOG" ] && exit 0

EDITED_FILES=$(jq -r '.[].file' "$EDIT_LOG" 2>/dev/null)

# Define file categories and their required test types (customize)
if echo "$EDITED_FILES" | grep -qE 'src/(mcp|integrations)/'; then
  echo "REMINDER: MCP/integration files were modified."
  echo "Run live integration tests before merging: pnpm test:integration"
fi

if echo "$EDITED_FILES" | grep -qE 'src/db/(schema|migrations)/'; then
  echo "REMINDER: Database files were modified."
  echo "Run migration tests: pnpm test:db"
fi

if echo "$EDITED_FILES" | grep -qE 'src/app/api/'; then
  echo "REMINDER: API routes were modified."
  echo "Run API tests: pnpm test:api"
fi
```

#### Reacting to Tool Output, Not Just Prompts

The hooks above all fire on prompts or on `Stop`. A `PostToolUse` hook with `matcher: "Bash"` can do something the others can't: **read the tool's output and react to a failure signal at the moment it happens.** This is the highest-value hook shape, because it catches problems mid-task rather than one prompt too late.

Three patterns worth copying:

**instrumentation-nudge.sh** (PostToolUse, `Edit|MultiEdit|Write`)

Skill activation on `UserPromptSubmit` can only fire on the *next* prompt — so a feature file written this turn ships uninstrumented. This hook closes that gap: when an edited file matches a skill's `fileTriggers.pathPatterns` in `skill-rules.json`, it prints a one-line reminder to add the instrumentation that skill prescribes (tracing spans, analytics events) **in the same turn the file is written**.

It calls no model — it matches the path against the same `pathPatterns` the skill system already declares, so there's one source of truth. Fail-soft: missing `jq`, malformed JSON, or a missing rules file all exit 0 rather than blocking the edit. Diagnostics go to stderr; only the nudge goes to stdout.

**review-nudge.sh** (PostToolUse, `Bash`)

After `gh pr create`, `gh pr edit`, or `git push` completes, remind the agent to run the descriptive impact reviewer and post the readout.

Implementation detail that matters: match **each command segment's leading tokens**, not a whole-string substring. Otherwise `cd x && ...`, env prefixes, and heredoc bodies produce false positives whenever a trigger word appears mid-line inside quoted text. For `git push`, resolve the current branch's open PR and no-op silently when there isn't one.

**auth-expired-nudge.sh** (PostToolUse, `Bash`)

When a command's output shows an expired cloud auth session, tell the agent to re-authenticate **itself** rather than handing the command back to the user.

The design points here generalize well:

1. **Match the tool *response*, not the command.** One expiry surfaced through four different CLIs (`aws`, `kubectl`, `helm`, `eksctl`) catches once, without enumerating commands.
2. **Skip the remedy's own output**, so the hook can't recurse or fire on a successful re-login that echoes prior error text.
3. **Separate definitive from ambiguous signatures.** `kubectl`'s `exec: executable aws failed` fires for *any* exec-plugin fault — expired token, wrong profile, missing binary. On ambiguous signals, hedge the wording and point at a disambiguating command instead of asserting expiry and sending the agent to re-login when the real fault is elsewhere.

All three call no model, print to stdout, never block, and exit 0 on every path.

#### Test the Non-Trivial Hooks

Hooks with real parsing logic — command-segment tokenization, glob-to-regex conversion, signature classification — deserve tests. Keep them in `.claude/hooks/__tests__/*.test.sh` and run with plain `bash`:

```bash
bash .claude/hooks/__tests__/review-nudge.test.sh
```

This is what makes the false-positive fixes above safe to keep refining. A hook without tests silently rots into either noise or silence.

### skill-rules.json

```json
{
  "version": "1.0",
  "skills": {
    "drizzle-orm": {
      "type": "domain",
      "priority": "high",
      "enforcement": "suggest",
      "file": ".claude/skills/technical/drizzle-orm.md",
      "description": "Database patterns with Drizzle ORM",
      "promptTriggers": {
        "keywords": ["database", "schema", "drizzle", "migration", "table"],
        "intentPatterns": ["add.*column", "create.*table", "modify.*schema"]
      }
    },
    "modify-db-model": {
      "type": "runbook",
      "priority": "critical",
      "enforcement": "suggest",
      "file": ".claude/skills/runbooks/modify-db-model.md",
      "description": "Steps for modifying database models",
      "promptTriggers": {
        "keywords": ["add column", "new table", "modify schema"],
        "intentPatterns": ["change.*database", "update.*model"]
      }
    },
    "blueprint-versioning": {
      "type": "guardrail",
      "priority": "critical",
      "enforcement": "warn",
      "file": ".claude/skills/reference/blueprint-versioning.md",
      "description": "Blueprint files require version bumps on modification",
      "promptTriggers": {
        "keywords": ["blueprint", "schema version"],
        "intentPatterns": ["modify.*blueprint", "update.*schema"]
      }
    }
  }
}
```

5. Dev Docs System

Create context persistence for multi-session tasks:

webapp/dev/
├── active/           # Currently in-progress (gitignored)
│   └── [task-name]/
│       ├── plan.md       # Implementation plan
│       ├── context.md    # Current state, key files, next steps
│       └── tasks.md      # Checklist with status
├── completed/        # Archived tasks (gitignored)
└── templates/        # Templates (tracked in git)

6. CLAUDE.md Integration

CLAUDE.md Guidelines

- **Keep CLAUDE.md minimal (~200 lines)** — move detailed guidelines to skills
- Include only: quick commands, service config, task workflow basics
- Point to skills for detailed patterns and procedures

Add to your CLAUDE.md:

### Skill Auto-Activation System

The project includes automatic skill activation based on context.

**How it works:**
1. When you submit a prompt, the `skill-activation-prompt` hook analyzes it
2. It matches keywords and patterns against skill definitions
3. Matching skills are displayed with priority levels
4. The hook tracks file edits for context persistence

**Skill types:**
- Technical skills: Framework patterns, best practices
- Runbooks: Step-by-step procedures
- References: Architecture documentation
- Guardrails: Critical invariants (enforcement: "warn")

**Setup:**
```bash
cd .claude/hooks
npm install   # Install tsx dependency
```

### PR Template Enforcement

`gh pr create --body` overrides GitHub's automatic template population. When creating PRs:
1. Always read `.github/pull_request_template.md` first
2. Fill in every section from git context
3. Pass the filled template as the `--body` argument

Add this to CLAUDE.md:
```
## PR Creation
When creating pull requests, ALWAYS read .github/pull_request_template.md and
reproduce its sections in the --body argument. Do not rely on GitHub auto-filling
the template — `gh pr create --body` overrides it.
```

### Permissions Allow-List

Pre-approve common safe commands so Claude doesn't prompt for every git/build operation. Add to settings.local.json `permissions.allow`:

```
Bash(pnpm dev:*)
Bash(pnpm test:*)
Bash(pnpm check)
Bash(pnpm install)
Bash(pnpm lint:*)
Bash(gh issue view:*)
Bash(gh issue list:*)
Bash(gh pr create:*)
Bash(gh pr view:*)
Bash(git checkout:*)
Bash(git branch:*)
Bash(git log:*)
Bash(git diff:*)
Bash(git status)
Bash(git stash:*)
Bash(git add:*)
Bash(git commit:*)
Bash(git push:*)
```

Worth adding once you have review loops and sticky comments:

```text
Bash(gh pr edit:*)
Bash(gh pr comment:*)
Bash(gh issue comment:*)
Bash(gh api repos/*/issues/*comments:*)
Bash($CLAUDE_PROJECT_DIR/.claude/hooks/pr-impact-sticky-comment.sh:*)
Bash($CLAUDE_PROJECT_DIR/.claude/hooks/codex-safe.sh exec:*)
```

Note the last two: allow-list the **wrapper script**, not the underlying CLI. That way the guards in Section 8 can't be bypassed by a call site that skips the wrapper.

### Dev Docs System

For multi-session tasks, create a task folder:
1. webapp/dev/active/[task-name]/
2. Update context.md frequently with current state
3. When resuming, read dev docs to restore context

7. Context Window Management

**Critical operational knowledge:** Your 200k context window can effectively shrink to ~70k with too many tools enabled. Performance degrades significantly.

### MCPs vs CLIs

**Prefer CLIs over MCPs in most cases.** MCPs add tool definitions that consume context even when unused.

- **GitHub:** Use `gh` CLI instead of GitHub MCP
- **Databases:** Use CLI tools or direct queries instead of database MCPs
- **Deployment:** Use `vercel`, `railway`, `fly` CLIs instead of MCPs

**When MCPs make sense:**
- Browser automation (no CLI equivalent)
- Services with complex auth that MCPs handle well
- Workflows where the MCP provides significant value over CLI

### MCP Guidelines

- **Rule of thumb:** Keep under 10 MCPs enabled / under 80 tools active
- Configure many MCPs at user level, but disable most per-project
- Use `disabledMcpServers` in `~/.claude.json` under `projects.[path]`:

```json
{
  "projects": {
    "/path/to/project": {
      "disabledMcpServers": [
        "playwright",
        "cloudflare-workers-builds",
        "some-heavy-mcp"
      ]
    }
  }
}
```

### Monitoring Context Usage

- Watch the context % in your statusline
- Use `/compact` to manually trigger compaction when needed
- If context usage seems high, audit enabled MCPs with `/plugins`

8. Automated Review Loops (Subagents)

Subagents are delegated processes with limited scope that free up context for the main agent.

### When Subagents Make Sense

**Good candidates for subagents:**
- Plan review (isolated analysis of implementation plan)
- Code review (quality, style, correctness)
- Security review (vulnerability analysis)
- Linting and formatting (self-contained)
- Test running (execute and report)
- Documentation updates (scoped changes)

**Keep in main agent:**
- Feature implementation (needs full context)
- Debugging (needs to understand system)
- Architecture decisions (needs holistic view)

### Automated Plan/Code Review Loops

The key pattern: after planning or coding, launch a subagent to review. Repeat until no material findings remain (or hit a max iteration count).

**Plan review loop (Step 6b of /fix-issue):**
```
ROUND=1
while ROUND <= 10:
  Launch subagent with prompt:
    "Review this implementation plan for completeness, correctness,
     and alignment with the issue requirements.
     Respond with MATERIAL_FINDINGS: true/false
     followed by your findings."

  Read subagent response
  Update context.md with round number and findings

  if MATERIAL_FINDINGS: false → break
  else → address findings, increment ROUND
```

**Code review loop (Step 7b of /fix-issue):**
```
ROUND=1
while ROUND <= 10:
  Launch subagent with prompt:
    "Review this code for bugs, style violations, missing tests,
     and alignment with the plan. Check that tests pass.
     Respond with MATERIAL_FINDINGS: true/false
     followed by your findings."

  Read subagent response
  Update context.md with round number and findings

  if MATERIAL_FINDINGS: false → break
  else → fix issues, increment ROUND
```

### Subagent Structure

**Commit subagents to the repo, not the laptop.** Put them in `.claude/agents/` rather than `~/.claude/agents/`. A reviewer that encodes your project's invariants — which paths are high-risk, which schemas drift, which directories are generated noise — is project knowledge. It should be versioned, code-reviewed, and travel with a clone (and with a worktree, since the `wt` function copies `.claude/`).

```
.claude/agents/
  plan-reviewer.md         # Gating: reviews the plan (MATERIAL_FINDINGS)
  code-reviewer.md         # Gating: quality and correctness (MATERIAL_FINDINGS)
  pr-impact-reviewer.md    # Descriptive: blast-radius readout (never gates)
  ui-tester.md             # Browser-driven UI verification
```

Each is a markdown file with frontmatter:

```markdown
---
name: pr-impact-reviewer
description: When to invoke this agent, and explicitly what it does NOT do.
model: opus
color: cyan
---

[System prompt: role, input contract, process, output format, degrade path]
```

### Gating vs. Descriptive Reviewers

Not every reviewer should be able to block. Splitting these is the pattern most worth stealing:

| Aspect | Gating | Descriptive |
| --- | --- | --- |
| Examples | `plan-reviewer`, `code-reviewer` | `pr-impact-reviewer` |
| Emits `MATERIAL_FINDINGS` | Yes | **Never** |
| Can block the loop | Yes | No |
| Consumer | The convergence loop | A human reading the PR |
| On failure | Surfaces the problem | Degrades to a note, loop continues |

A descriptive reviewer answers "how scary is this change?" — a question with no pass/fail answer, so wiring it into a gate produces either noise or false confidence. Keeping it purely descriptive means it can be opinionated and blunt without ever wedging the pipeline.

**Impact readout format** — the reviewer *returns* this text; the orchestration layer posts it:

```markdown
<!-- pr-impact-review -->
## PR Impact & Risk Readout

**Risk:** <one verbatim label>

### What changed and why it matters
<2–5 sentences, plain English, aimed at a teammate who did not write the code.
What the change does and what part of the system it touches — not a diff recap.>

### What to double-check
- <bullet>
```

The leading HTML marker is load-bearing: a small helper script (`gh api ... PATCH -F body=@file`) finds the comment by marker and edits it in place, so re-runs update one sticky comment instead of spamming the PR.

Pick the risk label by **reasoning about blast radius**, not by scoring a checklist: what breaks if this is wrong, who is affected, how reversible is it. Higher-risk signals to weigh — schema changes and migrations, auth and session paths, tool input/output schemas, billing, infra and deploy config, multi-tenant isolation. Lower-risk — docs, comments, tests, isolated additive UI.

One more thing worth copying: give the labels personality so they actually land. A blunt, slightly irreverent label set — escalating from a shrug at the low end to something that names the consequence of not reviewing at the high end — gets read where `Risk: Medium` gets scrolled past. Whatever wording you pick, define the labels as a fixed set of **exact strings** so downstream tooling can match on them.

### Two-Stage Delegation (Haiku reads, Opus judges)

For any reviewer that must consume a large diff, split the work by model. Reading is cheap high-volume token work; judgment is the expensive part.

1. **Stage 1 (Haiku):** the Opus agent gathers raw material (`gh pr view --json files,additions,deletions`, `gh pr diff`), then spawns an `Explore` subagent pinned to `haiku` and hands it the diff text. Haiku returns a compact structured summary — per changed area: which files, what kind of change, any risk signals it noticed.
2. **Stage 2 (Opus):** consumes Haiku's summary plus the file list and writes the judgment.

Skip Stage 1 when the diff is small enough that a subagent adds no value — but delegating the read is the default.

For very large diffs, fetch per-file via `gh api repos/<owner>/<repo>/pulls/<number>/files` rather than one giant `gh pr diff`.

### Scope Hygiene: Tell Subagents What to Ignore

Every reviewer prompt should carry an explicit ignore list, and should pass it down to any subagent it spawns. Without one, agents crawl generated trees and burn tokens producing nothing:

```text
node_modules/, .git/, .next/, .turbo/, dist/, build/
<generated docs output>/
<generated types>/
<migration snapshot JSON>
dev/active/, dev/completed/       # dev-docs scratchpad
coverage/, test-results/, playwright-report/
*.lock, pnpm-lock.yaml, package-lock.json, yarn.lock
```

A diff may legitimately touch generated files (a migration, for instance) — note that in the summary, but don't crawl the surrounding tree.

### Degrade Paths

Every optional reviewer needs an explicit degrade path in its prompt. Spell out that on any failure — model error, empty diff, unresolvable PR number — it must **return** a labeled note rather than throw:

```markdown
<!-- pr-impact-review -->
## PR Impact & Risk Readout

_Impact review unavailable: <one-line reason>._
```

Without this instruction, a transient failure in an optional step takes down a loop that had no dependency on it.

### Wrapping External CLI Agents

If a review loop calls a non-Claude CLI (Codex, Gemini) as a second opinion, wrap it in a single guard script instead of repeating flags at each call site. Every call site that has to remember a guard eventually forgets one. A wrapper like `codex-safe.sh` should enforce three:

1. **Strip credentials** — `env -u` each secret before exec'ing the CLI.
2. **Close stdin** (`</dev/null`) when stdin is a non-TTY pipe. `codex exec` appends piped stdin to the positional prompt; inside a Claude Code subagent the shell's stdin is an open pipe that never reaches EOF, so it blocks forever waiting on input that never arrives. The failure mode is silent — a long hang producing zero output, which looks like a slow review rather than a wedged one. Leave an interactive TTY alone, and provide an env var to opt back in for callers that genuinely pipe input.
3. **Bound wall-clock time.** macOS ships neither `timeout` nor `gtimeout`, so a `timeout ...` guard written into an agent definition is **inert** — the hang it was meant to bound isn't. Use perl's `alarm`, which is always present, and kill the whole process group so a wedged child can't outlive the parent.

Exit codes should follow shell convention so callers can distinguish outcomes: `124` for timeout, `128+signal` for signal death (**not** reported as success), otherwise the CLI's own code.

Add the wrapper to the permissions allow-list rather than the raw CLI:

```text
Bash($CLAUDE_PROJECT_DIR/.claude/hooks/codex-safe.sh exec:*)
```

### Subagent Design Principles

1. **Limit tools** - Give subagents only the tools they need
2. **Limit MCPs** - Subagents should have minimal/no MCPs
3. **Clear scope** - Define exactly what the subagent should do, and explicitly what it must NOT do
4. **Return format** - Specify how results should be reported back
5. **Convergence** - Use the `MATERIAL_FINDINGS: true/false` pattern to know when to stop
6. **Read-only by default** - State plainly that the agent returns text and does not write files or post comments; orchestration handles side effects
7. **Degrade, never crash** - Optional reviewers return a labeled note on failure
8. **Delegate the reading** - Pin bulk diff/file reading to Haiku; reserve Opus for judgment
9. **Commit them** - `.claude/agents/`, versioned with the code they review

### Implementation Notes

1. **Hooks need tsx** - Install with `npm install tsx @types/node` in `.claude/hooks/`

2. **Shell scripts need execute permission** - Run `chmod +x .claude/hooks/*.sh`

3. **Skill rules file** - Create `skill-rules.json` with your project's keywords

4. **Customize for your stack** - Replace framework names, file patterns, and commands

5. **Gitignore** - Add `webapp/dev/active/` and `webapp/dev/completed/` to `.gitignore`

6. **Commit `.claude/agents/`** - Subagents encode project invariants; version them with the code

7. **Test the parsing hooks** - Any hook doing tokenization or glob conversion gets a `__tests__/*.test.sh`

8. **Verify no hook calls a model** - Run the grep from the Cost guidance section in CI

---

This setup provides:
- **Consistency** - Same patterns and commands every session
- **Context persistence** - Dev docs survive session restarts
- **Quality gates** - Build checks, test reminders, and review loops
- **Discoverability** - Skills surface relevant docs automatically
- **Context efficiency** - MCPs managed, subagents for isolated tasks
- **Guardrails** - Domain-specific invariants enforced via hooks and skills
- **Session resilience** - Resume from checkpoints, error pattern detection
- **Failure-signal self-healing** - Hooks that read tool output and fix auth/instrumentation gaps in-turn
- **Human-readable risk** - Descriptive impact readouts that inform without gating

---

**Note:** For one-time laptop setup (git worktrees, custom status line, usage monitoring, keyboard shortcuts), see `laptop-setup.md`.
