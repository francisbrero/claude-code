# The Shorthand Guide to Everything Claude Code

**Source:** https://x.com/affaanmustafa/status/2012378465664745795
**Author:** @affaanmustafa (cogsec)
**Experience:** 10 months of daily Claude Code use, won Anthropic x Forum Ventures hackathon

## Key Concepts

### Skills vs Commands
- **Skills** (`~/.claude/skills/`): Broader workflow definitions, rules constricted to scopes
- **Commands** (`~/.claude/commands/`): Quick executable prompts via slash commands
- Skills and commands can be chained together in a single prompt
- Example skill structure:
  ```
  ~/.claude/skills/
    pmx-guidelines.md      # Project-specific patterns
    coding-standards.md    # Language best practices
    tdd-workflow/          # Multi-file skill with README.md
    security-review/       # Checklist-based skill
  ```

### Hooks (Trigger-Based Automations)
Hook types:
1. **PreToolUse** - Before a tool executes (validation, reminders)
2. **PostToolUse** - After a tool finishes (formatting, feedback loops)
3. **UserPromptSubmit** - When you send a message
4. **Stop** - When Claude finishes responding
5. **PreCompact** - Before context compaction
6. **Notification** - Permission requests

**Pro tip:** Use the `hookify` plugin to create hooks conversationally instead of writing JSON manually.

### Subagents
- Processes the orchestrator (main Claude) can delegate tasks to with limited scopes
- Can run in background or foreground, freeing up context
- Work nicely with skills - a subagent capable of executing a subset of skills can be delegated tasks
- Can be sandboxed with specific tool permissions

Suggested subagent structure:
```
~/.claude/agents/
  planner.md           # Break down features
  architect.md         # System design
  tdd-guide.md         # Write tests first
  code-reviewer.md     # Quality review
  security-reviewer.md # Vulnerability scan
  build-error-resolver.md
  e2e-runner.md        # Playwright tests
  refactor-cleaner.md  # Dead code removal
  doc-updater.md       # Keep docs synced
```

### Rules Structure
Two approaches:
1. **Single CLAUDE.md** - Everything in one file (user or project level)
2. **Rules folder** - Modular `.md` files grouped by concern

Suggested rules structure:
```
~/.claude/rules/
  security.md      # Mandatory security checks
  coding-style.md  # Immutability, file size limits
  testing.md       # TDD, 80% coverage
  git-workflow.md  # Conventional commits
  agents.md        # Subagent delegation rules
  patterns.md      # API response formats
  performance.md   # Model selection (Haiku vs Sonnet vs Opus)
  hooks.md         # Hook documentation
```

Example rules:
- No emojis in codebase
- Refrain from purple hues in frontend
- Always test code before deployment
- Prioritize modular code over mega-files
- Never commit console.logs

## CRITICAL: Context Window Management

**This is the most important operational insight:**
- Your 200k context window before compacting might only be 70k with too many tools enabled
- Performance degrades significantly with too many MCPs/plugins
- **Rule of thumb:** Have 20-30 MCPs in config, but keep under 10 enabled / under 80 tools active
- Disable per-project in `~/.claude.json` under `projects.[path].disabledMcpServers`

## Practical Hooks Configuration

```json
{
  "PreToolUse": [
    // tmux reminder for long-running commands
    { "matcher": "npm|pnpm|yarn|cargo|pytest", "hooks": ["tmux reminder"] },
    // Block unnecessary .md file creation
    { "matcher": "Write && .md file", "hooks": ["block unless README/CLAUDE"] },
    // Review before git push
    { "matcher": "git push", "hooks": ["open editor for review"] }
  ],
  "PostToolUse": [
    // Auto-format JS/TS with Prettier
    { "matcher": "Edit && .ts/.tsx/.js/.jsx", "hooks": ["prettier --write"] },
    // TypeScript check after edits
    { "matcher": "Edit && .ts/.tsx", "hooks": ["tsc --noEmit"] },
    // Warn about console.log
    { "matcher": "Edit", "hooks": ["grep console.log warning"] }
  ],
  "Stop": [
    // Audit for console.logs before session ends
    { "matcher": "*", "hooks": ["check modified files for console.log"] }
  ]
}
```

## Keyboard Shortcuts
- `Ctrl+U` - Delete entire line (faster than backspace spam)
- `!` - Quick bash command prefix
- `@` - Search for files
- `/` - Initiate slash commands
- `Shift+Enter` - Multi-line input
- `Tab` - Toggle thinking display
- `Esc Esc` - Interrupt Claude / restore code

## Parallel Workflows
- `/fork` - Fork conversations for non-overlapping parallel tasks
- **Git Worktrees** - For overlapping parallel Claudes without conflicts
  ```bash
  git worktree add ../feature-branch feature-branch
  # Now run separate Claude instances in each worktree
  ```
- **tmux** for long-running commands - stream and watch logs/bash processes

## Useful Commands
- `/rewind` - Go back to a previous state
- `/statusline` - Customize with branch, context %, todos
- `/checkpoints` - File-level undo points
- `/compact` - Manually trigger context compaction

## Plugins Ecosystem
- **LSP Plugins** are useful if running Claude Code outside editors
  - `typescript-lsp@claude-plugins-official`
  - `pyright-lsp@claude-plugins-official`
- **hookify** - Create hooks conversationally
- **mgrep@Mixedbread-Grep** - Better search than ripgrep (local + web search)
- **context7** - Live documentation

Installing plugins:
```bash
claude plugin marketplace add https://github.com/mixedbread-ai/mgrep
# Then /plugins to install
```

## MCP Server Configuration
Example user-level MCPs:
- github, firecrawl, supabase, memory, sequential-thinking
- vercel, railway (deployment)
- cloudflare-docs, cloudflare-workers-* (infrastructure)
- clickhouse (analytics)

## Editor Integration

### Zed (Author's preference)
- Agent Panel Integration for real-time file tracking
- `Ctrl + G` - quickly open file Claude is working on
- Performance (Rust-based, lightweight)
- `CMD+Shift+R` - Command palette for custom commands

### VSCode/Cursor
- Terminal format with `\ide` for LSP functionality
- Or use the extension for integrated UI

### General Editor Tips
- Split screen: Terminal with Claude Code on one side, editor on other
- Enable auto-save so Claude's file reads are always current
- Use editor's git features to review Claude's changes

## Key Takeaways (Author's Summary)
1. Don't overcomplicate - treat configuration like fine-tuning, not architecture
2. Context window is precious - disable unused MCPs and plugins
3. Parallel execution - fork conversations, use git worktrees
4. Automate the repetitive - hooks for formatting, linting, reminders
5. Scope your subagents - limited tools = focused execution

## Actionable Items for setup.md

### High Priority
1. **Context window management section** - Add guidance on MCP/plugin limits
2. **Hook examples** - tmux reminder, prettier auto-format, console.log warning
3. **Subagent patterns** - planner, architect, tdd-guide, code-reviewer, security-reviewer
4. **Rules structure** - Modular approach with security.md, coding-style.md, testing.md, etc.

### Medium Priority
1. **Keyboard shortcuts reference**
2. **Parallel workflow guidance** - /fork, git worktrees, tmux
3. **Useful commands** - /rewind, /statusline, /checkpoints, /compact
4. **Plugin recommendations** - LSP plugins, hookify, mgrep

### To Investigate
1. hookify plugin for conversational hook creation
2. mgrep as grep replacement
3. context7 for live documentation
