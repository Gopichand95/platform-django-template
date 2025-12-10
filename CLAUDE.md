# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Cookiecutter template for creating production-ready Django + Turborepo monorepos. Generated projects combine a Django backend with modern frontend apps (React/Astro) using pnpm workspaces.

## Development Commands

### Template Development (this repository)

```bash
# Install dependencies
uv sync

# Run tests (full suite)
uv run pytest -n auto tests

# Run quick test (defaults only)
QUICK_TEST=1 uv run pytest tests

# Run auto-fixable style tests
AUTOFIXABLE_STYLES=1 uv run pytest tests

# Test Docker builds
sh tests/test_docker.sh                    # Basic config
sh tests/test_docker.sh use_celery=y       # With Celery

# Generate a test project
uv run cookiecutter . --no-input
```

### Pre-commit Hooks

Pre-commit is configured with Ruff, Prettier, and pyproject-fmt. Runs automatically on commit or manually:

```bash
uv run pre-commit run --all-files
```

## Architecture

### Template Structure

```
hooks/                      # Cookiecutter hooks (pre/post generation)
scripts/                    # Version sync utilities
tests/                      # Template generation tests
{{cookiecutter.project_slug}}/  # Generated project template
```

### Generated Project Structure

The template produces a Turborepo monorepo with a modular monolith Django backend:

```
apps/                           # Frontend applications (Turborepo workspaces)
├── landing/                    # Astro static site
└── {project_slug}/             # Vite + React SPA
packages/                       # Shared workspace packages
├── ui/                         # Shared React component library (Radix UI)
├── eslint-config/              # Shared ESLint config
├── prettier-config/            # Shared Prettier config
└── typescript-config/          # Shared TypeScript configs
config/settings/                # Django settings (base, local, production, test)
{project_slug}/                 # Modular monolith - Django apps folder
└── users/                      # Custom user app (add more Django apps here)
docker/                        # Docker configurations
```

The `{project_slug}/` directory is the modular monolith container. Each subdirectory (like `users/`) is a Django app. Add new Django apps as sibling directories to `users/`.

### Key Configuration Options (cookiecutter.json)

- `use_drf`: Django REST Framework with OpenAPI (default: yes)
- `use_celery`: Celery + Redis task queue (default: no)
- `use_async`: ASGI support (default: no)
- `use_heroku`: Heroku deployment (default: no)
- `username_type`: "username" or "email" authentication

### Hooks Behavior

**pre_gen_project.py**: Validates project_slug (lowercase, valid Python identifier), author_name, and Heroku+Whitenoise requirement.

**post_gen_project.py**: Removes unused files based on options, generates random secrets in `.env`, installs Python deps via Docker uv, installs frontend deps via pnpm.

## Testing

Tests validate template generation across option combinations. Tests run on Ubuntu, Windows, and macOS (macOS skipped in CI for speed).

```bash
# Run specific test
uv run pytest tests/test_cookiecutter_generation.py::test_project_generation -k "defaults"

# Run with verbose output
uv run pytest -v tests/test_cookiecutter_generation.py
```

## Tech Stack

- **Python**: 3.13, Django 5.2, uv for dependency management
- **Frontend**: Node 22.14, pnpm 10.12, Turborepo
- **Database**: PostgreSQL 18
- **Code Quality**: Ruff, Prettier, djlint, mypy
