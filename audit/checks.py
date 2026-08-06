"""Cost checks. Each returns a Finding or None.

A Finding carries an estimated dollar saving so the report can rank by impact
rather than by opinion. Estimates are deliberately conservative and every one
states the arithmetic behind it, because a number nobody can reproduce is a
number nobody will act on.
"""

import os
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from pricing import (CACHE_READ_MULT, CACHE_WRITE_1H_MULT, CACHE_WRITE_5M_MULT,
                     FAMILY_TIER, prices_for)

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@dataclass
class Finding:
    key: str
    title: str
    severity: str          # "high" | "medium" | "low" | "ok"
    savings: float         # estimated USD saveable over the analysed window
    summary: str           # one-line verdict
    detail: str = ""       # markdown body: the evidence and the math
    fix: str = ""          # what to actually change
    table: list = field(default_factory=list)  # [(col, col, ...)], first row = header


def _pct(n, d):
    return 100.0 * n / d if d else 0.0


def blended_input_price(calls):
    """Input $/token, weighted by tokens actually consumed on each model.

    An unweighted mean over calls prices a Haiku call the same as an Opus call,
    which is wrong by up to 15x when a workload mixes tiers: thousands of small
    cheap subagent calls would drag the effective price far below what the
    expensive calls actually consuming the tokens really cost.
    """
    total_tokens = 0
    total_cost = 0.0
    for c in calls:
        toks = c.total_input
        if toks <= 0:
            continue
        total_tokens += toks
        total_cost += toks * prices_for(c.model)[0] / 1e6
    if not total_tokens:
        return 0.0
    return total_cost / total_tokens


def _money(x):
    if x >= 100:
        return f"${x:,.0f}"
    if x >= 1:
        return f"${x:,.2f}"
    return f"${x:.3f}"


def _tokens(n):
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= size:
            return f"{n / size:.1f}{unit}"
    return str(int(n))


# --------------------------------------------------------------------------
# 1. Cache health
# --------------------------------------------------------------------------

@check
def cache_hit_rate(ctx):
    calls = ctx.calls
    read = sum(c.cache_read for c in calls)
    write = sum(c.cache_write for c in calls)
    raw = sum(c.raw_input for c in calls)
    billed_input = read + write + raw
    if not billed_input:
        return None

    hit = _pct(read, billed_input)
    spend = ctx.total_cost
    uncached = sum(c.cost_uncached for c in calls)
    saved = uncached - spend

    # A poor hit rate means the prefix is being rebuilt instead of reused.
    # Model the upside as reaching a healthy 90% hit rate: the tokens that are
    # currently re-written would instead be read at 0.1x.
    savings = 0.0
    if hit < 90 and write > read * 0.15:
        excess = write - (read + write) * 0.10
        if excess > 0:
            per_tok = blended_input_price(calls)
            savings = excess * per_tok * (CACHE_WRITE_5M_MULT - CACHE_READ_MULT)

    if hit >= 90:
        sev, verdict = "ok", f"Cache hit rate {hit:.1f}% — healthy."
    elif hit >= 70:
        sev, verdict = "medium", f"Cache hit rate {hit:.1f}% — some prefix churn."
    else:
        sev, verdict = "high", f"Cache hit rate {hit:.1f}% — the prefix is being rebuilt constantly."

    return Finding(
        key="cache_hit_rate",
        title="Prompt cache hit rate",
        severity=sev,
        savings=savings,
        summary=verdict,
        detail=(
            f"Across {len(calls):,} API calls: **{_tokens(read)}** cache-read vs "
            f"**{_tokens(write)}** cache-write and **{_tokens(raw)}** uncached input.\n\n"
            f"Caching is currently saving {_money(saved)} "
            f"({_pct(saved, uncached):.0f}% off the {_money(uncached)} this would cost "
            f"with caching off).\n\n"
            "A cache read costs 0.1x base input; a 5m write costs 1.25x. So every "
            "avoidable re-write is a 12.5x markup over reusing the prefix."
        ),
        table=[
            ("Metric", "Value"),
            ("Cache hit rate", f"{hit:.1f}%"),
            ("Cache read tokens", _tokens(read)),
            ("Cache write tokens", _tokens(write)),
            ("Uncached input tokens", _tokens(raw)),
            ("Actual spend", _money(spend)),
            ("Spend if caching were off", _money(uncached)),
        ],
        fix=(
            "" if sev == "ok" else
            "Find what changes early in the prompt between turns: a hook injecting a "
            "timestamp or changing content via `UserPromptSubmit`, an MCP server "
            "reconnecting mid-session, or a statusline/CLAUDE.md that mutates. "
            "Anything that edits the prefix invalidates every token after it."
        ),
    )


