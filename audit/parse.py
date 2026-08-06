"""Parse ~/.claude/projects/**/*.jsonl transcripts into an analysable model.

One JSONL file == one session. Each `assistant` record is one billed API call
and carries a `usage` block with the cache/token breakdown we need.

Nothing here interprets the data — that's the checks' job. This module only
normalises it.
"""

import glob
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pricing import cost_of, cost_without_cache, family_of


def _ts(value):
    """Parse an ISO timestamp into an aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@dataclass
class Call:
    """One billed assistant API call."""

    request_id: str
    ts: datetime
    model: str
    family: str
    raw_input: int
    cache_write_5m: int
    cache_write_1h: int
    cache_read: int
    output: int
    is_sidechain: bool
    tools: list = field(default_factory=list)
    skill: str = None

    @property
    def total_input(self):
        return self.raw_input + self.cache_write_5m + self.cache_write_1h + self.cache_read

    @property
    def cache_write(self):
        return self.cache_write_5m + self.cache_write_1h

    @property
    def cost(self):
        return cost_of(
            self.model, self.raw_input, self.cache_write_5m,
            self.cache_write_1h, self.cache_read, self.output,
        )

    @property
    def cost_uncached(self):
        return cost_without_cache(
            self.model, self.raw_input, self.cache_write_5m,
            self.cache_write_1h, self.cache_read, self.output,
        )


@dataclass
class ToolResult:
    """A tool result that landed in context, with its size in characters."""

    name: str
    chars: int
    is_error: bool


@dataclass
class Session:
    path: str
    session_id: str = None
    cwd: str = None
    git_branch: str = None
    version: str = None
    calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    user_turns: int = 0
    compactions: int = 0
    skills_used: set = field(default_factory=set)

    @property
    def cost(self):
        return sum(c.cost for c in self.calls)

    @property
    def cost_uncached(self):
        return sum(c.cost_uncached for c in self.calls)

    @property
    def start(self):
        stamps = [c.ts for c in self.calls if c.ts]
        return min(stamps) if stamps else None

    @property
    def end(self):
        stamps = [c.ts for c in self.calls if c.ts]
        return max(stamps) if stamps else None

    @property
    def main_calls(self):
        return [c for c in self.calls if not c.is_sidechain]

    @property
    def sidechain_calls(self):
        return [c for c in self.calls if c.is_sidechain]

    def peak_context(self):
        """Largest total input on any single main-thread call.

        This is the high-water mark of the context window in this session.
        """
        return max((c.total_input for c in self.main_calls), default=0)


def _result_text(part):
    content = part.get("content")
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return json.dumps(content)


def parse_session(path):
    """Read one transcript file into a Session. Malformed lines are skipped."""
    s = Session(path=path)
    try:
        fh = open(path, errors="replace")
    except OSError:
        return None

    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue

            s.session_id = s.session_id or d.get("sessionId")
            s.cwd = s.cwd or d.get("cwd")
            s.git_branch = s.git_branch or d.get("gitBranch")
            s.version = s.version or d.get("version")

            kind = d.get("type")

            if kind == "assistant":
                msg = d.get("message") or {}
                usage = msg.get("usage") or {}
                creation = usage.get("cache_creation") or {}
                tools = [
                    p.get("name")
                    for p in msg.get("content", [])
                    if isinstance(p, dict) and p.get("type") == "tool_use"
                ]
                model = msg.get("model") or "unknown"
                if model == "<synthetic>":
                    continue  # not a billed call
                skill = d.get("attributionSkill")
                if skill:
                    s.skills_used.add(skill)
                s.calls.append(Call(
                    request_id=d.get("requestId"),
                    ts=_ts(d.get("timestamp")),
                    model=model,
                    family=family_of(model),
                    raw_input=usage.get("input_tokens", 0) or 0,
                    cache_write_5m=creation.get("ephemeral_5m_input_tokens", 0) or 0,
                    cache_write_1h=creation.get("ephemeral_1h_input_tokens", 0) or 0,
                    cache_read=usage.get("cache_read_input_tokens", 0) or 0,
                    output=usage.get("output_tokens", 0) or 0,
                    is_sidechain=bool(d.get("isSidechain")),
                    tools=tools,
                    skill=skill,
                ))

            elif kind == "user":
                if d.get("isCompactSummary"):
                    s.compactions += 1
                if d.get("isMeta"):
                    continue
                content = (d.get("message") or {}).get("content")
                if isinstance(content, str):
                    # A real human turn (or a slash command expansion).
                    s.user_turns += 1
                elif isinstance(content, list):
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        if part.get("type") == "tool_result":
                            s.tool_results.append(ToolResult(
                                name=_tool_name_for(d),
                                chars=len(_result_text(part)),
                                is_error=bool(part.get("is_error")),
                            ))
                        elif part.get("type") == "text":
                            s.user_turns += 1

    return s if s.calls else None


def _tool_name_for(record):
    """Best-effort tool name for a tool_result record.

    The result record doesn't name the tool, but toolUseResult's shape hints at
    it. This is only used for grouping in the report, so a fallback is fine.
    """
    tur = record.get("toolUseResult")
    if isinstance(tur, dict):
        if "stdout" in tur:
            return "Bash"
        if "matches" in tur:
            return "Search"
        if "file" in tur or "content" in tur:
            return "Read"
        if "task" in tur:
            return "Agent"
    return "other"


def find_transcripts(root=None, since_days=None):
    """All transcript paths under the Claude projects dir, newest first."""
    root = root or os.path.expanduser("~/.claude/projects")
    paths = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)
    if since_days:
        cutoff = datetime.now(timezone.utc).timestamp() - since_days * 86400
        paths = [p for p in paths if os.path.getmtime(p) >= cutoff]
    return sorted(paths, key=os.path.getmtime, reverse=True)


def load_sessions(root=None, since_days=None, limit=None):
    """Load and deduplicate sessions.

    Claude Code forks a transcript into a new file whenever a session is
    resumed or branched, replaying the earlier history into each new file. So
    the same billed API call appears in several files, and roughly half of all
    assistant records on disk are replays.

    Billing happens once per `requestId`, so that is the unit of truth: keep the
    first occurrence of each request and drop the rest. Files sharing a
    sessionId are merged into one Session, since they are one conversation.
    """
    paths = find_transcripts(root, since_days)
    if limit:
        paths = paths[:limit]

    seen_requests = set()
    merged = {}
    for p in paths:
        s = parse_session(p)
        if not s:
            continue

        fresh = []
        for c in s.calls:
            # Calls with no requestId can't be dedup-keyed; keep them, they are rare.
            if c.request_id:
                if c.request_id in seen_requests:
                    continue
                seen_requests.add(c.request_id)
            fresh.append(c)

        key = s.session_id or p
        if key in merged:
            base = merged[key]
            base.calls.extend(fresh)
            # Tool results and turn counts are replayed in forked files too, so
            # take the richest single file's view rather than summing.
            if len(s.tool_results) > len(base.tool_results):
                base.tool_results = s.tool_results
            base.user_turns = max(base.user_turns, s.user_turns)
            base.compactions = max(base.compactions, s.compactions)
            base.skills_used |= s.skills_used
        else:
            s.calls = fresh
            merged[key] = s

    return [s for s in merged.values() if s.calls]
