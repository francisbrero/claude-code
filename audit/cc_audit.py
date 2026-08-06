#!/usr/bin/env python3
"""cc-audit — audit a Claude Code setup for cost efficiency.

Reads local transcripts from ~/.claude/projects, works out where the money went,
and writes a ranked, actionable markdown report.

    python3 cc_audit.py                    # last 30 days -> CC-AUDIT.md
    python3 cc_audit.py --days 7
    python3 cc_audit.py --out report.md
    python3 cc_audit.py --json             # machine-readable, for aggregating

Standard library only. Nothing leaves the machine.
"""

import argparse
import json
import os
import statistics
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from checks import _money, _tokens, build_findings  # noqa: E402
from parse import load_sessions  # noqa: E402

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "ok": 3}
SEVERITY_LABEL = {
    "high": "🔴 High",
    "medium": "🟠 Medium",
    "low": "🟡 Low",
    "ok": "🟢 Healthy",
}


class Context:
    """Everything the checks need, computed once."""

    def __init__(self, sessions, settings):
        self.sessions = sessions
        self.calls = [c for s in sessions for c in s.calls]
        self.settings = settings
        self.total_cost = sum(c.cost for c in self.calls)
        self.compactions = sum(s.compactions for s in sessions)
        self.mcp_tool_count = settings.get("mcp_tool_count", 0)


def load_settings():
    """Read local config for signals the transcripts don't carry."""
    out = {}
    home = os.path.expanduser("~/.claude")

    for name in ("settings.json", "settings.local.json"):
        path = os.path.join(home, name)
        if os.path.exists(path):
            try:
                with open(path) as fh:
                    out[name] = json.load(fh)
            except (OSError, json.JSONDecodeError):
                pass

    # MCP servers configured for this user.
    mcp_path = os.path.join(home, ".claude.json")
    servers = {}
    for candidate in (mcp_path, os.path.expanduser("~/.claude.json")):
        if os.path.exists(candidate):
            try:
                with open(candidate) as fh:
                    data = json.load(fh)
                servers.update(data.get("mcpServers") or {})
            except (OSError, json.JSONDecodeError):
                pass
            break
    out["mcp_servers"] = sorted(servers)
    return out


def count_mcp_tools(sessions):
    """Count distinct MCP tools that appeared in these sessions.

    MCP tool schemas sit in the prompt prefix, so their count is a proxy for how
    much of the baseline context they occupy.
    """
    names = set()
    for s in sessions:
        for c in s.calls:
            for t in c.tools:
                if t and t.startswith("mcp__"):
                    names.add(t)
    return len(names)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def md_table(rows):
    if not rows:
        return ""
    head, body = rows[0], rows[1:]
    out = ["| " + " | ".join(str(c) for c in head) + " |",
           "|" + "|".join("---" for _ in head) + "|"]
    for r in body:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def spend_overview(ctx):
    calls = ctx.calls
    by_family = Counter()
    for c in calls:
        by_family[c.family] += c.cost

    rows = [("Model", "Calls", "Input tokens", "Output tokens", "Cost", "Share")]
    fam_calls = Counter(c.family for c in calls)
    for fam, cost in by_family.most_common():
        fam_list = [c for c in calls if c.family == fam]
        rows.append((
            fam,
            f"{fam_calls[fam]:,}",
            _tokens(sum(c.total_input for c in fam_list)),
            _tokens(sum(c.output for c in fam_list)),
            _money(cost),
            f"{100 * cost / ctx.total_cost:.1f}%" if ctx.total_cost else "—",
        ))
    return rows