@check
def cache_ttl(ctx):
    """1h cache writes cost 2x vs 1.25x for 5m. Only worth it if turns are >5min apart."""
    calls = ctx.calls
    w1h = sum(c.cache_write_1h for c in calls)
    w5m = sum(c.cache_write_5m for c in calls)
    total = w1h + w5m
    if not total or w1h == 0:
        return None

    share_1h = _pct(w1h, total)
    if share_1h < 5:
        return None

    # Gap distribution between consecutive main-thread calls, per session.
    gaps = []
    for sess in ctx.sessions:
        stamps = sorted(c.ts for c in sess.main_calls if c.ts)
        for a, b in zip(stamps, stamps[1:]):
            gaps.append((b - a).total_seconds())
    if not gaps:
        return None

    under5 = sum(1 for g in gaps if g < 300)
    mid = sum(1 for g in gaps if 300 <= g <= 3600)
    over60 = sum(1 for g in gaps if g > 3600)

    # The 1h premium only pays off in the 5-60min band. Everywhere else it is
    # pure markup: 2.0x vs 1.25x = 0.75x base input wasted.
    per_tok = blended_input_price(calls)
    wasted_share = _pct(under5 + over60, len(gaps)) / 100
    savings = w1h * per_tok * (CACHE_WRITE_1H_MULT - CACHE_WRITE_5M_MULT) * wasted_share

    useful = _pct(mid, len(gaps))
    sev = "high" if savings > 50 else ("medium" if savings > 5 else "low")

    return Finding(
        key="cache_ttl",
        title="Cache TTL choice (1-hour vs 5-minute)",
        severity=sev,
        savings=savings,
        summary=(
            f"{share_1h:.0f}% of cache writes use the 1h TTL, but only "
            f"{useful:.1f}% of turn gaps fall in the 5–60min window where it pays off."
        ),
        detail=(
            f"The 1-hour extended TTL bills cache writes at **2.0x** base input vs "
            f"**1.25x** for the standard 5-minute TTL. That premium only buys something "
            f"when consecutive turns are more than 5 minutes apart (so the cheap cache "
            f"would have expired) but less than an hour (so the expensive one hasn't).\n\n"
            f"Measured across {len(gaps):,} inter-turn gaps:\n\n"
            f"- **{_pct(under5, len(gaps)):.1f}%** are < 5 min — a 5m cache would have "
            f"survived; the 1h premium bought nothing.\n"
            f"- **{useful:.1f}%** are 5–60 min — the only band where 1h TTL saves a re-write.\n"
            f"- **{_pct(over60, len(gaps)):.1f}%** are > 60 min — the cache expires either way.\n\n"
            f"So the 2x premium is paid on {_tokens(w1h)} tokens to benefit ~{useful:.1f}% of turns."
        ),
        table=[
            ("TTL", "Write tokens", "Share"),
            ("1-hour (2.0x)", _tokens(w1h), f"{share_1h:.1f}%"),
            ("5-minute (1.25x)", _tokens(w5m), f"{100 - share_1h:.1f}%"),
        ],
        fix=(
            "Unset the extended cache TTL so writes bill at 1.25x instead of 2.0x. "
            "Check `CLAUDE_CODE_EXTENDED_CACHE_TTL` / cache settings in your env and "
            "`~/.claude/settings.json`. Worst case is an occasional re-cache when you "
            "step away for more than 5 minutes."
        ),
    )


# --------------------------------------------------------------------------
# 2. Worktrees
# --------------------------------------------------------------------------

