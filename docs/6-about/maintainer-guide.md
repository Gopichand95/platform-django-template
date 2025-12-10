# Maintainer guide

This document is intended for maintainers of the template.

## Automated updates

We use Dependabot to keep dependencies up-to-date, including Python packages, GitHub actions, npm packages, and Docker images.

## GitHub Actions workflows

### CI

`ci.yml`

The CI workflow runs on pushes to main and on pull requests. It covers two main aspects:

- **Tests job**: Runs pytest across Ubuntu, Windows, and macOS to validate template generation works correctly on all platforms.
- **Docker job**: Builds and tests Docker configurations for both the basic setup and with Celery enabled.

### Issue manager

`issue-manager.yml`

Uses [tiangolo/issue-manager](https://github.com/tiangolo/issue-manager) to automatically close issues and pull requests after a delay when labeled appropriately.

Runs daily at 00:12 UTC, and also triggers on issue comments, issue labeling, and PR labeling.

Configured labels and their behavior (all with 10-day delay):

| Label | Message |
|-------|---------|
| `answered` | Assuming the question was answered, this will be automatically closed now. |
| `solved` | Assuming the original issue was solved, it will be automatically closed now. |
| `waiting` | Automatically closing after waiting for additional info. To re-open, please provide the additional information requested. |
| `wontfix` | As discussed, we won't be implementing this. Automatically closing. |

### UV lock regeneration

`dependabot-uv-lock.yml`

Automatically regenerates `uv.lock` when `pyproject.toml` changes in PRs from Dependabot or PyUp. This ensures the lock file stays in sync with dependency updates.

Triggers on:
- Pull requests that modify `pyproject.toml` (from dependabot[bot] or pyup-bot)
- Manual workflow dispatch

### Align versions

`align-versions.yml`

Keeps version numbers synchronized across the template when Dependabot updates certain files. Runs the `scripts/node_version.py` and `scripts/ruff_version.py` scripts to propagate version changes.

Triggers on Dependabot PRs that modify:
- `{{cookiecutter.project_slug}}/.nvmrc`
- `{{cookiecutter.project_slug}}/requirements/local.txt`
