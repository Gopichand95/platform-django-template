#!/usr/bin/env python
"""
Post-generation script for Copier template.
Handles secret generation, settings configuration, and dependency installation.

This script is called as a Copier task after template generation.
It reads context from the .copier-answers.yml file in the destination directory.
"""

import os
import random
import shutil
import string
import subprocess
import sys
from pathlib import Path

import yaml

try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    using_sysrandom = False

TERMINATOR = "\x1b[0m"
WARNING = "\x1b[1;33m [WARNING]: "
INFO = "\x1b[1;33m [INFO]: "
HINT = "\x1b[3;33m"
SUCCESS = "\x1b[1;32m [SUCCESS]: "

DEBUG_VALUE = "debug"


def load_copier_answers() -> dict:
    """Load answers from .copier-answers.yml"""
    answers_file = Path(".copier-answers.yml")
    if not answers_file.exists():
        print(WARNING + "No .copier-answers.yml found, using defaults" + TERMINATOR)
        return {}

    with answers_file.open() as f:
        return yaml.safe_load(f) or {}


def generate_random_string(
    length: int,
    using_digits: bool = False,
    using_ascii_letters: bool = False,
    using_punctuation: bool = False,
) -> str | None:
    """
    Generate a random string for secrets.

    Example:
        opting out for 50 symbol-long, [a-z][A-Z][0-9] string
        would yield log_2((26+26+50)^50) ~= 334 bit strength.
    """
    if not using_sysrandom:
        return None

    symbols = []
    if using_digits:
        symbols += list(string.digits)
    if using_ascii_letters:
        symbols += list(string.ascii_letters)
    if using_punctuation:
        all_punctuation = set(string.punctuation)
        # These symbols can cause issues in environment variables
        unsuitable = {"'", '"', "\\", "$"}
        suitable = all_punctuation.difference(unsuitable)
        symbols += list(suitable)
    return "".join([random.choice(symbols) for _ in range(length)])


def generate_random_user() -> str | None:
    return generate_random_string(length=32, using_ascii_letters=True)


def set_flag(file_path: Path, flag: str, value: str | None = None, formatted: str | None = None, **kwargs) -> str:
    """Replace a flag placeholder in a file with a value or random string."""
    if value is None:
        random_string = generate_random_string(**kwargs)
        if random_string is None:
            print(
                "We couldn't find a secure pseudo-random number generator on your "
                f"system. Please, make sure to manually {flag} later.",
            )
            random_string = flag
        if formatted is not None:
            random_string = formatted.format(random_string)
        value = random_string

    with file_path.open("r+") as f:
        file_contents = f.read().replace(flag, value)
        f.seek(0)
        f.write(file_contents)
        f.truncate()

    return value


def generate_env_file(debug: bool = False, use_celery: bool = False):
    """Generate .env from .env.example with random secrets."""
    env_example = Path(".env.example")
    env_file = Path(".env")

    if not env_example.exists():
        print(WARNING + ".env.example not found, skipping .env generation" + TERMINATOR)
        return

    # Copy .env.example to .env
    shutil.copy(env_example, env_file)

    # Generate values
    postgres_user = DEBUG_VALUE if debug else generate_random_user()
    postgres_password = (
        DEBUG_VALUE if debug else generate_random_string(length=64, using_digits=True, using_ascii_letters=True)
    )
    django_secret_key = generate_random_string(length=64, using_digits=True, using_ascii_letters=True)
    django_admin_url = generate_random_string(length=32, using_digits=True, using_ascii_letters=True)

    # Set values in .env file
    set_flag(env_file, "!!!SET POSTGRES_USER!!!", value=postgres_user)
    set_flag(env_file, "!!!SET POSTGRES_PASSWORD!!!", value=postgres_password)
    set_flag(env_file, "!!!SET DJANGO_SECRET_KEY!!!", value=django_secret_key)
    set_flag(env_file, "!!!SET DJANGO_ADMIN_URL!!!", value=f"{django_admin_url}/")

    # Set Celery Flower credentials if Celery is enabled
    if use_celery:
        flower_user = DEBUG_VALUE if debug else generate_random_user()
        flower_password = (
            DEBUG_VALUE if debug else generate_random_string(length=64, using_digits=True, using_ascii_letters=True)
        )
        set_flag(env_file, "!!!SET CELERY_FLOWER_USER!!!", value=flower_user)
        set_flag(env_file, "!!!SET CELERY_FLOWER_PASSWORD!!!", value=flower_password)


def set_flags_in_settings_files():
    """Set Django secret keys in local and test settings."""
    for settings_file in ["local.py", "test.py"]:
        file_path = Path("config", "settings", settings_file)
        if file_path.exists():
            set_flag(
                file_path,
                "!!!SET DJANGO_SECRET_KEY!!!",
                length=64,
                using_digits=True,
                using_ascii_letters=True,
            )


def append_to_gitignore_file(ignored_line: str):
    """Append a line to .gitignore."""
    gitignore = Path(".gitignore")
    if gitignore.exists():
        with gitignore.open("a") as f:
            f.write(ignored_line)
            f.write("\n")


