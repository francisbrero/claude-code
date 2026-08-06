# cc-audit

Audits a Claude Code setup for cost efficiency by reading local transcripts, and
writes a ranked markdown report of what to change first.

Built for a specific question: *given an engineer spending thousands a month,
what is the shortest list of changes that actually reduces the bill?*

## Usage

```bash
python3 cc_audit.py                 # last 30 days -> CC-AUDIT.md
python3 cc_audit.py --days 7
python3 cc_audit.py --out me.md
python3 cc_audit.py --json          # machine-readable, for aggregating across a team
```

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
