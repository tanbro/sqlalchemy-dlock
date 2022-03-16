#!/usr/bin/env bash

set -e

ENV_DIR="$(mktemp -d)"
trap '{ rm -fr "${ENV_DIR}" ; }' EXIT

python -m venv ${ENV_DIR}

${ENV_DIR}/bin/pip install -U --no-cache-dir pip setuptools wheel \
$(if [ -n "${PYPI_INDEX_URL}" ] ; then echo "-i ${PYPI_INDEX_URL}" ; fi)

if [ -n "${PYPI_INDEX_URL}" ] ; then
    ${ENV_DIR}/bin/pip config --site set global.index-url ${PYPI_INDEX_URL} ;
fi

${ENV_DIR}/bin/pip install -U --no-cache-dir \
.$(if [ -z "${NO_ASYNCIO}" ] ; then echo "[asyncio]" ; fi) \
pytest pytest-cov \
-r $(if [ -n "${NO_ASYNCIO}" ] ; then echo "requires/test-no-asyncio.txt" ; else echo "requires/test.txt" ; fi)

${ENV_DIR}/bin/pytest -o cache_dir=/tmp/pytest_cache --no-cov-on-fail --cov=sqlalchemy_dlock