def setup_python_dependencies():
    """Install Python dependencies using uv via Docker."""
    print(INFO + "Installing Python dependencies using uv..." + TERMINATOR)

    uv_docker_image_path = Path("docker/local/uv/Dockerfile")
    if not uv_docker_image_path.exists():
        print(WARNING + "uv Dockerfile not found, skipping Python dependency installation" + TERMINATOR)
        return

    uv_image_tag = "copier-turbo-django-uv-runner:latest"
    try:
        subprocess.run(
            [
                "docker",
                "build",
                "--load",
                "-t",
                uv_image_tag,
                "-f",
                str(uv_docker_image_path),
                "-q",
                ".",
            ],
            check=True,
            env={
                **os.environ,
                "DOCKER_BUILDKIT": "1",
            },
        )
    except subprocess.CalledProcessError as e:
        print(WARNING + f"Error building Docker image: {e}" + TERMINATOR)
        return
    except FileNotFoundError:
        print(WARNING + "Docker not found, skipping Python dependency installation" + TERMINATOR)
        return

    current_path = Path.cwd().absolute()
    uv_cmd = ["docker", "run", "--rm", "-v", f"{current_path}:/app", uv_image_tag, "uv"]

    # Install production dependencies
    try:
        subprocess.run([*uv_cmd, "add", "--no-sync", "-r", "requirements/production.txt"], check=True)
    except subprocess.CalledProcessError as e:
        print(WARNING + f"Error installing production dependencies: {e}" + TERMINATOR)
        return

    # Install local (development) dependencies
    try:
        subprocess.run([*uv_cmd, "add", "--no-sync", "--dev", "-r", "requirements/local.txt"], check=True)
    except subprocess.CalledProcessError as e:
        print(WARNING + f"Error installing local dependencies: {e}" + TERMINATOR)
        return

    # Remove the requirements directory
    requirements_dir = Path("requirements")
    if requirements_dir.exists():
        shutil.rmtree(requirements_dir)

    # Remove the uv Docker image directory
    uv_image_parent_dir_path = Path("docker/local/uv")
    if uv_image_parent_dir_path.exists():
        shutil.rmtree(str(uv_image_parent_dir_path))

    print(SUCCESS + "Python dependencies installed!" + TERMINATOR)


def install_pnpm_dependencies():
    """Install frontend dependencies using pnpm."""
    print(INFO + "Installing frontend dependencies using pnpm..." + TERMINATOR)

    try:
        subprocess.run(["pnpm", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(WARNING + "pnpm is not installed. Please install pnpm to set up frontend dependencies." + TERMINATOR)
        print(HINT + "Install with: npm install -g pnpm" + TERMINATOR)
        return

    try:
        subprocess.run(["pnpm", "install"], check=True)
        print(SUCCESS + "Frontend dependencies installed!" + TERMINATOR)
    except subprocess.CalledProcessError as e:
        print(WARNING + f"Error installing frontend dependencies: {e}" + TERMINATOR)


def fix_python_formatting():
    """Run ruff to fix Python import ordering after template generation.

    Import order depends on the project_slug value which isn't known until generation.
    For example, 'my_project' comes before 'rest_framework' alphabetically,
    but 'zoo_project' comes after.
    """
    print(INFO + "Fixing Python import ordering with ruff..." + TERMINATOR)

    try:
        subprocess.run(["ruff", "check", "--select", "I", "--fix", "."], check=True, capture_output=True)
        print(SUCCESS + "Python import ordering fixed!" + TERMINATOR)
    except subprocess.CalledProcessError:
        # Ruff might not be installed yet, try with uvx
        try:
            subprocess.run(["uvx", "ruff", "check", "--select", "I", "--fix", "."], check=True, capture_output=True)
            print(SUCCESS + "Python import ordering fixed!" + TERMINATOR)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(WARNING + "Could not run ruff. Run 'ruff check --fix .' manually." + TERMINATOR)
    except FileNotFoundError:
        print(WARNING + "ruff not found. Run 'ruff check --fix .' manually." + TERMINATOR)


def fix_frontend_formatting():
    """Run prettier to format frontend code after template generation."""
    print(INFO + "Formatting frontend code with prettier..." + TERMINATOR)

    try:
        subprocess.run(["pnpm", "format"], check=True, capture_output=True)
        print(SUCCESS + "Frontend code formatted!" + TERMINATOR)
    except subprocess.CalledProcessError as e:
        print(WARNING + f"Could not run prettier: {e}. Run 'pnpm format' manually." + TERMINATOR)
    except FileNotFoundError:
        print(WARNING + "pnpm not found. Run 'pnpm format' manually." + TERMINATOR)


def main():
    # Load answers from Copier
    answers = load_copier_answers()

    debug = answers.get("debug", False)
    use_celery = answers.get("use_celery", True)
    keep_local_envs_in_vcs = answers.get("keep_local_envs_in_vcs", False)

    # Generate .env file with secrets
    generate_env_file(debug=debug, use_celery=use_celery)
    set_flags_in_settings_files()

    # Update .gitignore for .env
    append_to_gitignore_file(".env")
    if keep_local_envs_in_vcs:
        append_to_gitignore_file("!.env.example")

    # Install dependencies and run formatters (skip if COPIER_TEST_MODE is set)
    if not os.getenv("COPIER_TEST_MODE"):
        setup_python_dependencies()
        install_pnpm_dependencies()
        fix_python_formatting()
        fix_frontend_formatting()

    print(SUCCESS + "Project initialized, keep up the good work!" + TERMINATOR)


if __name__ == "__main__":
    main()
