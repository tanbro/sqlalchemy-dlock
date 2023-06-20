#!/usr/bin/env bash

set -e

ENV_DIR="$(mktemp -d)"
trap "{ echo 'Remove virtual Python environment ${ENV_DIR}'; rm -fr ${ENV_DIR}; }" EXIT

echo "Create virtual Python environment ${ENV_DIR}"
python -m venv ${ENV_DIR}

${ENV_DIR}/bin/pip install -U --no-cache-dir .[asyncio] pytest pytest-cov -r tests/requirements.txt

${ENV_DIR}/bin/pytest -o cache_dir=/tmp/pytest_cache --no-cov-on-fail --cov=sqlalchemy_dlock