def render(ctx, findings, days):
    sessions = ctx.sessions
    calls = ctx.calls
    starts = [s.start for s in sessions if s.start]
    window = ""
    if starts:
        window = f"{min(starts):%Y-%m-%d} → {max(starts):%Y-%m-%d}"

    total_savings = sum(f.savings for f in findings)
    actionable = [f for f in findings if f.severity != "ok"]
    actionable.sort(key=lambda f: (-f.savings, SEVERITY_ORDER[f.severity]))
    healthy = [f for f in findings if f.severity == "ok"]

    out = []
    out.append("# Claude Code cost audit\n")
    out.append(
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} · "
        f"last {days} days · {window}_\n"
    )

    # --- Headline -------------------------------------------------------
    out.append("## Bottom line\n")
    pct = 100 * total_savings / ctx.total_cost if ctx.total_cost else 0
    out.append(
        f"Analysed **{len(sessions):,} sessions** / **{len(calls):,} API calls** "
        f"costing **{_money(ctx.total_cost)}**.\n"
    )
    if total_savings > 0.01:
        out.append(
            f"Estimated recoverable: **{_money(total_savings)} (~{pct:.0f}%)** "
            f"across {len(actionable)} finding(s), ranked below by impact.\n"
        )
    else:
        out.append("No material savings identified — this setup looks efficient.\n")

    out.append(md_table([
        ("Metric", "Value"),
        ("Sessions", f"{len(sessions):,}"),
        ("API calls", f"{len(calls):,}"),
        ("Total input tokens", _tokens(sum(c.total_input for c in calls))),
        ("Total output tokens", _tokens(sum(c.output for c in calls))),
        ("Total spend", _money(ctx.total_cost)),
        ("Estimated recoverable", f"{_money(total_savings)} ({pct:.0f}%)"),
    ]) + "\n")

    # --- Priority list --------------------------------------------------
    if actionable:
        out.append("## Roadmap — highest impact first\n")
        rows = [("#", "Change", "Severity", "Est. saving")]
        for i, f in enumerate(actionable, 1):
            rows.append((i, f.title, SEVERITY_LABEL[f.severity], _money(f.savings)))
        out.append(md_table(rows) + "\n")

    # --- Spend breakdown ------------------------------------------------
    out.append("## Where the money goes\n")
    out.append(md_table(spend_overview(ctx)) + "\n")

    top = sorted(sessions, key=lambda s: -s.cost)[:10]
    if top:
        out.append("### Most expensive sessions\n")
        rows = [("Session", "Date", "Directory", "Turns", "Peak context", "Cost")]
        for s in top:
            d = (s.cwd or "?").split("/")[-1]
            rows.append((
                (s.session_id or "?")[:8],
                f"{s.start:%Y-%m-%d}" if s.start else "?",
                d,
                f"{len(s.main_calls):,}",
                _tokens(s.peak_context()),
                _money(s.cost),
            ))
        out.append(md_table(rows) + "\n")

    # --- Findings -------------------------------------------------------
    out.append("## Findings\n")
    for i, f in enumerate(actionable, 1):
        out.append(f"### {i}. {f.title} — {SEVERITY_LABEL[f.severity]}\n")
        out.append(f"**{f.summary}**\n")
        if f.savings > 0.01:
            out.append(f"> Estimated saving: **{_money(f.savings)}**\n")
        if f.detail:
            out.append(f.detail + "\n")
        if f.table:
            out.append(md_table(f.table) + "\n")
        if f.fix:
            out.append(f"**Fix:** {f.fix}\n")

    if healthy:
        out.append("## Already healthy\n")
        for f in healthy:
            out.append(f"- **{f.title}** — {f.summary}")
        out.append("")

    out.append("## Method\n")
    out.append(
        "Parsed from local `~/.claude/projects/**/*.jsonl` transcripts. Each `assistant` "
        "record is one billed API call; costs come from its `usage` block priced at "
        "published per-model rates (cache write 1.25x/2.0x, cache read 0.1x base input).\n\n"
        "Savings estimates are deliberately conservative and each finding shows its "
        "arithmetic. They are directional, not invoices — use them to rank what to change "
        "first, then verify against Console billing.\n"
    )
    return "\n".join(out)


def to_json(ctx, findings, days):
    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "window_days": days,
        "sessions": len(ctx.sessions),
        "api_calls": len(ctx.calls),
        "total_cost_usd": round(ctx.total_cost, 2),
        "estimated_savings_usd": round(sum(f.savings for f in findings), 2),
        "input_tokens": sum(c.total_input for c in ctx.calls),
        "output_tokens": sum(c.output for c in ctx.calls),
        "findings": [
            {
                "key": f.key,
                "title": f.title,
                "severity": f.severity,
                "savings_usd": round(f.savings, 2),
                "summary": f.summary,
                "fix": f.fix,
            }
            for f in sorted(findings, key=lambda f: -f.savings)
        ],
    }


def main():
    ap = argparse.ArgumentParser(
        prog="cc-audit",
        description="Audit a Claude Code setup for cost efficiency.",
    )
    ap.add_argument("--days", type=int, default=30,
                    help="how far back to analyse (default: 30)")
    ap.add_argument("--out", default="CC-AUDIT.md",
                    help="markdown report path (default: CC-AUDIT.md)")
    ap.add_argument("--json", action="store_true",
                    help="also print machine-readable JSON to stdout")
    ap.add_argument("--root", default=None,
                    help="transcript root (default: ~/.claude/projects)")
    ap.add_argument("--limit", type=int, default=None,
                    help="max sessions to analyse (for a quick look)")
    args = ap.parse_args()

    print(f"Reading transcripts (last {args.days} days)…", file=sys.stderr)
    sessions = load_sessions(root=args.root, since_days=args.days, limit=args.limit)
    if not sessions:
        print("No transcripts found. Is this the machine you run Claude Code on?",
              file=sys.stderr)
        return 1

    settings = load_settings()
    settings["mcp_tool_count"] = count_mcp_tools(sessions)
    ctx = Context(sessions, settings)

    print(f"Analysing {len(sessions):,} sessions / {len(ctx.calls):,} API calls…",
          file=sys.stderr)
    findings = build_findings(ctx)

    report = render(ctx, findings, args.days)
    with open(args.out, "w") as fh:
        fh.write(report)

    savings = sum(f.savings for f in findings)
    print(f"\n  Spend analysed:  {_money(ctx.total_cost)}", file=sys.stderr)
    print(f"  Recoverable:     {_money(savings)}", file=sys.stderr)
    print(f"  Report:          {args.out}\n", file=sys.stderr)

    if args.json:
        print(json.dumps(to_json(ctx, findings, args.days), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
