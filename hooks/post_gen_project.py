# ruff: noqa: PLR0133
import os
import random
import shutil
import string
import subprocess
import sys
from pathlib import Path

try:
    # Inspired by
    # https://github.com/django/django/blob/main/django/utils/crypto.py
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


def remove_open_source_files():
    file_names = ["CONTRIBUTORS.txt", "LICENSE"]
    for file_name in file_names:
        Path(file_name).unlink()


def remove_gplv3_files():
    file_names = ["COPYING"]
    for file_name in file_names:
        Path(file_name).unlink()


def remove_custom_user_manager_files():
    users_path = Path("{{cookiecutter.project_slug}}", "users")
    (users_path / "managers.py").unlink()
    (users_path / "tests" / "test_managers.py").unlink()


def remove_celery_files():
    file_paths = [
        Path("config", "celery_app.py"),
        Path("{{ cookiecutter.project_slug }}", "users", "tasks.py"),
        Path("{{ cookiecutter.project_slug }}", "users", "tests", "test_tasks.py"),
    ]
    for file_path in file_paths:
        file_path.unlink()


def remove_async_files():
    file_paths = [
        Path("config", "asgi.py"),
        Path("config", "websocket.py"),
    ]
    for file_path in file_paths:
        file_path.unlink()


def remove_celery_compose_dirs():
    shutil.rmtree(Path("compose", "local", "django", "celery"))
    shutil.rmtree(Path("compose", "production", "django", "celery"))


def remove_heroku_files():
    file_names = ["Procfile"]
    for file_name in file_names:
        Path(file_name).unlink()
    shutil.rmtree("bin")


def remove_drf_starter_files():
    Path("config", "api_router.py").unlink()
    shutil.rmtree(Path("{{cookiecutter.project_slug}}", "users", "api"))
    shutil.rmtree(Path("{{cookiecutter.project_slug}}", "users", "tests", "api"))


def remove_openapi_config():
    """Remove OpenAPI client generation config when DRF is not used."""
    openapi_config = Path("apps", "{{ cookiecutter.project_slug }}", "openapi-ts.config.ts")
    if openapi_config.exists():
        openapi_config.unlink()


def generate_random_string(length, using_digits=False, using_ascii_letters=False, using_punctuation=False):  # noqa: FBT002
    """
    Example:
        opting out for 50 symbol-long, [a-z][A-Z][0-9] string
        would yield log_2((26+26+50)^50) ~= 334 bit strength.
    """
    if not using_sysrandom:
        return None

    symbols = []
    if using_digits:
        symbols += string.digits
    if using_ascii_letters:
        symbols += string.ascii_letters
    if using_punctuation:
        all_punctuation = set(string.punctuation)
        # These symbols can cause issues in environment variables
        unsuitable = {"'", '"', "\\", "$"}
        suitable = all_punctuation.difference(unsuitable)
        symbols += "".join(suitable)
    return "".join([random.choice(symbols) for _ in range(length)])


def generate_random_user():
    return generate_random_string(length=32, using_ascii_letters=True)


def set_flag(file_path: Path, flag, value=None, formatted=None, *args, **kwargs):
    if value is None:
        random_string = generate_random_string(*args, **kwargs)
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


def generate_env_file(debug=False):  # noqa: FBT002
    """Generate .env from .env.example with random secrets."""
    env_example = Path(".env.example")
    env_file = Path(".env")

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
    if "{{ cookiecutter.use_celery }}".lower() == "y":
        flower_user = DEBUG_VALUE if debug else generate_random_user()
        flower_password = (
            DEBUG_VALUE if debug else generate_random_string(length=64, using_digits=True, using_ascii_letters=True)
        )
        set_flag(env_file, "!!!SET CELERY_FLOWER_USER!!!", value=flower_user)
        set_flag(env_file, "!!!SET CELERY_FLOWER_PASSWORD!!!", value=flower_password)


def set_flags_in_settings_files():
    set_flag(
        Path("config", "settings", "local.py"),
        "!!!SET DJANGO_SECRET_KEY!!!",
        length=64,
        using_digits=True,
        using_ascii_letters=True,
    )
    set_flag(
        Path("config", "settings", "test.py"),
        "!!!SET DJANGO_SECRET_KEY!!!",
        length=64,
        using_digits=True,
        using_ascii_letters=True,
    )


