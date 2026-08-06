Create a pull request for the current branch.

Steps:

1. Read `.github/pull_request_template.md` if it exists.
2. Run `git log master..HEAD --oneline` to get commit history.
3. Run `git diff master..HEAD --stat` to get the changed files summary.
4. Fill in each section of the PR template using the git context.
5. Create the PR with `gh pr create --title "..." --body "..."`.

IMPORTANT: `gh pr create --body` overrides GitHub's template auto-fill.
You MUST read and reproduce the template manually in the `--body` argument.

## Repo-specific checks

This repo is **public** while the config it documents is private. Before creating
the PR, verify the diff, the commit messages, and the PR body you are about to
write are all free of:

- the private source repo's name
- internal URLs and hostnames
- infrastructure specifics (cluster names, AWS profile names, account IDs)
- verbatim quotes from private source
- internal incident or ticket references

```bash
git diff master..HEAD | grep -nEi '<private-repo-name>|<internal-domain>|arn:aws|[0-9]{12}'
```

Check the PR body separately — it is not part of the diff, and it is the easiest
place to leak a name by accident.

Docs-only repo, so there is no build or test suite to run. Do lint the markdown
you touched:

```bash
npx --yes markdownlint-cli2 <changed-files>
```

Pre-existing warnings are expected (this repo's prose predates the default
rules). Fix what you introduced; don't reflow whole documents.
