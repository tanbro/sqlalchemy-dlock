set -eu

SYNC_TEST_URLS="\
mysql+mysqldb://$MYSQL_USER:$MYSQL_PASSWORD@mysql/$MYSQL_DATABASE \
mysql+pymysql://$MYSQL_USER:$MYSQL_PASSWORD@mysql/$MYSQL_DATABASE \
postgresql+psycopg2://postgres:$POSTGRES_PASSWORD@postgres/ \
mssql+pyodbc://sa:$MSSQL_SA_PASSWORD@mssql:1433/master?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

ASYNC_TEST_URLS="\
mysql+aiomysql://$MYSQL_USER:$MYSQL_PASSWORD@mysql/$MYSQL_DATABASE \
mysql+asyncmy://$MYSQL_USER:$MYSQL_PASSWORD@mysql/$MYSQL_DATABASE \
postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@postgres/ \
mssql+aioodbc://sa:$MSSQL_SA_PASSWORD@mssql:1433/master?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

# Note: Database health is ensured by docker-compose healthcheck + depends_on condition
# Note: Oracle testing skipped - Oracle Database Free does NOT support DBMS_LOCK.REQUEST

export SETUPTOOLS_SCM_PRETEND_VERSION=0

PYTHON_LIST=(3.10 3.11 3.12 3.13 3.14)

REQUIRES_LIST=("SQLAlchemy[asyncio]>=1.4.3,<2" "SQLAlchemy[asyncio]>=2,<3")

DRIVER_REQUIREMENTS=(
    "mysqlclient~=2.3"
    "aiomysql~=0.3.2"
    "asyncmy~=0.2.14"
    "PyMySQL~=1.1.0"
    "psycopg2~=2.9"
    "asyncpg~=0.31"
    "pyodbc~=5.3"
    "aioodbc~=0.5"
)

TEST_ENV_DIR=""

cleanup_test_env() {
    if [[ -n "$TEST_ENV_DIR" && -d "$TEST_ENV_DIR" ]]
    then
        rm -rf -- "$TEST_ENV_DIR"
    fi
    TEST_ENV_DIR=""
}

trap cleanup_test_env EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

for PYTHON in "${PYTHON_LIST[@]}"
do
    for REQUIRES in "${REQUIRES_LIST[@]}"
    do
        echo
        echo "---------------------------------------------------------------"
        echo "Begin of ${PYTHON} ${REQUIRES}"
        echo "---------------------------------------------------------------"
        TEST_ENV_DIR=$(mktemp -d -t "sqlalchemy-dlock-test-${PYTHON}-${REQUIRES//[^a-zA-Z0-9]/-}.XXXXXXXXXX")
        uv venv --python "$PYTHON" "$TEST_ENV_DIR"
        VENV_PYTHON="$TEST_ENV_DIR/bin/python"
        test -x "$VENV_PYTHON"
        (
            set -e
            cd /workspace
            export TEST_URLS="$SYNC_TEST_URLS"
            export TEST_ASYNC_URLS="$ASYNC_TEST_URLS"
            DRIVER_REQUIREMENTS_FOR_ENV=("${DRIVER_REQUIREMENTS[@]}")
            if [[ "$REQUIRES" == *">=2"* ]]
            then
                DRIVER_REQUIREMENTS_FOR_ENV+=("psycopg[binary]~=3.2")
                export TEST_URLS="$TEST_URLS postgresql+psycopg://postgres:$POSTGRES_PASSWORD@postgres/"
                export TEST_ASYNC_URLS="$TEST_ASYNC_URLS postgresql+psycopg://postgres:$POSTGRES_PASSWORD@postgres/"
            fi
            uv pip install --python "$VENV_PYTHON" \
                . \
                coverage \
                python-dotenv \
                cryptography \
                "$REQUIRES" \
                "${DRIVER_REQUIREMENTS_FOR_ENV[@]}"
            "$VENV_PYTHON" -m coverage run -m unittest -cfv
            "$VENV_PYTHON" -m coverage report
        ) || {
            echo "Test failed for ${PYTHON} ${REQUIRES}"
            exit 1
        }
        cleanup_test_env
        echo
        echo "---------------------------------------------------------------"
        echo "End of ${PYTHON} ${REQUIRES}"
        echo "---------------------------------------------------------------"
        echo
    done
done
