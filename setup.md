  Overview

  I want to set up a production-quality Claude Code configuration for my project. This should include:

  1. Fix-issue command - A slash command to fetch and implement GitHub issues
  2. Skills system - Auto-activated documentation, runbooks, and technical references
  3. Hooks - Automatic skill activation on prompts, file edit tracking, and build checking
  4. Dev docs system - Context persistence across sessions

  Directory Structure

  Create this structure:

  .claude/
  ├── commands/
  │   └── fix-issue.md           # /fix-issue slash command
  ├── hooks/
  │   ├── skill-activation-prompt.sh   # Shell wrapper
  │   ├── skill-activation-prompt.ts   # TypeScript skill matcher
  │   ├── file-edit-tracker.sh         # Track edited files
  │   ├── build-checker.sh             # Run build check on Stop
  │   ├── test-reminder.sh             # Remind about tests
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
  └── settings.local.json              # Hook configuration

  1. Fix-Issue Command (.claude/commands/fix-issue.md)

  Create a slash command that:
  - Fetches GitHub issue with gh issue view $ARGUMENTS
  - Creates branch based on issue labels (feature/, bugfix/, etc.)
  - Creates dev docs folder for context persistence
  - Plans implementation in phases
  - Waits for user approval before implementing
  - Runs tests and checks before finalizing — **tests must pass before marking complete**
  - Creates commit and PR when done

  The command should include:
  - Step-by-step workflow (fetch → branch → plan → implement → test → PR)
  - Template for plan.md, context.md, tasks.md
  - References to project guidelines

  2. Skills System

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

  3. Hooks Configuration

  settings.local.json

  {
    "permissions": {
      "allow": [
        "Bash(pnpm dev:*)",
        "Bash(gh issue view:*)",
        "Bash(git checkout:*)",
        "Bash(gh pr create:*)"
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
            }
          ]
        }
      ]
    }
  }

  skill-activation-prompt.ts

  A TypeScript hook that:
  1. Reads prompt from stdin (JSON with prompt field)
  2. Loads skill rules from skill-rules.json
  3. Matches keywords and regex patterns against the prompt
  4. Groups matches by priority (critical/high/medium/low)
  5. Outputs formatted skill suggestions with file paths
  6. Tells Claude to "Read referenced files before responding"

  skill-rules.json

  {
    "version": "1.0",
    "skills": {
      "drizzle-orm": {
        "type": "domain",
        "priority": "high",
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
        "file": ".claude/skills/runbooks/modify-db-model.md",
        "description": "Steps for modifying database models",
        "promptTriggers": {
          "keywords": ["add column", "new table", "modify schema"],
          "intentPatterns": ["change.*database", "update.*model"]
        }
      }
    }
  }

  file-edit-tracker.sh

  A bash script that:
  1. Reads tool info from stdin (JSON with tool_name, tool_input.file_path)
  2. Logs edits to a JSON file with timestamp, file path, operation type
  3. Used by build-checker and test-reminder hooks

  build-checker.sh

  A bash script that:
  1. Reads the edit log on Stop
  2. Checks if TypeScript files were edited
  3. Runs pnpm check (or your build command)
  4. Displays errors or success message
  5. Clears edit log on success

  test-reminder.sh

  A bash script that:
  1. Reads the edit log on Stop
  2. Checks if service/API files were edited
  3. Suggests corresponding test files
  4. Links to testing guidelines

  4. Dev Docs System

  Create context persistence for multi-session tasks:

  webapp/dev/
  ├── active/           # Currently in-progress (gitignored)
  │   └── [task-name]/
  │       ├── plan.md       # Implementation plan
  │       ├── context.md    # Current state, key files, next steps
  │       └── tasks.md      # Checklist with status
  ├── completed/        # Archived tasks (gitignored)
  └── templates/        # Templates (tracked in git)

  5. CLAUDE.md Integration

  CLAUDE.md Guidelines

  - **Keep CLAUDE.md minimal (~200 lines)** — move detailed guidelines to skills
  - Include only: quick commands, service config, task workflow basics
  - Point to skills for detailed patterns and procedures

  Add to your CLAUDE.md:

  ## Skill Auto-Activation System

  Phoenix includes automatic skill activation based on context.

  **How it works:**
  1. When you submit a prompt, the `skill-activation-prompt` hook analyzes it
  2. It matches keywords and patterns against skill definitions
  3. Matching skills are displayed with priority levels
  4. The hook tracks file edits for context persistence

  **Skill types:**
  - Technical skills: Framework patterns, best practices
  - Runbooks: Step-by-step procedures
  - References: Architecture documentation

  **Setup:**
  ```bash
  cd .claude/hooks
  npm install   # Install tsx dependency

  Dev Docs System

  For multi-session tasks, create a task folder:
  1. webapp/dev/active/[task-name]/
  2. Update context.md frequently with current state
  3. When resuming, read dev docs to restore context

  ### Implementation Notes

  1. **Hooks need tsx** - Install with `npm install tsx @types/node` in `.claude/hooks/`

  2. **Shell scripts need execute permission** - Run `chmod +x .claude/hooks/*.sh`

  3. **Skill rules file** - Create `skill-rules.json` with your project's keywords

  4. **Customize for your stack** - Replace framework names, file patterns, and commands

  5. **Gitignore** - Add `webapp/dev/active/` and `webapp/dev/completed/` to `.gitignore`

  ---

  6. Context Window Management

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

  7. Subagents (Experimental)

  Subagents are delegated processes with limited scope that free up context for the main agent. This pattern is still evolving.

  ### When Subagents Make Sense

  **Good candidates for subagents:**
  - Linting and formatting (self-contained, no broader context needed)
  - Security review (focused analysis)
  - Code review (isolated feedback)
  - Test running (execute and report)
  - Documentation updates (scoped changes)

  **Keep in main agent:**
  - Feature implementation (needs full context)
  - Debugging (needs to understand system)
  - Architecture decisions (needs holistic view)

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

  8. Parallel Workflows

  ### Forking Conversations

  Use `/fork` for non-overlapping parallel tasks instead of queuing messages.

  ### Git Worktrees

  Worktrees enable running multiple Claude instances on overlapping work without conflicts.

  **Basic worktree creation:**
  ```bash
  git worktree add ../feature-branch feature-branch
  # Run separate Claude instance in each worktree
  ```

  **Fast worktree function (recommended):**

  Since worktrees don't include gitignored files, use a shell function that:
  1. Creates the worktree with a new branch
  2. Copies all `.env` files (including in subdirectories)
  3. Copies hidden dev folders (`.claude`, `.github`, `.vscode`, `.idea`)
  4. Opens the new worktree in your editor

  Add to `~/.config/zsh/wt.zsh` (and source from `.zshrc`):

  ```zsh
  # Git Worktree Setup Function
  # Usage: wt <feature-name>
  # Creates a worktree in adjacent -worktrees folder and opens in Cursor
  wt() {
      if [ -z "$1" ]; then
          echo "Usage: wt <feature-name>"
          return 1
      fi

      local FEATURE_NAME="$1"
      local CURRENT_DIR=$(basename "$(pwd)")
      local PARENT_DIR=$(dirname "$(pwd)")
      local WORKTREES_DIR="$PARENT_DIR/${CURRENT_DIR}-worktrees"

      if ! git rev-parse --git-dir > /dev/null 2>&1; then
          echo "Error: Not in a git repository"
          return 1
      fi

      # Create worktrees directory if needed
      [ ! -d "$WORKTREES_DIR" ] && mkdir -p "$WORKTREES_DIR"

      local WORKTREE_PATH="$WORKTREES_DIR/$FEATURE_NAME"

      if [ -d "$WORKTREE_PATH" ]; then
          echo "Error: Worktree '$FEATURE_NAME' already exists"
          return 1
      fi

      # Create the git worktree with new branch
      if git worktree add -b "$FEATURE_NAME" "$WORKTREE_PATH"; then
          echo "Created worktree: $WORKTREE_PATH"

          # Copy all .env files (including subdirectories)
          while IFS= read -r -d '' env_file; do
              local rel_path="${env_file#$(pwd)/}"
              local target_dir="$WORKTREE_PATH/$(dirname "$rel_path")"
              mkdir -p "$target_dir"
              cp "$env_file" "$target_dir/"
              echo "  Copied: $rel_path"
          done < <(find "$(pwd)" -name ".env*" -type f -print0)

          # Copy hidden dev folders
          local hidden_folders=(".claude" ".github" ".vscode" ".idea")
          for folder_name in "${hidden_folders[@]}"; do
              while IFS= read -r -d '' hidden_folder; do
                  local rel_path="${hidden_folder#$(pwd)/}"
                  local target_dir="$WORKTREE_PATH/$(dirname "$rel_path")"
                  mkdir -p "$target_dir"
                  cp -r "$hidden_folder" "$target_dir/"
                  echo "  Copied: $rel_path"
              done < <(find "$(pwd)" -name "$folder_name" -type d -print0)
          done

          # Open in editor (adjust for your editor: code, cursor, zed, etc.)
          cursor -n "$WORKTREE_PATH"

          echo "Done! Branch '$FEATURE_NAME' ready at $WORKTREE_PATH"
      else
          echo "Failed to create git worktree"
          return 1
      fi
  }
  ```

  **Key features:**
  - Creates worktrees in `project-worktrees/` adjacent to your project
  - Recursively finds and copies all `.env*` files
  - Copies `.claude/` so your Claude config travels with the worktree
  - Opens directly in your editor

  ### tmux for Long-Running Commands

  Use tmux to:
  - Run dev servers that Claude can monitor
  - Keep sessions alive for long operations
  - **Access sessions remotely from phone/tablet**

  **Basic tmux workflow:**
  ```bash
  # Start named session
  tmux new -s dev

  # Claude runs commands here, you can detach (Ctrl+b d) and reattach
  tmux attach -t dev

  # View logs from specific session
  tmux attach -t frontend-logs
  ```

  **Remote access pattern:**
  1. SSH into your dev machine from phone
  2. `tmux attach -t dev` to see running session
  3. Monitor progress, intervene if needed
  4. Detach and let it continue

  **Hook for tmux reminder:**
  ```json
  {
    "PreToolUse": [
      {
        "matcher": "tool == 'Bash' && tool_input.command matches '(npm|pnpm|yarn|cargo|pytest)'",
        "hooks": [
          {
            "type": "command",
            "command": "if [ -z \"$TMUX\" ]; then echo '[Hook] Consider tmux for session persistence' >&2; fi"
          }
        ]
      }
    ]
  }
  ```

  9. Remote Session Control

  Control Claude Code sessions from your phone or other devices.

  ### Prerequisites

  - Mac with Claude Code installed
  - tmux (`brew install tmux`)
  - SSH enabled (System Settings > General > Sharing > Remote Login)
  - Mobile SSH client (Blink Shell recommended for iOS)

  ### Quick Setup (Tailscale + Mosh)

  **1. Install Tailscale on both devices**
  ```bash
  # Mac
  brew install tailscale
  # Start and authenticate
  sudo tailscale up
  ```

  **2. Install Mosh for resilient connections**
  ```bash
  brew install mosh
  ```

  **3. Enable SSH on Mac**
  - System Settings > General > Sharing > Remote Login: On
  - Add your SSH key to `~/.ssh/authorized_keys`

  **4. Connect from phone (Blink Shell)**
  ```bash
  # Mosh survives network changes
  mosh user@your-mac-tailscale-name

  # Attach to Claude session
  tmux attach -t claude
  ```

  ### Session Helper Functions

  Add to your `.zshrc`:
  ```bash
  source ~/path/to/scripts/claude-remote.zsh
  ```

  **Core commands:**
  | Command | Description |
  |---------|-------------|
  | `claude-session [name]` | Start/attach to named session |
  | `claude-bg [name]` | Start session in background |
  | `cc` | Project-based session (uses directory name) |
  | `ccbg` | Project session in background |
  | `cca` | Quick attach to any Claude session |
  | `claude-ls` | List all Claude sessions |
  | `claude-kill [name]` | Kill a session |

  **Remote control (without attaching):**
  | Command | Description |
  |---------|-------------|
  | `claude-send "prompt"` | Send prompt to running session |
  | `claude-capture [lines]` | View recent session output |

  **Unattended mode:**
  | Command | Description |
  |---------|-------------|
  | `claude-auto [name]` | Start with --dangerously-skip-permissions |
  | `claude-auto-bg [name]` | Background unattended session |

  **Typical workflow:**
  ```bash
  # On your Mac - start a session and detach
  cc                     # Start project session
  # Press Ctrl+B, D to detach

  # From phone via SSH/Mosh
  cca                    # Quick attach
  # Or send a prompt without attaching
  claude-send "Run the tests and fix any failures"
  ```

  ### Headless Mode (Programmatic)

  For automation and CI/CD, use the `-p` flag. Add helpers to `.zshrc`:
  ```bash
  source ~/path/to/scripts/claude-headless.zsh
  ```

  **Quick queries:**
  | Command | Description |
  |---------|-------------|
  | `cq "question"` | Simple text query |
  | `cqj "question"` | JSON output (with metadata) |
  | `cqs "question"` | Streaming JSON |
  | `cc-result "question"` | Extract just the result text |

  **Session continuation:**
  | Command | Description |
  |---------|-------------|
  | `cc-continue "follow up"` | Continue last conversation |
  | `cc-resume <id> "question"` | Resume specific session |
  | `session=$(cc-start "task")` | Get session ID for later |

  **Tool control:**
  | Command | Description |
  |---------|-------------|
  | `cc-readonly "analyze this"` | Read-only tools |
  | `cc-edit "refactor this"` | With edit capability |
  | `cc-full "implement this"` | All tools (careful!) |
  | `cc-with-tools "Bash,Read" "task"` | Custom tool set |

  **Pipeline helpers:**
  | Command | Description |
  |---------|-------------|
  | `cat file | cc-pipe "summarize"` | Pipe content to Claude |
  | `cc-file myfile.ts "explain"` | Process specific file |
  | `cc-diff` | Review git diff |
  | `cc-pr-desc [base]` | Generate PR description |

  **Examples:**
  ```bash
  # Quick codebase question
  cq "What does the auth module do?"

  # Code review with JSON output
  cc-review "review the payment service" | jq '.result'

  # Multi-turn session
  session=$(cc-start "Review this codebase for security issues")
  cc-resume "$session" "Focus on the API routes"
  cc-resume "$session" "Generate a report of findings"

  # PR automation
  gh pr diff 123 | cc-pipe "Review this PR for issues"
  ```

  ### Security Notes

  - Use SSH keys, never passwords
  - Tailscale provides encrypted mesh networking
  - `--dangerously-skip-permissions` should only be used in trusted environments
  - Consider limiting tool access with `--allowedTools` for automated workflows

  10. Keyboard Shortcuts Reference

  | Shortcut | Action |
  |----------|--------|
  | `Ctrl+U` | Delete entire line (faster than backspace) |
  | `!` | Quick bash command prefix |
  | `@` | Search for files |
  | `/` | Initiate slash commands |
  | `Shift+Enter` | Multi-line input |
  | `Tab` | Toggle thinking display |
  | `Esc Esc` | Interrupt Claude / restore code |

  ### Useful Commands

  | Command | Action |
  |---------|--------|
  | `/fork` | Fork conversation for parallel work |
  | `/rewind` | Go back to a previous state |
  | `/statusline` | Customize status display |
  | `/checkpoints` | File-level undo points |
  | `/compact` | Manually trigger context compaction |
  | `/plugins` | View and manage MCPs and plugins |

  ---

  This setup provides:
  - **Consistency** - Same patterns and commands every session
  - **Context persistence** - Dev docs survive session restarts
  - **Quality gates** - Build checks and test reminders
  - **Discoverability** - Skills surface relevant docs automatically
  - **Context efficiency** - MCPs managed, subagents for isolated tasks
  - **Parallel capability** - Worktrees and tmux for concurrent work