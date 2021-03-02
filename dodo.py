import platform
import re
import shutil
from pathlib import Path

DOIT_CONFIG = {
    "default_tasks": ["format", "test", "lint"],
    "backend": "json",
}

HERE = Path(__file__).parent


def task_format():
    """Reformat all files using black."""
    return {"actions": [["black", HERE]], "verbosity": 1}


def task_format_check():
    """Check, but not change, formatting using black."""
    return {"actions": [["black", HERE, "--check"]], "verbosity": 1}


def task_test():
    """Run Pytest with coverage."""
    return {
        "actions": ["pytest --cov=gaitmap %(paras)s"],
        "params": [{"name": "paras", "short": "p", "long": "paras", "default": ""}],
        "verbosity": 2,
    }


def task_lint():
    """Lint all files with Prospector."""
    return {"actions": [["prospector"]], "verbosity": 1}


def task_type_check():
    """Type check with mypy."""
    return {"actions": [["mypy", "-p", "gaitmap"]], "verbosity": 1}


def task_docs():
    """Build the html docs using Sphinx."""
    # Delete Autogenerated files from previous run
    shutil.rmtree(str(HERE / "docs/modules/generated"), ignore_errors=True)

    if platform.system() == "Windows":
        return {"actions": [[HERE / "docs/make.bat", "html"]], "verbosity": 2}
    else:
        return {"actions": [["make", "-C", HERE / "docs", "html"]], "verbosity": 2}


def task_register_ipykernel():
    """Add a jupyter kernel with the gaitmap env to your local install."""

    return {
        "actions": [
            ["python", "-m", "ipykernel", "install", "--user", "--name", "gaitmap", "--display-name", "gaitmap"]
        ]
    }


def update_version_strings(file_path, new_version):
    # taken from:
    # https://stackoverflow.com/questions/57108712/replace-updated-version-strings-in-files-via-python
    version_regex = re.compile(r"(^_*?version_*?\s*=\s*['\"])(\d+\.\d+\.\d+)", re.M)
    with open(file_path, "r+") as f:
        content = f.read()
        f.seek(0)
        f.write(
            re.sub(
                version_regex,
                lambda match: "{}{}".format(match.group(1), new_version),
                content,
            )
        )
        f.truncate()


def update_version(version):
    update_version_strings(HERE / "gaitmap/__init__.py", version)
    update_version_strings(HERE / "pyproject.toml", version)


def task_update_version():
    """Bump the version in pyproject.toml and gaitmap.__init__ ."""
    return {
        "actions": [(update_version,)],
        "params": [{"name": "version", "short": "v", "default": None}],
    }
