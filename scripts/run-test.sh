set -eu

export TEST_URLS="mysql://$MYSQL_USER:$MYSQL_PASSWORD@mysql/$MYSQL_DATABASE postgresql://postgres:$POSTGRES_PASSWORD@postgres/"
export TEST_ASYNC_URLS="mysql+aiomysql://$MYSQL_USER:$MYSQL_PASSWORD@mysql/$MYSQL_DATABASE postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@postgres/"

/bin/bash scripts/wait-for-postgres.sh postgres $POSTGRES_PASSWORD
/bin/bash scripts/wait-for-mysql.sh mysql $MYSQL_DATABASE $MYSQL_USER $MYSQL_PASSWORD

export SETUPTOOLS_SCM_PRETEND_VERSION=0
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_ROOT_USER_ACTION=ignore
export PIP_NO_WARN_SCRIPT_LOCATION=1

PYTHON_LIST=(python3.9 python3.10 python3.11 python3.12 python3.13 python3.14)
REQUIRES_LIST=("SQLAlchemy[asyncio]>=1.4.3,<2" "SQLAlchemy[asyncio]>=2,<3")

trap 'rm -rf /tmp/sqlalchemy-dlock-test-*' EXIT

for PYTHON in ${PYTHON_LIST[@]}
do
    for REQUIRES in ${REQUIRES_LIST[@]}
    do
        echo
        echo "---------------------------------------------------------------"
        echo "Begin of ${PYTHON} ${REQUIRES}"
        echo "---------------------------------------------------------------"
        echo
        TMPDIR=$(mktemp -d -t sqlalchemy-dlock-test-${PYTHON}-${REQUIRES//[^a-zA-Z0-9]/-})
        (
            set -e
            cd /workspace
            $TMPDIR/bin/python -m pip install -e . cryptography $REQUIRES
            $TMPDIR/bin/python -m pip install mysqlclient aiomysql psycopg2 asyncpg
            $TMPDIR/bin/python -m coverage run -m unittest -cfv
            $TMPDIR/bin/python -m coverage report
        ) || {
            echo "Test failed for ${PYTHON} ${REQUIRES}"
            exit 1
        }
        rm -rf $TMPDIR
        echo
        echo "---------------------------------------------------------------"
        echo "End of ${PYTHON} ${REQUIRES}"
        echo "---------------------------------------------------------------"
        echo
    done
done
