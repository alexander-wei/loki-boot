---
name: gh-prs
description: Create and inspect pull requests for loki-boot with the gh CLI.
---

# GitHub Pull Requests

## Critical: fork versus upstream

This repository is checked out from a fork:

- Upstream/source repository (PR destination): `alexander-wei/loki-boot`
- Fork/push repository: `dev1-alexwei-net/loki-boot` (`origin`)

Push your branch to the fork, then create every PR in the upstream repository. Do **not** use the fork as `gh pr create --repo`. The explicit head owner is required because the fork belongs to a different user:

```sh
git push -u origin <branch>
gh pr create --repo alexander-wei/loki-boot --base master --head dev1-alexwei-net:<branch> --title "<type>: <short title>" --body-file /tmp/pr-body.md
```

If remotes differ in another checkout, inspect `git remote -v`; use the upstream repository as `--repo` and the actual fork owner/repository as `--head OWNER:<branch>`. Do not infer the PR destination from `origin`.

Verify the PR destination and head after creation:

```sh
gh pr view <number> --repo alexander-wei/loki-boot --json url,baseRefName,headRefName,headRepositoryOwner
```

The base must be `master`, and the head must be the pushed fork branch.

## PR body

Write a concise body describing:

- **Problem:** what the issue asks to solve.
- **Change:** what this PR adds or changes.
- **Impact:** who benefits and how.
- **Verification:** checks actually performed (never claim checks that were not run).
- Link the issue with `Closes #<number>` when this PR completes it.

Use `gh pr list --repo alexander-wei/loki-boot` and `gh pr view <number> --repo alexander-wei/loki-boot` to inspect upstream PRs. Use `gh pr checks <number> --repo alexander-wei/loki-boot` to inspect checks.
