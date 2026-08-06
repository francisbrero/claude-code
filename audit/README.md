# cc-audit

Audits a Claude Code setup for cost efficiency by reading local transcripts, and
writes a ranked markdown report of what to change first.

Built for a specific question: *given an engineer spending thousands a month,
what is the shortest list of changes that actually reduces the bill?*

## Usage

```bash
python3 cc_audit.py                 # ALL repos, last 30 days -> CC-AUDIT.md
python3 cc_audit.py --days 7
python3 cc_audit.py --out me.md
python3 cc_audit.py --json          # machine-readable, for aggregating across a team
```

## Stored reports

Every run saves a dated copy under `~/.claude/cc-audit-reports/<user-id>/`, so
learnings accumulate as more people run it:

```text
~/.claude/cc-audit-reports/
  alice-b73b/
    2026-01-15.md      full report — paths, commands, session IDs
    2026-01-15.json    sanitized metrics — safe to pool
    latest.md -> 2026-01-15.md
```

The user ID is `<os-username>-<4-char machine hash>`; the hash distinguishes two
laptops without embedding a hostname. One report per user per day — re-running
overwrites that day.

**The two files exist for different audiences.** The markdown is for the person
who ran it and keeps every detail that made a finding actionable. The JSON is
what you collect centrally, and it carries **no file paths, no shell commands,
no repo names, and no free text** — summaries and fixes are dropped precisely
because they quote real paths. Pooling the JSON cannot leak anyone's work.

```bash
python3 cc_audit.py --trend              # your reports over time
python3 cc_audit.py --trend --all-users  # everyone under the report dir
python3 cc_audit.py --no-store           # don't save this run
python3 cc_audit.py --report-dir /shared/audits   # collect somewhere central
```

`--trend` also tallies which findings recur across reports, which is the point
of keeping a history: it shows whether a fix actually moved the number, and
which problems are common enough to be worth solving org-wide rather than
one engineer at a time.

To gather reports centrally, have people point `--report-dir` at a synced
folder, or collect the `*.json` files — they are designed to be concatenated:

```python
import store
rows = store.history(root="/shared/audits")   # every user, oldest first
```

## Excluding personal repos

Every repo is analysed by default. To leave personal work out of a report you're
going to share, first see what's there:

```bash
python3 cc_audit.py --list-repos
```

Then exclude by repo name, a repo-name glob, or a path:

```bash
python3 cc_audit.py --exclude side-project --exclude 'hobby-*'
python3 cc_audit.py --exclude '/Users/me/personal/*'
```

To set it once instead of retyping, create `~/.claude/cc-audit.json`:

```json
{ "exclude": ["side-project", "/Users/me/personal/*"] }
```

Config and `--exclude` flags combine; `--no-config` ignores the file for one run.

Matching rules, which are deliberately narrow to avoid dropping work by accident:

- A **bare name** matches the repo only — never an arbitrary path segment. A
  worktree can share a name with an unrelated repo (`work-repo-worktrees/website`
  vs a standalone `website`), and excluding the latter must not silently drop the
  former.
- **Worktrees follow their parent repo**, so `--exclude myrepo` also excludes
  every `myrepo-worktrees/*` checkout.
- A pattern containing a **slash** matches the working directory tree.

Exclusions are disclosed in the report and in the JSON output, so a reader can
tell the figures are partial rather than assuming they cover everything.

Python 3.9+, standard library only. No install, no dependencies, no network
access — it reads `~/.claude/projects/**/*.jsonl` and writes one file. Nothing
leaves the machine, which matters because transcripts contain source code.

## Rolling it out across a team

The tool is self-serve by design: transcripts live on each engineer's laptop, so
each person runs it themselves.

```bash
# each engineer runs:
python3 cc_audit.py --days 30 --json > "$USER-audit.json"
```

The JSON output carries totals and per-finding savings without any prompt or
code content, so it is safe to share for aggregation. The markdown report
contains directory names and session IDs — review before circulating widely.

## What it checks

| Check | What it catches |
|---|---|
| **Runaway sessions** | Sessions grown past 200K context, where every turn re-reads the entire history |
| **Premium model on retrieval** | High-input/low-output Opus calls — reading and grepping on the most expensive model |
| **Subagent delegation** | Whether read-heavy work is delegated, and whether those subagents run on cheap models |
| **Session hygiene** | Context growth between 100K and 200K, compaction events |
| **Cache hit rate** | Prefix churn — the cache being rebuilt rather than reused |
| **Cache TTL** | Paying the 2.0x 1-hour write premium when turn gaps don't justify it |
| **Worktree fragmentation** | Cold cache starts multiplied across many working directories |
| **Context bloat** | Baseline prefix size — CLAUDE.md, MCP tool schemas, system prompt |
| **Tool output waste** | Oversized tool results that stay in context and are re-read every turn |
| **Config switches** | No `~/.claude/agents/` (subagents inherit the expensive model), no-op `MAX_THINKING_TOKENS`, fallback chains, uncapped MCP output |

The report also benchmarks cost per active day against Anthropic's published
figures (~$13/developer/active day; 90% of users under $30/active day), so the
headline number is interpretable rather than merely large.

## How the cost model works

Each `assistant` record in a transcript is one billed API call carrying a
`usage` block. Costs are computed per call from published rates:

| Component | Multiplier on base input price |
|---|---|
| Cache read | 0.10x |
| Cache write, 5-minute TTL | 1.25x |
| Cache write, 1-hour TTL | 2.00x |
| Uncached input | 1.00x |

Rates live in `pricing.py` — update `FAMILY_PRICES` when Anthropic publishes new
ones and every estimate follows.

### Deduplication

Claude Code forks a transcript into a new file whenever a session is resumed or
branched, replaying earlier history into each new file. On a real machine this
meant **40,548 of 82,841 assistant records were replays** — naively summing them
overstated spend by roughly 2x.

Billing happens once per `requestId`, so that is the unit of truth: the first
occurrence of each request wins and the rest are dropped. Files sharing a
`sessionId` are merged into one session.

## Reading the numbers

Savings estimates are **directional, not invoices**. Every finding shows its
arithmetic so you can check the reasoning rather than trust the total. They are
deliberately conservative — each applies a discount factor for work that is
genuinely necessary rather than assuming all of it is waste.

Two caveats worth stating plainly:

- **Costs are API-equivalent.** If usage is covered by a subscription, the
  dollar figures represent relative cost, not an amount billed. They are still
  the right way to rank what to fix.
- **Findings are scoped to avoid double-counting**, but they are not fully
  independent — fixing runaway sessions also reduces the retrieval-on-Opus
  number, since both are consequences of oversized context. Treat the total as
  an upper bound on the combined effect, not a sum of separate wins.

## The one-line version

In practice the ranking is stable across setups: **context size dominates
everything**. A session at 800K tokens pays ~$1.20 per turn on Opus before doing
any work. Clearing at task boundaries and pushing file reading into cheap
subagents is worth more than every cache tweak combined.
