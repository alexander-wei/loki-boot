---
name: gh-issues
description: Read and work on loki-boot GitHub issues with the gh CLI.
---

# GitHub Issues

Use `gh` for issue work in `alexander-wei/loki-boot` (the upstream repository).

## Read and select

```sh
gh auth status
gh issue list --repo alexander-wei/loki-boot --state open
gh issue view <number> --repo alexander-wei/loki-boot
```

Before starting, check whether the issue already has an open PR:

```sh
gh pr list --repo alexander-wei/loki-boot --state open
```

Read the issue and relevant files first. Keep the change scoped to the requested issue.

## Start issue work

This checkout's `origin` is a fork owned by `dev1-alexwei-net`; `upstream` is `alexander-wei/loki-boot`. Keep those roles distinct. Start a branch from the upstream default branch, for example:

```sh
git status --short
git fetch upstream master
git switch -c fix/issue-<number>-<short-name> upstream/master
```

Push the branch to the fork (`origin`), but open the PR against upstream. See the `gh-prs` skill for the exact command. Never create the PR in the fork just because `origin` points there.

Only comment on or close an issue when the requested work calls for it. Reference the issue in the PR body so GitHub links the work.
