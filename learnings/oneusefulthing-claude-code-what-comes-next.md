# Claude Code and What Comes Next

**Source**: https://www.oneusefulthing.org/p/claude-code-and-what-comes-next
**Type**: Article/Newsletter (One Useful Thing by Ethan Mollick)
**Date Processed**: 2026-01-16

## Summary

Ethan Mollick's overview of Claude Code for a general audience. Focuses on high-level concepts (compacting, skills, subagents, MCP) rather than implementation details. More of an introduction than a technical guide.

## Key Learnings

### 1. Compacting for Long Sessions

Claude Code handles context limits by taking notes when running out of space, then clearing and resuming from those notes. Enables multi-hour autonomous work sessions.

**Applicability**: Low (describes built-in behavior, not a practice to adopt)
**Confidence**: Documented feature

### 2. Subagents for Parallel Processing

Create specialized AI instances for specific tasks. Benefits: parallel processing, cost reduction (cheaper models for simple work), separate context windows for focused problem-solving.

**Applicability**: Medium (we already have agents in setup.md)
**Confidence**: Tested

### 3. Request Critical Feedback Explicitly

AI tends toward optimistic rather than honest assessment. When having AI test or review, explicitly request critical feedback.

**Applicability**: Medium (prompting tip)
**Confidence**: Reported

### 4. Security: Only Use Trusted Skills

Skills can be hijacked with hidden prompt injection. Only use skills from trusted sources.

**Applicability**: High (security consideration)
**Confidence**: Known risk

### 5. Use Dedicated Folders with Backups

Provide dedicated folders with clear boundaries. Make backups of sensitive data before letting AI work on it.

**Applicability**: Low (basic practice)
**Confidence**: Common sense

## Assessment

### Recommended for setup.md

None. This article is more of an introduction for newcomers than a source of new patterns.

### Already covered

- Skills system → Already in setup.md
- Subagents → Already have agents concept
- Context persistence → Dev docs system handles this

### Not recommended

- No concrete configurations or patterns to extract
- Security warning is valid but generic (don't run untrusted code)

### Observations

This is a great article for explaining Claude Code to someone new, but doesn't add actionable patterns for our setup.md. The audience is general knowledge workers, not developers building infrastructure.

## Questions for Review

None — this source is informative but doesn't suggest changes to our setup.