@check
def worktree_cache_cost(ctx):
    """Each distinct working dir gets its own cache prefix — more dirs, more cold starts."""
    by_dir = defaultdict(list)
    for sess in ctx.sessions:
        if sess.cwd:
            by_dir[sess.cwd].append(sess)
    if len(by_dir) < 2:
        return None

    # Group sibling worktrees: same parent dir, and at least one path looks like
    # a worktree checkout of another.
    groups = defaultdict(list)
    for d in by_dir:
        groups[os.path.dirname(d.rstrip("/"))].append(d)
    multi = {k: v for k, v in groups.items() if len(v) > 1}

    # A cold start is the first call of a session: cache_read == 0 but a large write.
    cold_tokens = 0
    cold_count = 0
    for sess in ctx.sessions:
        for c in sess.main_calls:
            if c.cache_read == 0 and c.cache_write > 1000:
                cold_tokens += c.cache_write
                cold_count += 1

    if not cold_count:
        return None

    per_tok = blended_input_price(ctx.calls)
    # Cold-start writes are unavoidable in principle, but sessions fragmented
    # across many dirs multiply them. Model the excess as the cold starts beyond
    # one per directory.
    excess = max(0, cold_count - len(by_dir))
    avg_cold = cold_tokens / cold_count
    savings = excess * avg_cold * per_tok * CACHE_WRITE_5M_MULT * 0.5

    rows = [("Working directory", "Sessions", "Cost")]
    ranked = sorted(by_dir.items(), key=lambda kv: -sum(s.cost for s in kv[1]))
    for d, sessions in ranked[:8]:
        rows.append((
            "`" + (d if len(d) < 52 else "…" + d[-49:]) + "`",
            str(len(sessions)),
            _money(sum(s.cost for s in sessions)),
        ))

    sev = "medium" if multi and savings > 5 else "low"
    return Finding(
        key="worktrees",
        title="Worktree / working-directory fragmentation",
        severity=sev,
        savings=savings,
        summary=(
            f"{len(by_dir)} distinct working directories, "
            f"{cold_count:,} cold cache starts ({_tokens(cold_tokens)} written from scratch)."
            + (f" {len(multi)} sibling-worktree group(s) detected." if multi else "")
        ),
        detail=(
            "Every working directory builds its own cache prefix — a different CLAUDE.md, "
            "file tree and git branch means no prefix sharing. Each new session in each "
            "directory pays a **cold write** at 1.25x for the full system prompt + "
            "CLAUDE.md before any reuse begins.\n\n"
            f"Observed {cold_count:,} cold starts averaging {_tokens(avg_cold)} each. "
            f"With {len(by_dir)} directories in play, roughly {excess:,} of those cold "
            "starts are repeat sessions that could have continued an existing warm one.\n\n"
            + ("Sibling worktrees sharing a parent were detected — these duplicate the "
               "same CLAUDE.md and repo context under different paths, so none of that "
               "prefix is shared between them.\n" if multi else "")
        ),
        table=rows,
        fix=(
            "Fewer, longer-lived sessions per worktree beat many short ones. Resume with "
            "`claude --continue` instead of starting cold. If parallel worktrees are a "
            "workflow requirement, keep the shared prefix small — a lean CLAUDE.md pays "
            "off once per worktree per session."
        ),
    )


# --------------------------------------------------------------------------
# 3. Model tiering / subagent delegation
# --------------------------------------------------------------------------

