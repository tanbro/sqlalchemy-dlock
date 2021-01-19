#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pkg_resources import parse_requirements
from setuptools import setup

SETUP_REQUIRES = [
    'setuptools_scm', 'setuptools_scm_git_archive'
]

INSTALL_REQUIRES = [
    str(x) for x in parse_requirements(open('requirements.txt'))
]
TESTS_REQUIRES = [
    str(x) for x in parse_requirements(open('requires/tests.txt'))
]

setup(
    setup_requires=SETUP_REQUIRES,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRES,
    use_scm_version={
        # guess-next-dev:	automatically guesses the next development version (default)
        # post-release:	generates post release versions (adds postN)
        'version_scheme': 'guess-next-dev',
        'write_to': 'src/sqlalchemy_dlock/version.py',
    },
)
