"""
Pre-commit hook to lint the generated Copier template.

Generates the template with default options, runs ruff check on the
generated project, and exits with non-zero if linting fails.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from copier import run_copy

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RESET = "\033[0m"


def _get_ruff_path() -> str:
    """Get the full path to ruff executable."""
    ruff_path = shutil.which("ruff")
    if ruff_path is None:
        print(f"{RED}ruff not found. Install with: uv sync{RESET}")
        sys.exit(1)
    return ruff_path


def main() -> int:
    """Generate template and run ruff check."""
    root_dir = Path(__file__).parent.parent
    ruff = _get_ruff_path()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        print(f"{YELLOW}Generating template with default options...{RESET}")

        # Skip post-generation hooks (dependency installation) during linting
        os.environ["COPIER_TEST_MODE"] = "1"

        try:
            run_copy(
                str(root_dir),
                str(output_dir),
                unsafe=True,
                defaults=True,
                vcs_ref="HEAD",
            )
        except (OSError, ValueError) as e:
            print(f"{RED}Error generating template: {e}{RESET}")
            return 1

        generated_dirs = list(output_dir.iterdir())
        if not generated_dirs:
            print(f"{RED}No project was generated{RESET}")
            return 1

        project_dir = output_dir
        print(f"{GREEN}Generated project in: {project_dir}{RESET}")

        # Fix import ordering first - the correct order depends on the project_slug
        # value which isn't known until generation (e.g., 'my_project' vs 'zoo_project')
        print(f"{YELLOW}Fixing import ordering...{RESET}")
        subprocess.run(  # noqa: S603
            [ruff, "check", "--select", "I", "--fix", "."],
            cwd=project_dir,
            capture_output=True,
            check=False,
        )

        print(f"{YELLOW}Running ruff check...{RESET}")

        result = subprocess.run(  # noqa: S603
            [ruff, "check", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"{RED}Ruff check failed:{RESET}")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return 1

        print(f"{GREEN}Ruff check passed!{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