@check
def expensive_model_grunt_work(ctx):
    """High-input / low-output turns on a premium model are retrieval, not reasoning."""
    THRESHOLD_OUT = 300     # tokens of output
    THRESHOLD_IN = 20_000   # tokens of input

    grunt = [
        c for c in ctx.calls
        if c.family == "opus" and c.output < THRESHOLD_OUT and c.total_input > THRESHOLD_IN
    ]
    if not grunt:
        return None

    grunt_cost = sum(c.cost for c in grunt)
    opus_calls = [c for c in ctx.calls if c.family == "opus"]
    if not opus_calls:
        return None

    # Same usage re-priced on Sonnet.
    def repriced(call, fam_in, fam_out):
        return (
            call.raw_input * fam_in / 1e6
            + call.cache_write_5m * fam_in / 1e6 * CACHE_WRITE_5M_MULT
            + call.cache_write_1h * fam_in / 1e6 * CACHE_WRITE_1H_MULT
            + call.cache_read * fam_in / 1e6 * CACHE_READ_MULT
            + call.output * fam_out / 1e6
        )

    s_in, s_out = prices_for("sonnet")
    sonnet_cost = sum(repriced(c, s_in, s_out) for c in grunt)
    savings = (grunt_cost - sonnet_cost) * 0.6  # assume 60% is genuinely delegable

    share = _pct(len(grunt), len(opus_calls))
    sev = "high" if savings > 50 else ("medium" if savings > 5 else "low")

    return Finding(
        key="model_tiering",
        title="Premium model doing retrieval work",
        severity=sev,
        savings=savings,
        summary=(
            f"{len(grunt):,} Opus calls ({share:.0f}% of all Opus calls) consumed "
            f">{THRESHOLD_IN // 1000}K input but produced <{THRESHOLD_OUT} output tokens — "
            f"{_money(grunt_cost)} of read-heavy, low-reasoning work."
        ),
        detail=(
            "A call that ingests a large context and emits almost nothing is doing "
            "**retrieval**: reading files, grepping, gathering context. That is the "
            "cheapest possible cognitive task and it is running on the most expensive "
            "model. Opus input is 5x Sonnet and 15x Haiku.\n\n"
            f"These {len(grunt):,} calls cost {_money(grunt_cost)} on Opus. The identical "
            f"token usage on Sonnet would be {_money(sonnet_cost)}. Assuming ~60% of it is "
            f"genuinely delegable retrieval, that is **{_money(savings)}** recoverable.\n\n"
            f"Median output on these calls: {statistics.median([c.output for c in grunt]):.0f} tokens."
        ),
        table=[
            ("Metric", "Value"),
            ("Opus retrieval-shaped calls", f"{len(grunt):,}"),
            ("Their cost on Opus", _money(grunt_cost)),
            ("Same usage on Sonnet", _money(sonnet_cost)),
            ("Median output tokens", f"{statistics.median([c.output for c in grunt]):.0f}"),
        ],
        fix=(
            "Push the read-heavy phase into a subagent pinned to a cheap model, and let "
            "the premium model judge only the distilled result. In a subagent definition, "
            "set `model: haiku` (or `sonnet`) in the frontmatter; the Explore agent exists "
            "for exactly this. Two-stage 'cheap model reads, expensive model decides' is "
            "the single highest-leverage change for a read-heavy workload."
        ),
    )


@check
def subagent_delegation(ctx):
    """Is read-heavy work delegated at all, and are the subagents on cheap models?"""
    side = [c for c in ctx.calls if c.is_sidechain]
    main = [c for c in ctx.calls if not c.is_sidechain]
    if not main:
        return None

    side_cost = sum(c.cost for c in side)
    main_cost = sum(c.cost for c in main)
    total = side_cost + main_cost

    fam_counts = Counter(c.family for c in side)
    cheap = sum(v for k, v in fam_counts.items() if FAMILY_TIER.get(k, 3) <= 2)
    expensive = sum(v for k, v in fam_counts.items() if FAMILY_TIER.get(k, 3) > 2)

    rows = [("Model", "Subagent calls", "Cost")]
    for fam, n in fam_counts.most_common():
        rows.append((fam, f"{n:,}", _money(sum(c.cost for c in side if c.family == fam))))

    if not side:
        return Finding(
            key="subagents",
            title="Subagent delegation",
            severity="high",
            savings=main_cost * 0.15,
            summary="No subagent usage at all — every token of exploration runs on the main model.",
            detail=(
                "There are no sidechain (subagent) calls in this window. That means all "
                "file reading, searching and context gathering happens on the main "
                "conversation, at the main model's price, and every byte read stays in "
                "the main context window for the rest of the session — inflating every "
                "subsequent turn.\n\n"
                "Delegating exploration to a subagent does two things: it runs at the "
                "subagent's (cheaper) model price, and the bulk output never enters the "
                "main context, so it isn't re-sent on every later turn."
            ),
            table=[],
            fix=(
                "Use the `Explore` agent for broad searches, or define subagents in "
                "`.claude/agents/*.md` with `model: haiku` for retrieval. Rule of thumb: "
                "if a task is high-input and low-judgement, it belongs in a subagent."
            ),
        )

    # Expensive subagents doing subagent work is a partial miss.
    exp_cost = sum(c.cost for c in side if FAMILY_TIER.get(c.family, 3) > 2)
    s_in, s_out = prices_for("sonnet")
    savings = exp_cost * 0.5 if expensive else 0.0
    cheap_share = _pct(cheap, len(side))

    if cheap_share >= 80 and side_cost / total > 0.15:
        sev = "ok"
        summary = (
            f"Good delegation: {_pct(side_cost, total):.0f}% of spend runs in subagents, "
            f"{cheap_share:.0f}% of them on cheaper models."
        )
    elif expensive:
        sev = "medium"
        summary = (
            f"{expensive:,} subagent calls ({_pct(expensive, len(side)):.0f}%) run on a "
            f"premium model, costing {_money(exp_cost)}."
        )
    else:
        sev = "low"
        summary = (
            f"Subagents are used ({_pct(side_cost, total):.0f}% of spend) and mostly on "
            f"cheap models, but delegation is light."
        )

    return Finding(
        key="subagents",
        title="Subagent delegation and model tiering",
        severity=sev,
        savings=savings,
        summary=summary,
        detail=(
            f"Subagent (sidechain) calls: **{len(side):,}** costing {_money(side_cost)}; "
            f"main-thread calls: **{len(main):,}** costing {_money(main_cost)}. "
            f"Subagents are {_pct(side_cost, total):.0f}% of spend.\n\n"
            f"{cheap_share:.0f}% of subagent calls run on Haiku/Sonnet-tier models."
            + (f" The remaining {expensive:,} run on a premium tier — if those are doing "
               f"retrieval rather than judgement, half that {_money(exp_cost)} is recoverable."
               if expensive else "")
        ),
        table=rows,
        fix=(
            "" if sev == "ok" else
            "Pin retrieval subagents to Haiku via `model: haiku` in the agent's frontmatter. "
            "Reserve premium models for the verdict step that reads the subagent's summary."
        ),
    )


