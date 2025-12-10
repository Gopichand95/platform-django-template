import os

# Skip dependency installation during tests for faster execution.
# The linting tests (ruff, djlint, django-upgrade) don't need
# dependencies installed - they just check the generated code syntax.
# Use test_docker.sh for full integration testing with dependencies.
os.environ["COOKIECUTTER_TEST_MODE"] = "1"
