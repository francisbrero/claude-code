Overview

I want to set up a production-quality Claude Code configuration for my project. This should include:

1. Fix-issue command - A slash command to fetch and implement GitHub issues
2. Additional commands - PR creation, Jira conversion, instance setup
3. Skills system - Auto-activated documentation, runbooks, and technical references
4. Hooks - Skill activation, edit tracking, build checking, guardrails, and context pre-loading
5. Dev docs system - Context persistence across sessions
6. CLAUDE.md patterns - PR templates, review loops, permissions, guardrails

### Core Principle: Subagent Delegation

The dominant cost of a long Claude Code session is cache-read at Opus rates (~$1.50/MTok). At a typical 800K-token context, every broad inline grep re-reads the full cache — open-ended exploration in the main session is the most expensive shape of work you can do. The slash commands and hooks below are written around three rules:

1. **Targeted lookups stay in the main context.** When you know the file path or exact symbol, use `Read` or `Bash grep` directly.
2. **Open-ended exploration goes to an `Explore` subagent on Haiku** ("where does X live", "find callers of Y", "what implements Z"). Sidechain context is independent and Haiku is ~1/15 the input cost of Opus.
3. **Hooks that invoke a model pin to Haiku.** Hooks fire on every prompt — defaulting to inherited Opus is a quiet, recurring cost.

This is why the patterns below delegate exploration aggressively and reserve Opus for reasoning that needs the full context.

Directory Structure

Create this structure:

.claude/
├── commands/
│   ├── fix-issue.md           # /fix-issue slash command
│   ├── create-pr.md           # /create-pr slash command
│   ├── jira-to-github-issue.md # /jira-to-github-issue command
│   └── setup-instance.md      # /setup-instance command
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

#### Additional Hooks (from hip-phoenix)

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

A project-specific pattern reminder. When certain keywords are detected in the prompt, reminds Claude about domain invariants. For example, in hip-phoenix, when "agent" or "MCP" keywords are detected, it reminds about dual execution paths (server actions + MCP handlers).

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

The key pattern from hip-phoenix: after planning or coding, launch a subagent to review. Repeat until no material findings remain (or hit a max iteration count).

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

```
~/.claude/agents/
  planner.md           # Break down features into tasks
  code-reviewer.md     # Quality and style review
  security-reviewer.md # Vulnerability analysis
  tdd-guide.md         # Test-driven development
  refactor-cleaner.md  # Dead code removal
```

### Subagent Design Principles

1. **Limit tools** - Give subagents only the tools they need
2. **Limit MCPs** - Subagents should have minimal/no MCPs
3. **Clear scope** - Define exactly what the subagent should do
4. **Return format** - Specify how results should be reported back
5. **Convergence** - Use the `MATERIAL_FINDINGS: true/false` pattern to know when to stop

### Implementation Notes

1. **Hooks need tsx** - Install with `npm install tsx @types/node` in `.claude/hooks/`

2. **Shell scripts need execute permission** - Run `chmod +x .claude/hooks/*.sh`

3. **Skill rules file** - Create `skill-rules.json` with your project's keywords

4. **Customize for your stack** - Replace framework names, file patterns, and commands

5. **Gitignore** - Add `webapp/dev/active/` and `webapp/dev/completed/` to `.gitignore`

---

This setup provides:
- **Consistency** - Same patterns and commands every session
- **Context persistence** - Dev docs survive session restarts
- **Quality gates** - Build checks, test reminders, and review loops
- **Discoverability** - Skills surface relevant docs automatically
- **Context efficiency** - MCPs managed, subagents for isolated tasks
- **Guardrails** - Domain-specific invariants enforced via hooks and skills
- **Session resilience** - Resume from checkpoints, error pattern detection

---

**Note:** For one-time laptop setup (git worktrees, keyboard shortcuts), see `laptop-setup.md`.
