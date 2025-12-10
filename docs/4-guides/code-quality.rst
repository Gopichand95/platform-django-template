Code Quality
============

.. index:: code-quality, linters, formatters, type-checking, ruff, mypy, eslint, prettier, typescript, djlint, lefthook

This project uses a comprehensive code quality stack across both Python/Django and frontend workspaces. Python tools are configured in ``pyproject.toml``, while frontend tools use shared workspace packages in ``packages/``. All tools run automatically via Lefthook on pre-commit.

Quick Reference
---------------

.. list-table::
   :header-rows: 1
   :widths: 15 15 35 35

   * - Tool
     - Scope
     - Check Command
     - Fix Command
   * - Ruff
     - Python
     - ``ruff check .``
     - ``ruff check --fix .``
   * - Ruff (format)
     - Python
     - ``ruff format --diff .``
     - ``ruff format .``
   * - mypy
     - Python
     - ``mypy .``
     - —
   * - djLint
     - Templates
     - ``djlint {project_slug}/templates/``
     - ``djlint --reformat {project_slug}/templates/``
   * - ESLint
     - Frontend
     - ``pnpm turbo lint``
     - ``pnpm turbo lint -- --fix``
   * - Prettier
     - Frontend
     - ``pnpm format:check``
     - ``pnpm format``
   * - TypeScript
     - Frontend
     - ``pnpm turbo typecheck``
     - —
   * - Lefthook
     - All
     - ``lefthook run pre-commit``
     - —

Python/Django Tools
-------------------

Ruff
~~~~

Ruff is an extremely fast Python linter and formatter written in Rust. It replaces flake8, pylint, black, isort, pyupgrade, and many other tools in a single binary.

Ruff provides two commands:

- ``ruff check`` — linter (finds errors, style issues, bugs)
- ``ruff format`` — formatter (consistent code style)

**Configuration** is in ``pyproject.toml`` under ``[tool.ruff]``.

To check without modifying files::

    $ ruff format --diff .
    $ ruff check .

To auto-fix issues::

    $ ruff format .
    $ ruff check --fix .

.. note::
   Commit your changes before running ``--fix`` so you can revert if needed. The ``--unsafe-fixes`` flag can make breaking changes — use with caution.

**Enabled rule categories** include:

- ``F`` (Pyflakes) — undefined names, unused imports
- ``E``, ``W`` (pycodestyle) — PEP 8 style
- ``I`` (isort) — import sorting
- ``N`` (pep8-naming) — naming conventions
- ``UP`` (pyupgrade) — modern Python syntax
- ``DJ`` (flake8-django) — Django best practices
- ``B`` (bugbear) — likely bugs and design problems
- ``S`` (bandit) — security issues
- ``C4`` (comprehensions) — list/dict comprehension style
- ``SIM`` (simplify) — code simplification
- ``RUF`` — Ruff-specific rules

For the full list of enabled rules, see ``pyproject.toml``. Rule documentation: https://docs.astral.sh/ruff/rules/

mypy
~~~~

mypy provides static type checking for Python code with Django and DRF plugin support.

**Configuration** is in ``pyproject.toml`` under ``[tool.mypy]``.

Key settings:

- Python 3.13 target
- ``check_untyped_defs = true`` — checks functions without annotations
- ``warn_unused_ignores = true`` — flags unnecessary ``# type: ignore``
- Plugins: ``mypy_django_plugin`` (always), ``mypy_drf_plugin`` (if DRF enabled)
- Migrations are ignored via ``[[tool.mypy.overrides]]``

To run type checking::

    $ mypy .

Or via Docker::

    $ docker compose -f docker-compose.local.yml run --rm django mypy .

.. note::
   The ``django_settings_module`` in ``[tool.django-stubs]`` must point to a valid settings file for the Django plugin to work correctly.

djLint
~~~~~~

djLint lints and formats Django/Jinja2 templates for consistent HTML structure.

**Configuration** is in ``pyproject.toml`` under ``[tool.djlint]``.

Key settings:

- ``profile = "django"`` — Django template syntax
- ``indent = 2`` — 2-space indentation
- ``format_css = true``, ``format_js = true`` — formats embedded CSS/JS
- ``max_line_length = 119``

To lint templates::

    $ djlint {project_slug}/templates/

To auto-format templates::

    $ djlint --reformat {project_slug}/templates/

**Ignored rules**:

