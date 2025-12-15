import glob
import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

try:
    import sh
except (ImportError, ModuleNotFoundError):
    sh = None  # sh doesn't support Windows
import yaml
from binaryornot.check import is_binary
from copier import run_copy
from copier.errors import UserMessageError

# Pattern to detect unreplaced Copier/Jinja variables
PATTERN = r"\{\{\s*(\w+)\s*\}\}"
RE_OBJ = re.compile(PATTERN)

# Known valid patterns that look like Jinja but are actually valid content
VALID_PATTERNS = {
    "raw",
    "endraw",
}

if sys.platform.startswith("win"):
    pytest.skip("sh doesn't support windows", allow_module_level=True)
elif sys.platform.startswith("darwin") and os.getenv("CI"):
    pytest.skip("skipping slow macOS tests on CI", allow_module_level=True)

# Run auto-fixable styles checks - skipped on CI by default. These can be fixed
# automatically by running pre-commit after generation however they are tedious
# to fix in the template, so we don't insist too much in fixing them.
AUTOFIXABLE_STYLES = os.getenv("AUTOFIXABLE_STYLES") == "1"
auto_fixable = pytest.mark.skipif(not AUTOFIXABLE_STYLES, reason="auto-fixable")


# Smoke tests for key option combinations
# Note: Copier uses proper boolean types instead of "y"/"n" strings
SUPPORTED_COMBINATIONS = [
    {},  # defaults
    {"username_type": "email"},
    {"open_source_license": "Not open source"},
    {"open_source_license": "MIT"},
    {"open_source_license": "BSD"},
    {"open_source_license": "GPLv3"},
    {"mail_service": "Amazon SES"},
    {"mail_service": "Sendgrid"},
    {"mail_service": "Other SMTP"},
    {"use_drf": False},
    {"use_celery": True},
    {"use_sentry": True},
    {"use_heroku": True, "use_whitenoise": True},  # heroku requires whitenoise
    {"use_async": True},
    {"use_mailpit": False},
    {"use_whitenoise": False, "use_heroku": False},
    {"keep_local_envs_in_vcs": False},
    {"debug": True},
]

# Quick combinations for fast local iteration
QUICK_COMBINATIONS = [{}]  # Just defaults

# Select combinations based on environment
TEST_COMBINATIONS = QUICK_COMBINATIONS if os.getenv("QUICK_TEST") else SUPPORTED_COMBINATIONS


def _fixture_id(ctx):
    """Helper to get a user-friendly test name from the parametrized context."""
    if not ctx:
        return "defaults"
    return "-".join(f"{key}:{value}" for key, value in ctx.items())


def build_files_list(base_path: Path):
    """Build a list containing absolute paths to the generated files."""
    # Exclude directories that shouldn't be checked for Jinja variable replacement
    # - .venv, __pycache__, node_modules: build/environment artifacts
    # - turbo/generators: contains Handlebars templates with {{ }} syntax
    # - packages: may contain JSX with {{ }} object literal syntax
    excluded_dirs = {".venv", "__pycache__", "node_modules", "generators", "packages"}

    f = []
    for dirpath, subdirs, files in base_path.walk():
        subdirs[:] = [d for d in subdirs if d not in excluded_dirs]

        f.extend(dirpath / file_path for file_path in files)
    return f


def check_paths(paths: Iterable[Path]):
    """Method to check all paths have correct substitutions."""
    # Assert that no match is found in any of the files
    for path in paths:
        if is_binary(str(path)):
            continue

        content = path.read_text()
        # Look for unreplaced Jinja patterns
        for match in RE_OBJ.finditer(content):
            var_name = match.group(1)
            # Skip known valid patterns (like Django template tags in raw blocks)
            if var_name not in VALID_PATTERNS:
                # Only fail on patterns that look like our template variables
                if (var_name.islower() and "_" in var_name) or var_name in (
                    "project_name",
                    "project_slug",
                    "author_name",
                    "email",
                    "description",
                    "domain_name",
                    "version",
                    "timezone",
                ):
                    pytest.fail(f"Copier variable '{var_name}' not replaced in {path}")


def generate_project(template_path: Path, dst_path: Path, context: dict, context_override: dict) -> Path:
    """Generate a project using Copier."""
    data = {**context, **context_override}

    run_copy(
        src_path=str(template_path),
        dst_path=str(dst_path),
        data=data,
        unsafe=True,  # Skip file safety prompts
        defaults=True,  # Use defaults for missing fields
        vcs_ref="HEAD",  # Use current state
    )

    # Fix import ordering - the correct order depends on the project_slug value
    # which isn't known until generation (e.g., 'my_project' vs 'zoo_project')
    sh.ruff("check", "--select", "I", "--fix", ".", _cwd=str(dst_path))

    return dst_path


@pytest.mark.parametrize("context_override", TEST_COMBINATIONS, ids=_fixture_id)
def test_project_generation(template_path, tmp_path, context, context_override):
    """Test that project is generated and fully rendered."""
    project_path = generate_project(template_path, tmp_path, context, context_override)

    assert project_path.is_dir()

    paths = build_files_list(project_path)
    assert paths
    check_paths(paths)