# --------------------------------------------------------------------------
# 4. Context bloat
# --------------------------------------------------------------------------

@check
def context_bloat(ctx):
    """A large baseline prefix is paid on every single turn of every session."""
    baselines = []
    for sess in ctx.sessions:
        first = next((c for c in sess.main_calls if c.cache_write > 0), None)
        if first:
            baselines.append(first.cache_write + first.raw_input)
    if not baselines:
        return None

    median = statistics.median(baselines)
    per_tok = blended_input_price(ctx.calls)

    # Everything above a lean ~25K baseline is avoidable. It is paid twice: once
    # per session as a cache write, and again on every turn as a cache read.
    #
    # Only the WRITE half is claimed here. The per-turn read half is already
    # billed by session_hygiene / runaway_context, which charge for total context
    # size above 100K — and the baseline is part of that total. Claiming both
    # would double-count the same tokens across findings, so the reported saving
    # is deliberately the smaller, non-overlapping number.
    LEAN = 25_000
    excess = max(0, median - LEAN)
    turns = sum(len(s.main_calls) for s in ctx.sessions)
    savings = excess * len(ctx.sessions) * per_tok * CACHE_WRITE_5M_MULT
    read_half = excess * turns * per_tok * CACHE_READ_MULT

    if excess <= 0:
        sev = "ok"
    elif median > 60_000:
        sev = "high"
    elif median > 40_000:
        sev = "medium"
    else:
        sev = "low"

    mcp = ctx.mcp_tool_count
    return Finding(
        key="context_bloat",
        title="Baseline context size (system prompt + CLAUDE.md + tool schemas)",
        severity=sev,
        savings=savings,
        summary=(
            f"Median starting context is {_tokens(median)} tokens before any work begins"
            + (f"; {mcp} MCP tools are loaded." if mcp else ".")
        ),
        detail=(
            "The baseline prefix — system prompt, CLAUDE.md, tool definitions, MCP "
            "schemas — is written to cache once per session at 1.25x and then **read on "
            "every single turn** at 0.1x. It is the multiplier on your entire bill: a "
            "session with 200 turns pays for that prefix 200 times.\n\n"
            f"Median baseline here: **{_tokens(median)}** tokens across {len(ctx.sessions)} "
            f"sessions and {turns:,} main-thread turns. A lean setup lands near "
            f"{_tokens(LEAN)}.\n\n"
            f"Trimming it saves {_money(savings)} in cache writes, plus a further "
            f"~{_money(read_half)} in per-turn cache reads — that read saving is "
            "already counted under the session-context findings above, so it is not "
            "added again here.\n\n"
            + (f"MCP tool definitions are a common hidden bulk — **{mcp} tools** are "
               "currently exposed. Every one of their schemas sits in the prefix whether "
               "or not it is ever called.\n" if mcp else "")
        ),
        table=[
            ("Metric", "Value"),
            ("Median baseline context", _tokens(median)),
            ("Largest baseline", _tokens(max(baselines))),
            ("Sessions", f"{len(ctx.sessions):,}"),
            ("Main-thread turns", f"{turns:,}"),
            ("MCP tools exposed", str(mcp) if mcp else "n/a"),
        ],
        fix=(
            "" if sev == "ok" else
            "Trim CLAUDE.md to invariants only — move reference material into skills that "
            "load on demand. Disable MCP servers you don't use in this repo (they cost "
            "prefix bytes even when idle). Prefer deferred/on-demand tool schemas over "
            "always-loaded ones."
        ),
    )


