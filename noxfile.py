import nox

PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run unit tests with pytest."""
    session.install(".")  # Install the package
    session.install("pytest")  # Install testing dependencies
    session.run("pytest")


@nox.session(python=PYTHON_VERSIONS)
def mypy(session):
    """Run mypy for static type checking."""
    session.install(".")  # Install the package
    session.install("mypy")  # Install mypy
    session.run("mypy", "openpuc_scrapers")


@nox.session(python="3.11")  # Use a single Python version for linting
def lint(session):
    """Run Ruff for linting and formatting."""
    session.install("ruff")
    session.run("ruff", "check", "openpuc_scrapers")
