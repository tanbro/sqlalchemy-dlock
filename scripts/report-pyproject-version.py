#!/usr/bin/env python3

"""Report PyProject version.

The project to report version MUST have a `pyproject.toml` file with project metadata defined in it!

If version was defined in [project] section already, print it directly.
Else if version is dynamic, it will dry-run `pip install` to re-generate version, then print it.

Environment `PYTHONUTF8` may be needed on non-western language Windows.

PyPI package `toml` is required for Python version smaller then 3.11, to install:

    pip install "toml;python_version<3.11"
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import toml as tomllib
    except ImportError as err:
        msg = dedent(
            f"""
            {err}

            You may install the library by execute:

                {sys.executable} -m pip install toml
            """
        ).lstrip()
        print(msg)
        exit(-255)

PIP_REPORT_COMMAND_FRAGMENT = [
    "pip",
    "install",
    "--disable-pip-version-check",
    "--dry-run",
    "--no-deps",
    "--ignore-installed",
    "--ignore-requires-python",
    "--quiet",
    "--report",
    "-",
]


def set_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--python",
        "-P",
        default=f"{sys.executable}",
        help="Run `pip` of this Python executable (default: %(default)s).",
    )
    parser.add_argument(
        "--pip-options",
        metavar="OPTIONS",
        help="Extra options to be supplied to the pip.",
    )
    parser.add_argument(
        "dir",
        metavar="DIR",
        nargs="?",
        default=".",
        help="Report version of the Python source code project in this directory. A pyproject.toml file MUST be in it. (default=%(default)r)",
    )
    return parser.parse_args()


def main(args):
    with Path(args.dir).joinpath("pyproject.toml").open("rb") as fp:
        pyproject = tomllib.load(fp)
    project = pyproject["project"]
    project_name = project["name"]
    try:
        project_version = project["version"]  # try find Static version
    except KeyError:
        if "version" not in project.get("dynamic", dict()):
            raise
    else:  # Print static version, then exit
        print(project_version)
        return
    # Dynamic version!
    completed_process = subprocess.run(
        (
            [args.python, "-m"]
            + PIP_REPORT_COMMAND_FRAGMENT
            + (shlex.split(args.pip_options) if args.pip_options else [])
            + ["--editable", args.dir]
        ),
        capture_output=True,
        check=True,
        text=True,
    )
    report = json.loads(completed_process.stdout)
    for package in report["install"]:
        if package["metadata"]["name"] == project_name:
            print(package["metadata"]["version"])
            break


if __name__ == "__main__":
    exit(main(set_args()))