@check
def session_hygiene(ctx):
    """Long sessions re-send an enormous context on every turn."""
    heavy = [s for s in ctx.sessions if s.peak_context() > 150_000]
    if not ctx.sessions:
        return None

    peaks = [s.peak_context() for s in ctx.sessions]
    median_peak = statistics.median(peaks)

    # Cost of the reads between a 100K working ceiling and the 200K window.
    # Anything above 200K is attributed to the runaway_context check instead, so
    # the two findings never bill the same tokens twice.
    CEILING = 100_000
    RUNAWAY = 200_000
    per_tok = blended_input_price(ctx.calls)
    excess_reads = sum(
        max(0, min(c.total_input, RUNAWAY) - CEILING)
        for s in ctx.sessions for c in s.main_calls
    )
    savings = excess_reads * per_tok * CACHE_READ_MULT * 0.5

    rows = [("Session", "Turns", "Peak context", "Cost")]
    for s in sorted(ctx.sessions, key=lambda s: -s.cost)[:8]:
        rows.append((
            (s.session_id or "?")[:8],
            f"{len(s.main_calls):,}",
            _tokens(s.peak_context()),
            _money(s.cost),
        ))

    sev = "high" if len(heavy) > len(ctx.sessions) * 0.25 else (
        "medium" if heavy else "low")

    return Finding(
        key="session_hygiene",
        title="Session length and context growth",
        severity=sev,
        savings=savings,
        summary=(
            f"{len(heavy)} of {len(ctx.sessions)} sessions exceeded 150K context; "
            f"median peak is {_tokens(median_peak)}."
        ),
        detail=(
            "Context is re-sent on every turn. A session that grows to 180K tokens is "
            "paying for 180K of cache reads on each subsequent turn, forever — even if "
            "the useful part of the conversation is the last 10K. The reads are cheap "
            "individually (0.1x) but they are paid per turn, so they dominate long sessions.\n\n"
            f"{excess_reads and _tokens(excess_reads) or '0'} tokens were read above a "
            f"{_tokens(CEILING)} working ceiling across this window.\n\n"
            f"Compaction events observed: {ctx.compactions}."
            + ("\n\nCompaction itself is not free — it re-reads the whole conversation to "
               "summarise it. Clearing at a natural task boundary is cheaper than letting "
               "auto-compact fire." if ctx.compactions else "")
        ),
        table=rows,
        fix=(
            "" if sev == "low" else
            "`/clear` between unrelated tasks rather than letting one session sprawl. "
            "Start a fresh session per issue/PR. If a session must run long, delegate the "
            "bulky reading to subagents so the transcript stays small."
        ),
    )


