# Process Source

Process a resource URL to extract AI coding learnings.

## Usage

```
/process-source <url>
```

## Workflow

### Step 1: Fetch and Analyze

Fetch the content from `$ARGUMENTS` using WebFetch (for articles/Reddit) or explore the repo (for GitHub).

Identify the source type:
- **Reddit post**: Look for discussion threads, tips, workflows
- **GitHub repo**: Look for .claude/, CLAUDE.md, hooks, commands, configurations
- **Article/blog**: Look for patterns, recommendations, case studies

### Step 2: Extract Learnings

Create a learnings file at `learnings/[source-name].md` with:

```markdown
# [Title]

**Source**: [URL]
**Type**: Reddit | GitHub | Article
**Date Processed**: [YYYY-MM-DD]

## Summary

[2-3 sentence overview of what this source covers]

## Key Learnings

### [Learning 1 Title]
[Description of the pattern/practice]

**Applicability**: High | Medium | Low
**Confidence**: Tested | Reported | Theoretical

### [Learning 2 Title]
...

## Relevant Code/Config

[Any specific configurations, commands, or code worth preserving]

## Assessment

### Recommended for setup.md
- [ ] [Specific addition 1]
- [ ] [Specific addition 2]

### Not recommended (with reasoning)
- [Pattern X] - [Why it doesn't fit our needs]

## Questions for Review

- [Any uncertainties that need human judgment]
```

### Step 3: Present Assessment

After creating the learnings file, present:

1. **Quick summary** of the source
2. **Top recommendations** for setup.md (if any)
3. **Questions** that need my input before updating setup.md

Do NOT automatically update setup.md. Always ask first with specific proposed changes.

### Step 4: Update sources.md

Move the URL from "To Review" to "Reviewed sources" in sources.md.

## Guidelines

- Be selective: only recommend additions likely to have real impact
- Prefer concrete, testable patterns over vague advice
- Note when something is "reported to work" vs "tested by us"
- Flag anything that conflicts with existing setup.md patterns
- When uncertain, ask rather than assume