@pytest.mark.parametrize("context_override", TEST_COMBINATIONS, ids=_fixture_id)
def test_ruff_check_passes(template_path, tmp_path, context, context_override):
    """Generated project should pass ruff check."""
    project_path = generate_project(template_path, tmp_path, context, context_override)

    try:
        sh.ruff("check", ".", _cwd=str(project_path))
    except sh.ErrorReturnCode as e:
        pytest.fail(e.stdout.decode())


@auto_fixable
@pytest.mark.parametrize("context_override", TEST_COMBINATIONS, ids=_fixture_id)
def test_ruff_format_passes(template_path, tmp_path, context, context_override):
    """Check whether generated project passes ruff format."""
    project_path = generate_project(template_path, tmp_path, context, context_override)

    try:
        sh.ruff(
            "format",
            ".",
            _cwd=str(project_path),
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(e.stdout.decode())


@auto_fixable
@pytest.mark.parametrize("context_override", TEST_COMBINATIONS, ids=_fixture_id)
def test_django_upgrade_passes(template_path, tmp_path, context, context_override):
    """Check whether generated project passes django-upgrade."""
    project_path = generate_project(template_path, tmp_path, context, context_override)

    python_files = [
        file_path.removeprefix(f"{project_path}/")
        for file_path in glob.glob(str(project_path / "**" / "*.py"), recursive=True)  # noqa: PTH207
    ]
    try:
        sh.django_upgrade(
            "--target-version",
            "5.0",
            *python_files,
            _cwd=str(project_path),
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(e.stdout.decode())


@pytest.mark.parametrize("context_override", TEST_COMBINATIONS, ids=_fixture_id)
def test_djlint_lint_passes(template_path, tmp_path, context, context_override):
    """Check whether generated project passes djLint --lint."""
    project_path = generate_project(template_path, tmp_path, context, context_override)

    autofixable_rules = "H014,T001"
    # TODO: remove T002 when fixed https://github.com/Riverside-Healthcare/djLint/issues/687
    ignored_rules = "H006,H030,H031,T002"
    try:
        sh.djlint(
            "--lint",
            "--ignore",
            f"{autofixable_rules},{ignored_rules}",
            ".",
            _cwd=str(project_path),
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(e.stdout.decode())


@auto_fixable
@pytest.mark.parametrize("context_override", TEST_COMBINATIONS, ids=_fixture_id)
def test_djlint_check_passes(template_path, tmp_path, context, context_override):
    """Check whether generated project passes djLint --check."""
    project_path = generate_project(template_path, tmp_path, context, context_override)

    try:
        sh.djlint("--check", ".", _cwd=str(project_path))
    except sh.ErrorReturnCode as e:
        pytest.fail(e.stdout.decode())


def test_github_invokes_linter_and_pytest(template_path, tmp_path, context):
    """Test GitHub Actions CI configuration."""
    project_path = generate_project(template_path, tmp_path, context, {})

    assert project_path.is_dir()

    with (project_path / ".github" / "workflows" / "ci.yml").open() as github_yml:
        try:
            github_config = yaml.safe_load(github_yml)
            # Verify linter job exists
            assert "linter" in github_config["jobs"]
            # Verify pytest job exists
            assert "pytest" in github_config["jobs"]
        except yaml.YAMLError as e:
            pytest.fail(str(e))


@pytest.mark.parametrize("slug", ["project slug", "Project_Slug"])
def test_invalid_slug(template_path, tmp_path, context, slug):
    """Invalid slug should fail validation."""
    context.update({"project_slug": slug})

    # Copier 9.x raises ValueError for validation errors
    with pytest.raises((UserMessageError, ValueError)):
        generate_project(template_path, tmp_path, context, {})


def test_trim_domain_email(template_path, tmp_path, context):
    """Check that leading and trailing spaces are trimmed in domain and email."""
    context.update(
        {
            "domain_name": "   example.com   ",
            "email": "  me@example.com  ",
        },
    )
    project_path = generate_project(template_path, tmp_path, context, {})

    # Check domain is trimmed in base settings
    base_settings = project_path / "config" / "settings" / "base.py"
    assert '"me@example.com"' in base_settings.read_text()


def test_pyproject_toml(template_path, tmp_path, context):
    """Test that pyproject.toml is generated correctly."""
    import tomllib  # noqa: PLC0415

    author_name = "Project Author"
    author_email = "me@example.com"
    context.update(
        {
            "description": "DESCRIPTION",
            "domain_name": "example.com",
            "email": author_email,
            "author_name": author_name,
        },
    )
    project_path = generate_project(template_path, tmp_path, context, {})

    pyproject_toml = project_path / "pyproject.toml"

    data = tomllib.loads(pyproject_toml.read_text())

    assert data
    assert data["project"]["authors"][0]["email"] == author_email
    assert data["project"]["authors"][0]["name"] == author_name
    assert data["project"]["name"] == context["project_slug"]
