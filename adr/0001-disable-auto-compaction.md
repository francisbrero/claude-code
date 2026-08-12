# ADR 0001: Disable auto-compaction; compact at explicit checkpoints instead

- **Status:** Accepted
- **Date:** 2026-08-12
- **Scope:** User-level `~/.claude/settings.json`; interacts with the compaction
  checkpoints in each repo's `fix-issue.md`

## Context

A cost audit across 30 days of local transcripts found that context re-reading
dominated spend: 74 sessions grew past 200K tokens, and roughly $1,285 was spent
re-reading context above the 200K mark in the two largest repos alone. The
mechanism is that context is re-sent on every API call, so a session that reaches
800K pays for 800K of cache reads on every subsequent call regardless of how
small the actual work is.

The first response was to lower `autoCompactWindow` to 160000, well below the
default (~95% of the context window). It worked on cost. Sessions that compacted
ran at $0.090 per API call against $0.184 for those that did not, and they
serviced a comparable number of user turns in ~40% fewer API calls.

It also produced a second problem. 160K sits just above the median session peak
of 132K, so the setting was catching the *typical* session rather than the
exceptional one. Compaction stopped being a safety net and became routine: one
session recorded **22 compactions across 750 API calls** — roughly one every 34
calls.

The concern that followed was not cost but quality: that the nuances of a
solution were being lost, and that the resulting code was drifting toward the
generic.

## Evidence

**Measured locally.** In the 22-compaction session, all 7 repeated file reads
occurred within 5 reads of a compaction boundary; none occurred mid-stretch. If
re-reading were ordinary edit-verify behaviour it would scatter across the
session. Clustering at boundaries is the visible surface of context loss. The
volume was small (~12% rework) — but re-reads are only the *recoverable* half of
the problem.

The unrecoverable half is invisible to this kind of measurement. When the model
loses a file it re-reads it, which shows up in the transcript. When it loses
*why* a decision was made, it proceeds confidently without it and ships the
generic version. There is no error, no retry, and no cost signal. Token counts
cannot distinguish "chose the obvious approach because it was right" from "chose
it because the constraint that ruled it out is gone."

**Corroborated externally.** Published work on long-horizon coding agents finds
compaction preferentially destroys exactly this material — "reasoning steps,
rationale, and constraints" — and that intermediate reasoning and task
constraints are the most vulnerable, being critical for success yet easily
eliminated by compression that optimises for token reduction. The concise
formulation: compaction optimises for *what to do next*, not *why we did what we
did*, so decision context is the first casualty. Summaries retain roughly 20–30%
of original detail.

Critically, **loss compounds across compactions.** Claude Code's own
documentation notes cumulative information loss over multiple compactions; Codex
CLI carries a similar warning. At 22 events, each retaining a fraction of the
previous summary, early-session rationale has been compressed repeatedly. That
is the mechanism behind drift toward generic output — not one lossy step, but
many.

This inverts the naive intuition (and an earlier recommendation in this work)
that a *smaller* window is safer. Smaller window means more frequent compaction,
and frequency is what compounds.

## Distribution

Peak context across 204 sessions that never compacted, so peaks are genuine
rather than clipped by the setting:

| Percentile | Peak context |
|---|---|
| p50 | 132K |
| p75 | 256K |
| p85 | 370K |
| p90 | 432K |
| p95 | 615K |
| p99 | 805K |

| Window | Share of sessions that would compact |
|---|---|
| 160K (previous) | ~50% |
| 300K | 20% |
| 400K | 14% |
| 500K | 8% |

The cost auto-compaction was saving in the tail is small: at a 400K window, the
29 affected sessions carry only **$350** of above-the-line spend out of $5,803.
At 500K it is $175. Auto-compaction was buying little in the tail while firing
constantly in the body of the distribution.

## Decision

**Disable auto-compaction** (`autoCompactEnabled: false`) and remove
`autoCompactWindow` rather than leaving a stale value beside a disabled flag.

Compaction now happens only when invoked deliberately — via `/compact`, or via
the checkpoints in each repo's `fix-issue.md` that fire after plan review and
after code review.

Those checkpoints are the reason this is viable. They fire at boundaries where
state is already written to `plan.md` / `context.md`, so the summary has
something durable to compress toward and nothing in flight is lost. Auto-compact
fires wherever the window happens to fill, frequently mid-task. Sessions in the
tail are the worst case for this: one recorded 991 API calls across 18 user
turns, meaning long autonomous stretches where an interruption destroys the most
accumulated reasoning.

## Consequences

**Expected.** Cost rises. Compacted sessions ran at roughly half the per-call
cost of uncompacted ones, and that difference is the price of this decision.
The "Context carried above 200K" component of the audit grade will rise; that is
the intended trade, not a regression.

**Risk accepted.** There is no automatic backstop. A long session can now run to
the context limit and stop rather than degrade. Based on 30 days, ~86% of
sessions would not have compacted even at a 400K window and only 1.5% exceeded
800K, so this is rare — but when it happens it is a hard stop. Mitigation is to
`/compact` deliberately when a session is visibly growing, which is strictly
better than the automatic behaviour because the moment is chosen.

**Not addressed by this decision.** Compaction remains lossy toward rationale
whenever it runs, including at explicit checkpoints. Material that exists only in
the transcript is one summarisation away from gone. The durable fix is to write
decisions — especially *rejected* approaches and the reasons for rejecting them —
to disk at the moment they are made, since anything loaded from disk is
re-injected after compaction while anything that arrived through conversation is
summarised. That is a separate change and is not made here.

## Alternatives considered

- **`autoCompactWindow: 400000`** — the 85/15 threshold, keeping auto-compaction
  as a genuine safety net rather than a routine mechanism. Rejected in favour of
  full control, on the view that the explicit checkpoints already cover the
  common path and the tail savings ($350/mo) do not justify unpredictable
  mid-task interruption. This is the natural fallback if the hard-stop risk
  proves annoying in practice.
- **Keep 160K and improve the compaction focus string** — treats the symptom.
  Focus strings help per event; they do not address compounding across 22 events.
- **Raise to 300K** — halves compaction count but still fires on ~20% of
  sessions, retaining routine-mechanism behaviour without the benefit of either
  extreme.

## Revisiting

Re-run the audit after a week of sessions. Compaction count should fall to near
zero. Watch whether any session hits the context limit, and whether cost rises
more than the ~2x per-call difference predicts.

The quality question — whether the code is crisper — is not measurable by this
tooling. Calls-per-user-turn and rework rates are proxies for "did it lose the
thread," not measurements of it. A read of recent diffs is better evidence than
any metric here, and should be what decides whether this holds.
