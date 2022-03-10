#!/usr/bin/env bash

# 用于在 Docker 中运行测试:
# eg:
# docker run -it --rm -v "$(pwd):/work" -w /work --env-file .env python /bin/bash /work/scripts/run-tests.sh

set -e

VENV="$(mktemp -d)"
trap '{ rm -fr "${VENV}" ; }' EXIT

python -m venv ${VENV}

${VENV}/bin/pip install -U --no-cache-dir pip setuptools wheel $(if [ -n "${PYPI_INDEX_URL}" ]; then echo "-i ${PYPI_INDEX_URL}"; fi)
if [ -n "${PYPI_INDEX_URL}" ] ; then
    ${VENV}/bin/pip config --site set global.index-url ${PYPI_INDEX_URL} ;
fi

${VENV}/bin/pip install -U --no-cache-dir .$(if [ -n "${NO_ASYNCIO}" ]; then echo "[asyncio]"; fi) pytest -r $(if [ -n "${NO_ASYNCIO}" ]; then echo "requires/test-no-asyncio.txt"; else echo "requires/test.txt" ; fi)

${VENV}/bin/pytest