def append_to_gitignore_file(ignored_line):
    with Path(".gitignore").open("a") as gitignore_file:
        gitignore_file.write(ignored_line)
        gitignore_file.write("\n")


def setup_python_dependencies():
    """Install Python dependencies using uv."""
    print("Installing python dependencies using uv...")

    # Build a trimmed down Docker image to run uv
    uv_docker_image_path = Path("docker/local/uv/Dockerfile")
    uv_image_tag = "cookiecutter-django-uv-runner:latest"
    try:
        subprocess.run(  # noqa: S603
            [  # noqa: S607
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
        print(f"Error building Docker image: {e}", file=sys.stderr)
        sys.exit(1)

    current_path = Path.cwd().absolute()
    # Use Docker to run the uv command
    uv_cmd = ["docker", "run", "--rm", "-v", f"{current_path}:/app", uv_image_tag, "uv"]

    # Install production dependencies
    try:
        subprocess.run([*uv_cmd, "add", "--no-sync", "-r", "requirements/production.txt"], check=True)  # noqa: S603
    except subprocess.CalledProcessError as e:
        print(f"Error installing production dependencies: {e}", file=sys.stderr)
        sys.exit(1)

    # Install local (development) dependencies
    try:
        subprocess.run([*uv_cmd, "add", "--no-sync", "--dev", "-r", "requirements/local.txt"], check=True)  # noqa: S603
    except subprocess.CalledProcessError as e:
        print(f"Error installing local dependencies: {e}", file=sys.stderr)
        sys.exit(1)

    # Remove the requirements directory
    requirements_dir = Path("requirements")
    if requirements_dir.exists():
        try:
            shutil.rmtree(requirements_dir)
        except Exception as e:  # noqa: BLE001
            print(f"Error removing 'requirements' folder: {e}", file=sys.stderr)
            sys.exit(1)

    # Remove the uv Docker image directory
    uv_image_parent_dir_path = Path("docker/local/uv")
    if uv_image_parent_dir_path.exists():
        shutil.rmtree(str(uv_image_parent_dir_path))

    print("Python dependencies installed!")


def install_pnpm_dependencies():
    """Install frontend dependencies using pnpm."""
    print("Installing frontend dependencies using pnpm...")

    # Check if pnpm is available
    try:
        subprocess.run(["pnpm", "--version"], check=True, capture_output=True)  # noqa: S607
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(WARNING + "pnpm is not installed. Please install pnpm to set up frontend dependencies." + TERMINATOR)
        print(HINT + "Install with: npm install -g pnpm" + TERMINATOR)
        return

    try:
        subprocess.run(["pnpm", "install"], check=True)  # noqa: S607
        print("Frontend dependencies installed!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing frontend dependencies: {e}", file=sys.stderr)


def main():
    debug = "{{ cookiecutter.debug }}".lower() == "y"

    # Generate .env file with secrets
    generate_env_file(debug=debug)
    set_flags_in_settings_files()

    # License handling
    if "{{ cookiecutter.open_source_license }}" == "Not open source":
        remove_open_source_files()
    if "{{ cookiecutter.open_source_license}}" != "GPLv3":
        remove_gplv3_files()

    # Username type handling
    if "{{ cookiecutter.username_type }}" == "username":
        remove_custom_user_manager_files()

    # Celery handling
    if "{{ cookiecutter.use_celery }}".lower() == "n":
        remove_celery_files()
        remove_celery_compose_dirs()

    # DRF handling
    if "{{ cookiecutter.use_drf }}".lower() == "n":
        remove_drf_starter_files()
        remove_openapi_config()

    # Async handling
    if "{{ cookiecutter.use_async }}".lower() == "n":
        remove_async_files()

    # Heroku handling
    if "{{ cookiecutter.use_heroku }}".lower() == "n":
        remove_heroku_files()

    # Update .gitignore for .env
    append_to_gitignore_file(".env")
    if "{{ cookiecutter.keep_local_envs_in_vcs }}".lower() == "y":
        append_to_gitignore_file("!.env.example")

    # Install dependencies (skip in test mode for faster tests)
    if not os.getenv("COOKIECUTTER_TEST_MODE"):
        setup_python_dependencies()
        install_pnpm_dependencies()

    print(SUCCESS + "Project initialized, keep up the good work!" + TERMINATOR)


if __name__ == "__main__":
    main()
