# Learnings

This folder contains processed learnings from AI coding resources.

## Structure

Each file represents one processed source:

```
learnings/
├── README.md
├── reddit-claude-code-tips-6-months.md
├── anthropic-effective-harnesses.md
└── ...
```

## File Format

Each learning file includes:

- **Source URL and metadata**
- **Summary** of the content
- **Key learnings** with applicability ratings
- **Assessment** of what to add to setup.md
- **Questions** requiring human review

## Workflow

1. Run `/process-source <url>` to analyze a resource
2. Review the generated learnings file
3. Decide which recommendations to incorporate into setup.md
4. Move the URL to "Reviewed sources" in sources.md
