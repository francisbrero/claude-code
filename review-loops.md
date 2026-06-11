# Automated Review Loops & External-Agent Safety

Patterns hardened in hip-phoenix *after* the original [setup.md](setup.md) was written. Where `setup.md` sketches generic plan/code review loops, this is what the production version actually looks like once you run it against a real codebase for a few months: a primary external reviewer (Codex) with an automatic in-model fallback, a strict convergence contract, three distinct review passes, and the safety + token-cost guardrails you discover only after they bite you.

## 1. Reviewer subagents: external-primary, in-model fallback

The review loops in `setup.md` assume a single reviewer. In practice you want the *strongest available* reviewer with a guarantee the loop never silently stalls. The hip-phoenix `plan-reviewer` and `code-reviewer` subagents both follow the same shape:

**Step 1 — try the external reviewer (Codex).** Pin the model explicitly; never inherit CLI defaults from `~/.codex/config.toml`, because a teammate's local config should not change what your review loop does:

```bash
.claude/hooks/codex-safe.sh exec \
  -m gpt-5.5 \
  -c model_reasoning_effort=high \
  review --base master --full-auto -o /tmp/review-out.md
```

**Step 2 — detect failure honestly.** Treat the external run as *failed* (and fall back) when ANY of these hold — not just on a non-zero exit code:

- non-zero exit / CLI missing / auth or credit-exhaustion error
- empty output file
- the output does not contain the literal contract string `MATERIAL_FINDINGS`

