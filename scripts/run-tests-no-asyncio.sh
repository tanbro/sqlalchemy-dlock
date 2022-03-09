#!/usr/bin/env bash

# 用于在 Docker 中运行测试:
# eg:
# docker run -it --rm -v "$(pwd):/work" -w /work --env-file .env python /bin/bash /work/tools/run-tests.sh

set -e

export TEST_NO_ASYNCIO=1

python -m venv /opt/venv
/opt/venv/bin/pip install -U pip setuptools wheel $(if [ -n "${PYPI_INDEX_URL}" ]; then echo "-i ${PYPI_INDEX_URL}"; fi)
if [ -n "${PYPI_INDEX_URL}" ] ; then
    /opt/venv/bin/pip config --site set global.index-url ${PYPI_INDEX_URL} ;
fi
/opt/venv/bin/pip install -U . pytest -r requires/test-no-asyncio.txt
/opt/venv/bin/pytest