@check
def tool_output_waste(ctx):
    """Giant tool results land in context permanently and are re-read every turn."""
    results = [r for s in ctx.sessions for r in s.tool_results]
    if not results:
        return None

    BIG = 20_000  # chars, ~5K tokens
    big = [r for r in results if r.chars > BIG]
    if not big:
        return None

    big_chars = sum(r.chars for r in big)
    est_tokens = big_chars / 4

    # Each big result is re-read on every subsequent turn of its session.
    avg_turns_after = statistics.mean(
        [max(1, len(s.main_calls) / 2) for s in ctx.sessions]
    )
    per_tok = blended_input_price(ctx.calls)
    savings = est_tokens * avg_turns_after * per_tok * CACHE_READ_MULT * 0.5

    by_tool = Counter()
    for r in big:
        by_tool[r.name] += r.chars

    rows = [("Tool", "Oversized results", "Total chars")]
    counts = Counter(r.name for r in big)
    for name, chars in by_tool.most_common(6):
        rows.append((name, f"{counts[name]:,}", f"{chars:,}"))

    errors = [r for r in results if r.is_error]
    sev = "high" if len(big) > len(results) * 0.05 else "medium"

    return Finding(
        key="tool_output",
        title="Oversized tool output in context",
        severity=sev,
        savings=savings,
        summary=(
            f"{len(big):,} tool results exceeded {BIG // 1000}K characters "
            f"(~{_tokens(est_tokens)} tokens total), and each is re-read on every "
            "later turn of its session."
        ),
        detail=(
            "A tool result is not a one-off cost. Once it lands in the transcript it is "
            "part of the context for every subsequent turn — an unbounded `grep`, a "
            "`cat` of a generated file, or a full-file `Read` where 20 lines were needed "
            "keeps billing long after it stopped being useful.\n\n"
            f"Oversized results: **{len(big):,}** of {len(results):,} total "
            f"({_pct(len(big), len(results)):.1f}%), ~{_tokens(est_tokens)} tokens.\n\n"
            f"Failed tool calls (which occupy context while contributing nothing): "
            f"**{len(errors):,}** ({_pct(len(errors), len(results)):.1f}%)."
            + ("\n\nA high error rate usually means retry loops — the same failing edit or "
               "command attempted repeatedly, each attempt paying full context."
               if _pct(len(errors), len(results)) > 10 else "")
        ),
        table=rows,
        fix=(
            "Read with `offset`/`limit` instead of whole files. Pipe shell output through "
            "`head`/`wc -l`. Add build artifacts, `node_modules` and lockfiles to the "
            "search skip-list. Push exploratory greps into a subagent so the raw output "
            "never enters the main context."
        ),
    )


@check
def runaway_context(ctx):
    """Sessions that blow past the standard 200K window into long-context territory.

    Above ~200K the whole conversation is re-read on every turn at a size no
    amount of caching can make cheap: 800K cache-read tokens on Opus is ~$1.20
    per turn before the model has done anything. These sessions are almost
    always one task that should have been several.
    """
    RUNAWAY = 200_000
    offenders = [s for s in ctx.sessions if s.peak_context() > RUNAWAY]
    if not offenders:
        return None

    # Cost of the cache reads above the window, which is the part that a /clear
    # at a task boundary would simply not have happened.
    per_tok_by_fam = {}
    excess_cost = 0.0
    for s in offenders:
        for c in s.main_calls:
            over = c.total_input - RUNAWAY
            if over > 0:
                inp = prices_for(c.model)[0] / 1e6
                excess_cost += over * inp * CACHE_READ_MULT

    savings = excess_cost * 0.7  # some long-context work is genuinely necessary
    off_cost = sum(s.cost for s in offenders)

    rows = [("Session", "Directory", "Turns", "Peak context", "Cost")]
    for s in sorted(offenders, key=lambda s: -s.cost)[:10]:
        rows.append((
            (s.session_id or "?")[:8],
            (s.cwd or "?").split("/")[-1],
            f"{len(s.main_calls):,}",
            _tokens(s.peak_context()),
            _money(s.cost),
        ))

    worst = max(offenders, key=lambda s: s.peak_context())
    return Finding(
        key="runaway_context",
        title="Runaway sessions (context beyond 200K)",
        severity="high",
        savings=savings,
        summary=(
            f"{len(offenders)} sessions grew past 200K context — the largest reached "
            f"{_tokens(worst.peak_context())} over {len(worst.main_calls):,} turns. "
            f"These sessions account for {_money(off_cost)} "
            f"({_pct(off_cost, ctx.total_cost):.0f}% of all spend)."
        ),
        detail=(
            "This is the single biggest cost multiplier in most expensive setups.\n\n"
            "Context is re-sent on **every** turn. Once a session reaches 800K tokens, "
            "each additional turn re-reads 800K tokens before the model does any work — "
            "on Opus that is roughly **$1.20 per turn in pure re-reading**, whether the "
            "turn is a one-line edit or a deep refactor. Multiply by several hundred "
            "turns and the session costs more than a month of disciplined usage.\n\n"
            f"Worst offender: `{(worst.session_id or '?')[:8]}` in "
            f"`{(worst.cwd or '?').split('/')[-1]}` — {len(worst.main_calls):,} turns, "
            f"peak {_tokens(worst.peak_context())}, {_money(worst.cost)}.\n\n"
            f"Across all {len(offenders)} runaway sessions, "
            f"{_money(excess_cost)} was spent purely on re-reading context above the "
            "200K mark."
        ),
        table=rows,
        fix=(
            "Treat 200K as a hard ceiling. `/clear` at every task boundary — a new issue, "
            "a new PR, a new bug — instead of continuing one session all day. Push file "
            "reading into subagents so their output never enters the main transcript. "
            "If work genuinely spans many hours, write findings to a scratch file and "
            "start fresh rather than carrying the full history forward."
        ),
    )