- ``H006`` — img tag without alt (handled by accessibility testing)
- ``H030``, ``H031`` — meta tag formatting
- ``T002`` — known djLint bug (see https://github.com/djlint/djLint/issues/687)

Frontend Tools
--------------

Shared Config Packages
~~~~~~~~~~~~~~~~~~~~~~

Frontend tools use a Turborepo pattern: shared configurations live in internal workspace packages under ``packages/``. This provides a single source of truth that all apps inherit.

- ``@workspace/eslint-config`` — ESLint flat configs
- ``@workspace/prettier-config`` — Prettier settings
- ``@workspace/typescript-config`` — TypeScript compiler options

Apps reference these via their ``package.json`` or config files. Changes to shared configs propagate to all workspaces automatically.

ESLint
~~~~~~

ESLint v9 with flat config format provides JavaScript/TypeScript linting.

**Shared config package**: ``packages/eslint-config/``

Four exported configurations:

- ``./base.js`` — Foundation with TypeScript + Turbo plugin
- ``./react-internal.js`` — For shared React libraries (``packages/ui``)
- ``./vite.js`` — For Vite + React applications
- ``./next-js.js`` — For Next.js applications

**Key plugins**:

- ``typescript-eslint`` — TypeScript support
- ``eslint-plugin-react`` and ``eslint-plugin-react-hooks`` — React rules
- ``eslint-plugin-react-refresh`` — Vite HMR support
- ``eslint-plugin-turbo`` — Turborepo-specific rules
- ``eslint-plugin-only-warn`` — Converts errors to warnings for DX
- ``eslint-config-prettier`` — Disables formatting rules (Prettier handles those)

To lint all workspaces::

    $ pnpm turbo lint

To auto-fix::

    $ pnpm turbo lint -- --fix

**Example usage** in an app's ``eslint.config.js``:

.. code-block:: javascript

   import { viteConfig } from "@workspace/eslint-config/vite"
   export default viteConfig

Prettier
~~~~~~~~

Prettier provides consistent code formatting across all frontend code.

**Shared config package**: ``packages/prettier-config/``

Key settings (from ``index.mjs``):

- ``tabWidth: 2``, ``useTabs: false``
- ``semi: true``, ``singleQuote: true``
- ``printWidth: 100``
- ``endOfLine: 'lf'``

**Plugins**:

- ``@trivago/prettier-plugin-sort-imports`` — Automatic import ordering
- ``prettier-plugin-tailwindcss`` — Sorts Tailwind CSS classes

**Import order** (enforced automatically):

1. ``react``
2. Third-party modules
3. ``@workspace/*`` (workspace packages)
4. ``@/*`` (app-specific aliases)
5. Relative imports (``./``, ``../``)

To format all files::

    $ pnpm format

To check without modifying::

    $ pnpm format:check

**Example usage** in an app's ``package.json``:

.. code-block:: json

   {
     "prettier": "@workspace/prettier-config"
   }

TypeScript
~~~~~~~~~~

TypeScript provides static type checking for frontend code with strict mode enabled.

**Shared config package**: ``packages/typescript-config/``

Four exported configurations:

- ``base.json`` — Foundation with strict settings
- ``react-library.json`` — For shared React packages
- ``vite-app.json`` — For Vite applications
- ``vite-node.json`` — For Node.js tooling (Vite config, etc.)

**Key settings** from ``base.json``:

- ``strict: true`` — Enables all strict type checking
- ``noUncheckedIndexedAccess: true`` — Safer array/object access
- ``target: ES2022``, ``lib: ["es2022", "DOM", "DOM.Iterable"]``
- ``skipLibCheck: true`` — Faster builds

To type check all workspaces::

    $ pnpm turbo typecheck

**Example usage** in an app's ``tsconfig.json``:

.. code-block:: json

   {
     "extends": "@workspace/typescript-config/vite-app.json",
     "compilerOptions": {
       "baseUrl": ".",
       "paths": {
         "@/*": ["./src/*"]
       }
     },
     "include": ["src"]
   }

Git Hooks with Lefthook
-----------------------

Lefthook is a fast Git hooks manager that orchestrates all code quality tools. It replaces Husky + lint-staged with better performance and simpler configuration.

**Configuration**: ``lefthook.yml``

How Lefthook Works
~~~~~~~~~~~~~~~~~~

- ``parallel: true`` — All commands run simultaneously for speed
- ``glob`` — File patterns to match (e.g., ``*.py``, ``*.{ts,tsx}``)
- ``exclude`` — Paths to skip (e.g., ``/migrations/``)
- ``stage_fixed: true`` — Auto-stages files after fixing

Only staged files are processed, not the entire codebase.

What Runs on Pre-Commit
~~~~~~~~~~~~~~~~~~~~~~~

**File Validation**:

- ``trailing-whitespace`` — Removes trailing whitespace
- ``end-of-file-fixer`` — Ensures files end with newline
- ``check-json``, ``check-toml``, ``check-yaml``, ``check-xml`` — Validates syntax
- ``debug-statements`` — Prevents committing pdb/breakpoint
- ``detect-private-key`` — Security check for leaked keys

**Python**:

- ``django-upgrade`` — Modernizes Django code to 5.0+
- ``ruff-check`` — Lints and auto-fixes Python
- ``ruff-format`` — Formats Python code
- ``mypy`` — Static type checking

**Django Templates**:

- ``djlint-reformat`` — Formats HTML templates
- ``djlint-lint`` — Lints templates

**Frontend**:

- ``turbo-typecheck`` — TypeScript checking via Turborepo
- ``turbo-lint`` — ESLint via Turborepo
- ``prettier`` — Formats JS/TS/CSS/JSON files

Manual Execution
~~~~~~~~~~~~~~~~

Run all hooks manually::

    $ lefthook run pre-commit

Skip hooks temporarily (not recommended)::

    $ git commit --no-verify

IDE Integration
---------------

Recommended VS Code extensions:

- **Python**: ``ms-python.python``, ``charliermarsh.ruff``
- **Django**: ``batisteo.vscode-django``
- **Frontend**: ``esbenp.prettier-vscode``, ``dbaeumer.vscode-eslint``

.. note::
   Use workspace settings (``.vscode/settings.json``) over global settings to ensure consistent behavior across the team.

Customization
-------------

**Python** (``pyproject.toml``):

- Add Ruff rules: modify ``[tool.ruff.lint.select]``
- Ignore rules: add to ``[tool.ruff.lint.ignore]`` or use ``# noqa: RULE`` inline
- Add mypy overrides: new ``[[tool.mypy.overrides]]`` sections

**Frontend** (``packages/*-config/``):

- ESLint: Modify files in ``packages/eslint-config/``
- Prettier: Modify ``packages/prettier-config/index.mjs``
- TypeScript: Modify files in ``packages/typescript-config/``
- App-specific overrides: Extend the base config in your app's config file

**Lefthook** (``lefthook.yml``):

- Add/remove hooks as needed
- Disable a hook temporarily: add ``skip: true`` to the command
