#!/usr/bin/env bash

# Python unittest running script for the docker-compose tests.
# DO NOT run it alone.

set -e

python -m pip install -U -e /workspace[asyncio] -r /workspace/tests/requirements.txt $(printenv SQLALCHEMY_REQUIRES)

/bin/bash scripts/wait-for-postgres.sh postgres test
/bin/bash scripts/wait-for-mysql.sh mysql test test test

python -m unittest -cfv $(printenv TEST_TESTS)