@check
def config_levers(ctx):
    """Settings-level switches that change cost but leave no trace in usage numbers."""
    issues = []
    fixes = []
    settings = ctx.settings
    merged_env = {}
    for name in ("settings.json", "settings.local.json"):
        merged_env.update((settings.get(name) or {}).get("env") or {})

    # 1. No custom subagent definitions => subagents inherit the main model.
    #    Retrieval work then runs at premium prices by default.
    if not settings.get("has_agents_dir"):
        issues.append(
            "**No `~/.claude/agents/` directory.** Subagents inherit the main model "
            "instead of being pinned to a cheap one, so delegated retrieval costs the "
            "same as doing it inline."
        )
        fixes.append(
            "Create `~/.claude/agents/explore.md` with `model: haiku` in the frontmatter "
            "so read-heavy delegation actually lands on a cheap model."
        )

    # 2. MAX_THINKING_TOKENS is ignored by adaptive-reasoning models. Setting it
    #    and assuming thinking is capped is false confidence, not a cap.
    mtt = merged_env.get("MAX_THINKING_TOKENS")
    if mtt and str(mtt) != "0":
        issues.append(
            f"**`MAX_THINKING_TOKENS={mtt}` is not doing what it looks like.** "
            "Adaptive-reasoning models ignore nonzero thinking budgets — only `0` "
            "reliably disables thinking. This setting is very likely a no-op."
        )
        fixes.append(
            "Use effort levels to control reasoning cost on adaptive models; set "
            "`MAX_THINKING_TOKENS=0` only if you genuinely want thinking off."
        )

    # 3. A fallback chain can silently land on a pricier model.
    fb = None
    for name in ("settings.json", "settings.local.json"):
        fb = fb or (settings.get(name) or {}).get("fallbackModel")
    if fb:
        issues.append(
            f"**`fallbackModel` is set to `{fb}`.** Fallbacks fire on overload without "
            "announcing themselves; if the chain lands on a pricier model the extra "
            "spend is invisible."
        )
        fixes.append("Confirm every model in the fallback chain is one you want to pay for.")

    # 4. MCP output cap. Default is 25,000 tokens per tool result, which is a lot
    #    of context for one call to inject.
    cap = merged_env.get("MAX_MCP_OUTPUT_TOKENS")
    if ctx.mcp_tool_count and not cap:
        issues.append(
            f"**{ctx.mcp_tool_count} MCP tools in use with no `MAX_MCP_OUTPUT_TOKENS` cap.** "
            "The default allows up to 25,000 tokens per tool result, and whatever lands "
            "there stays in context for the rest of the session."
        )
        fixes.append(
            "Set `MAX_MCP_OUTPUT_TOKENS` to something like 5000 unless a server genuinely "
            "needs to return more."
        )

    if not issues:
        return None

    return Finding(
        key="config_levers",
        title="Configuration switches worth changing",
        severity="medium",
        savings=0.0,  # real but not separately attributable; avoid double-counting
        summary=f"{len(issues)} configuration issue(s) that affect cost but don't show up in token counts.",
        detail=(
            "These are settings-level findings. They have no separate dollar estimate "
            "because their cost is already counted in the findings above — but they are "
            "often the *mechanism* behind those numbers, and the cheapest things to change.\n\n"
            + "\n\n".join(f"- {i}" for i in issues)
        ),
        table=[],
        fix=" ".join(fixes),
    )


def build_findings(ctx):
    out = []
    for fn in CHECKS:
        try:
            f = fn(ctx)
        except Exception as exc:  # a broken check must not kill the report
            f = Finding(
                key=fn.__name__, title=fn.__name__, severity="low", savings=0.0,
                summary=f"check failed: {exc}",
            )
        if f:
            out.append(f)
    return out
