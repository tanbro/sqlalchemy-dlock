#!/bin/sh

set -e

ENV_DIR="$(mktemp -d)"
trap "{ echo 'Remove virtual Python environment ${ENV_DIR}'; rm -fr ${ENV_DIR}; }" EXIT

echo "Create virtual Python environment ${ENV_DIR}"
python -m venv ${ENV_DIR}

${ENV_DIR}/bin/pip install -U --no-cache-dir \
.$(if [ -z "${NO_ASYNCIO}" ]; then echo "[asyncio]"; fi) \
pytest pytest-cov \
$(if [ -n "${NO_ASYNCIO}" ]; then echo "-r requires/test-no-asyncio.txt"; else echo "-r requires/test.txt"; fi)

${ENV_DIR}/bin/pytest -o cache_dir=/tmp/pytest_cache --no-cov-on-fail --cov=sqlalchemy_dlock