That last one matters: an external agent can "succeed" while reviewing the wrong target (e.g. a sandboxed GitHub plugin that can't reach the PR silently reviews a stale local branch and returns prose with no verdict). Treat format-less output as failure, not as a clean review.

**Step 3 — fall back to the in-model reviewer (Opus).** Same input contract, same output format. The fallback reads the diff/plan directly (`gh pr diff`, `git diff --base`, `Read`), spot-checks the load-bearing claims against the actual code, and applies the same severity rubric. The point of the fallback is to **keep the loop running** when the external reviewer is down — never to report "reviewer unavailable" with an empty findings list.

Every review — both paths — ends with a machine-parseable footer:

```
MATERIAL_FINDINGS: true|false
REVIEWER: codex|claude-opus
```

The `REVIEWER:` line is mandatory in both paths so the parent agent (and you, reading the log) can tell which reviewer produced a finding without grepping logs.

## 2. The convergence contract

The loop's stop condition is severity-gated, and the gating is **not re-litigated** by the wrapper agent:

- `MATERIAL_FINDINGS: true` iff at least one finding is `[critical] / [high] / [major]`.
- `[minor] / [nit] / style` findings may be listed but never flip the gate on their own.
- The parent agent does **not** re-classify or filter — any material finding from *either* reviewer (Codex or the Opus fallback) sets the gate. This is deliberate: it stops a wrapper from rationalizing away a real finding to escape the loop.

Loop until `MATERIAL_FINDINGS: false` or a hard cap (10 rounds in hip-phoenix). Log every round — round number, reviewer, findings summary — in `context.md` so a resumed session knows where the loop stood.

## 3. Three review passes, not one

A single post-implementation review misses two whole classes of problem. hip-phoenix runs the loop at three points:

| Pass | When | Scope argument | Catches |
|------|------|----------------|---------|
| **Plan review** | after writing `plan.md`, before any code | the plan file | wrong approach, missing migration step, unstated dependency — *before* you've written code against it |
| **Code review** | after implementation, before commit | `base master` (matches the eventual PR diff — **not** `uncommitted`) | bugs, missing tests, convention drift |
| **Post-PR review** | after the PR is opened | `pr <PR_URL>` | what a human reviewer actually sees on GitHub — rendered diff, CI context, cross-file interactions the local diff obscured |

The plan pass is the highest-leverage one and the easiest to skip. A material plan finding costs one paragraph to fix; the same flaw caught at code-review costs a rewrite.

Use `base <branch>` for the code pass, not `uncommitted`. `--base` produces the same diff the PR will show, so the reviewer sees exactly what a human will. `uncommitted` drifts from the PR the moment you commit.

## 4. `codex-safe.sh`: strip secrets before invoking an external agent

Any CLI agent you shell out to inherits your environment — including `DATABASE_URL`, `AUTH_SECRET`, API keys loaded from `.env`. An external reviewer does not need them, and you do not want them in that process's context, telemetry, or any prompt it might construct. Wrap the invocation in a script that unsets them:

```bash
#!/bin/bash
# codex-safe.sh — strip credentials before invoking an external agent CLI
set -e
env \
  -u DATABASE_URL \
  -u TEST_DATABASE_URL \
  -u AUTH_SECRET \
  -u AUTH_GOOGLE_ID \
  -u AUTH_GOOGLE_SECRET \
  -u SENDGRID_API_KEY \
  -u REDIS_URL \
  -u OPENROUTER_API_KEY \
  codex "$@"
```

Always route the external reviewer through this wrapper rather than calling `codex` directly. The list should mirror every secret-bearing key your `.env` actually defines — audit it whenever you add a new secret.

> **Aside — never paste a live secret into a prompt.** Selecting a `.env` line and dropping it into a Claude prompt sends it to the model and may be retained. If that happens, rotate the credential rather than hoping it wasn't logged. The whole reason `codex-safe.sh` exists is that secrets leak through the seams of agent tooling, not through the front door.

## 5. Subagent scope hygiene (a token-cost guardrail)

A review or exploration subagent with filesystem tools will, left to its own devices, enumerate `node_modules/`, build output, and generated files — burning a large fraction of its budget before doing any useful work. Bake the skip-list into the subagent's prompt; it does not read your `CLAUDE.md` automatically.

One line to paste into any `Explore` / reviewer subagent prompt:

> *Do not read, grep, or enumerate `node_modules/`, build/cache dirs (`.next`, `.docusaurus`, `dist`, `build`), generated files (`src/generated/`, migration snapshot JSON, any `llms-full.txt`), dev-docs scratch dirs, or `*.lock`. If you need evidence from a library internal, cite the one specific file.*

For the in-model fallback reviewer specifically, pass the equivalent as ripgrep globs (`--glob '!node_modules/**'`). The reviewer's job is to verify the diff's load-bearing claims against the code being changed — framework internals matter only when the diff itself cites a specific `file:line`.

### Match the model tier to the work, not to the task label

`setup.md`'s core principle — *high-volume, low-reasoning search goes to a Haiku subagent; reserve Opus for reasoning that needs the full context* — applies **inside** a review loop too, not just to standalone `Explore` calls. A review pass is rarely one homogeneous lump of "reasoning"; it's a heavy, judgment-light evidence-gathering phase followed by a small, judgment-heavy verdict.

Split it on that seam:

- **Haiku** for anything that reads or grabs a lot of content but barely reasons over it: collecting the diff, enumerating changed files, pulling the surrounding context for each hunk, grepping for every caller of a changed symbol, fetching the issue body and linked files. This is the bulk of the tokens and almost none of the thinking.
- **Opus (or the main session)** only for the actual verdict: weighing whether a change is correct, classifying finding severity, deciding `MATERIAL_FINDINGS`. This is almost none of the tokens and all of the thinking.

The trap is labeling the whole subagent "code review → must be Opus" and paying Opus rates to scroll through a 2,000-line diff. The *reading* of the diff is Haiku work; only the *judgment* is Opus work. If a subagent's job is overwhelmingly "search through / grab through a lot of content and report back," it's a Haiku subagent — even if it lives inside a loop you think of as high-stakes. Reserve Opus for the call where being wrong actually costs something.

Rule of thumb: before spawning a subagent, ask *"does this need to reason, or just to retrieve?"* Retrieval is Haiku. Only genuine judgment earns Opus.

## 6. Stop-hook gates that pair with the loops

Two Stop hooks worth adding alongside the review loops, because they catch the "the code is correct but a derived artifact drifted" class that reviewers reading only the diff tend to miss:

- **Derived-doc drift checker** — if MCP-tool / agent docs were edited this session but the aggregated `llms.txt` (or your equivalent generated doc) was not, warn before Stop. Source-of-truth and its generated mirror must move together.
- **Live integration-test gate by file category** — when files that talk to a real external API are edited (MCP tools, provider clients), remind to run *live* integration tests, not just unit tests. Unit tests on `execute()` mock the API and sail past bugs like a regex that doesn't match the real response shape — the exact failure mode this gate was built for.

Both read the session edit-log written by the `post-tool-use-tracker` hook and exit silently when nothing relevant changed.

---

**Why these aren't in `setup.md`:** every one of them is a lesson learned from a loop that stalled, a secret that nearly leaked, a subagent that spent its budget on `node_modules`, or a reviewer that approved a diff while a generated file silently drifted. They're the difference between review loops that look good in a README and review loops that converge on a real codebase under real failure conditions.
