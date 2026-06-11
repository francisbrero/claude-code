# SDLC Standards Worth Porting to Any Repo

These are repo-level engineering standards from hip-phoenix that change how *an agent* (and a human) should operate — guardrails Claude must respect, single-sources-of-truth it must not bypass, and CI gates it must understand before it touches deploy-adjacent code. They're not a generic DevOps cookbook; each one earns its place because ignoring it produces a class of mistake Claude will otherwise make confidently.

Everything here is verified against the live repo, not aspirational.

## 1. Generated files have one source of truth — never edit the output

Several artifacts in the repo are *generated* from a spec or a shared data file, and editing the generated output directly is always a bug — it gets silently overwritten on the next codegen run, and the spec/output drift apart.

Two instances worth copying as a pattern:

- **API models from a spec.** TypeSpec (`webapp/specifications/`) compiles via `pnpm types:compile` to `webapp/src/generated/`. The `.tsp` is the source; the generated TS is never hand-edited.
- **Shared constants across languages.** `shared/pricing/tiers.json` is the single source; `scripts/sync-pricing-tiers.mjs` regenerates both a TypeScript file (`webapp/src/lib/pricing-tiers.generated.ts`) and a Python file (`agent-service/src/pricing_tiers.py`). The generated files carry a "do not edit" header. The one fact lives in JSON; both stacks read a typed binding.

**The transferable rule, and how to make Claude obey it:** any file whose content is derived from another file must (a) carry a `// AUTO-GENERATED — DO NOT EDIT. Source: <path>. Regenerate: <command>` header, and (b) be named so the derivation is obvious (`*.generated.ts`). Then add a guardrail skill (`enforcement: "warn"`, see `setup.md` §3) keyed on the generated path or the keyword, so when Claude is about to edit it the hook fires: *"this is generated from X — edit X and run Y instead."* A drift check in CI (`pnpm check` fails if regenerating produces a diff) closes the loop.

This generalizes far beyond pricing: OpenAPI → client SDKs, protobuf → stubs, a design-tokens JSON → CSS vars + a TS theme. The principle is identical — **one editable source, N generated outputs, a header + a guardrail + a CI drift check.**

## 2. The DB migration *is* the deploy gate — understand it before touching schema

hip-phoenix gates production promotion on migrations succeeding, via a deliberately simple mechanism (`.github/workflows/db-migrations.yml`):

1. The workflow triggers on push to `master` filtered by path (`webapp/drizzle/**`, the schema dirs).
2. Its first action posts a **`pending` GitHub commit status** with a fixed context string (`Vercel - phoenix: Apply DB Migrations`).
3. Vercel's project is configured to wait on *that exact status string* before promoting the deploy.
4. On success the status flips to `success` and Vercel promotes; on failure the deploy is blocked.

Two things Claude must internalize when working in a repo like this:

- **The load-bearing identifier is the `context:` string, not the job name.** Renaming the workflow or job is safe; renaming the `context:` silently breaks the gate because the deploy platform is matching on the string. Any agent refactoring CI must treat that string as an API.
- **Migration triggers can have coverage gaps.** In hip-phoenix the per-PR preview-DB workflow (`neon-pr-branches.yml`) only fires on PR `opened`/`reopened`/`closed` — **not** on subsequent pushes to an already-open PR. So a PR that adds a column in its *second* commit leaves the preview DB on the old schema. Recovery is close+reopen the PR (or run the migrate command manually against the preview DB). The general lesson: **when a migration mysteriously "didn't apply," check the workflow's trigger `types` before assuming the migration itself is broken.**

**Transferable rule:** if schema changes gate deploys, document (a) the exact gate identifier, (b) the trigger paths/events and their gaps, and (c) the manual recovery command — and never use a "push schema directly" command (`db:push`-style) against any deployed environment; only versioned, auditable migrations.

## 3. Decouple validation from deployment — gate the release on a nightly, with an explicit, justified bypass

hip-phoenix merges to `master` continuously but does **not** treat every merge as a production release. The production release workflow (`.github/workflows/release-production.yml`) first runs a `verify-nightly` job that queries the last *scheduled* nightly E2E/smoke run against staging and refuses to proceed unless it passed.

Two design choices worth copying:

- **Nightly validates; release deploys.** Heavy, slow, flaky-prone suites (full E2E, visual, live-integration) run on a schedule against staging, not on every PR. The release gate just reads the latest nightly conclusion. This keeps PR CI fast while keeping production honest.
- **The bypass is explicit and self-documenting.** There's a `skip_nightly_gate` input "for urgent hotfixes only" that writes a visible note into the run summary when used. The escape hatch exists, but using it leaves a trail. This is the right shape for any gate an agent might be tempted to route around under pressure — make the bypass *possible but loud*, never silent.

**Transferable rule:** separate "is the code healthy?" (scheduled, comprehensive) from "ship it" (on-demand, gated on the latest health signal). Give the gate a bypass that demands a reason and records it.

## 4. Preview-env smoke tests for anything with an HTTP surface

Unit and E2E tests don't catch routing, edge config, env-injection, or auth-redirect bugs that only appear in a real deployment. hip-phoenix's PR template requires a manual preview-env smoke for changes touching REST / MCP / OAuth / webhook surfaces — link the `curl` and its result, backed by an ADR (`webapp/specifications/ards/2026_04_PrEnvironmentTesting.md`).

**Transferable rule:** for HTTP-facing changes, require evidence the surface actually works on a prod-class preview before review — not just that the unit tests pass. Bake the checklist into the PR template so it's not optional. (This pairs with the `/create-pr` + PR-template-enforcement pattern already in `setup.md` — the template is where you encode "what evidence does a reviewer need?")

## 5. Fail fast on the developer's machine, before `dev` even starts

A `predev` hook runs an env-validation script (`scripts/env-check.mjs`) before `pnpm dev`, and a `pnpm doctor` script (`scripts/doctor.mjs`) gives a full environment diagnostic. Missing/invalid env vars surface as a clear message at startup instead of as a confusing runtime crash three screens in.

**Transferable rule:** validate the environment at the earliest possible point (a `predev`/`prestart` hook), and ship a one-command `doctor` that checks tool versions, services, and required secrets. This is high-leverage for both human onboarding and for an agent setting up a fresh worktree — it turns "why won't this boot?" into a named, fixable error. (Complements the worktree-setup notes in `laptop-setup.md`.)

---

**The through-line:** each of these makes an invariant *legible and enforced* rather than relying on everyone (human or agent) to remember it. A generated file announces it's generated and a guardrail stops the edit; a deploy gate names its load-bearing string; a release gate's bypass writes its own justification; an HTTP change must show its smoke test; a broken env fails at `predev`. That legibility is exactly what lets an agent work safely in the repo without having memorized its entire operational history.
