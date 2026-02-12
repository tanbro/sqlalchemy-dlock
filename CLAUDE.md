# sqlalchemy-dlock

A distributed lock implementation based on SQLAlchemy.

## Commands

### Development
```bash
# Install with all dependency groups
uv sync --all

# Install with specific groups
uv sync --group test
uv sync --group typecheck
uv sync --group docs

# Run tests (requires databases running)
python -m unittest

# Type checking
uv run --no-dev mypy

# Linting and formatting
ruff check .
ruff format .

# Build package
uv build
```

### Testing with Docker
```bash
# Start test databases (MySQL, PostgreSQL, MSSQL, Oracle)
docker compose -f db.docker-compose.yml up

# Run full test matrix across Python and SQLAlchemy versions
cd tests
docker compose up --abort-on-container-exit
```

> **Note:** Oracle testing requires **Oracle Database Enterprise/Standard Edition**. Oracle Database Free (23c/23ai) does NOT support `DBMS_LOCK.REQUEST` which is required for distributed lock functionality. This is a fundamental limitation of the Free/Express edition, not related to the container image flavor.

For local Oracle testing, ensure you have a full Oracle Database installation or use the official Oracle image:
```bash
docker compose -f db.docker-compose.yml up
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Architecture

**Entry Points:** `create_sadlock()`, `create_async_sadlock()` in [factory.py](src/sqlalchemy_dlock/factory.py)

**Factory Pattern:**
1. Inspect SQLAlchemy engine name from connection/session
2. Look up lock class in [registry.py](src/sqlalchemy_dlock/registry.py) (`REGISTRY` for sync, `ASYNCIO_REGISTRY` for async)
3. Instantiate database-specific lock implementation

**Key Directories:**
- [lock/](src/sqlalchemy_dlock/lock/) - Database-specific lock implementations
  - [base.py](src/sqlalchemy_dlock/lock/base.py) - `BaseSadLock` (sync), `BaseAsyncSadLock` (async)
  - [mysql.py](src/sqlalchemy_dlock/lock/mysql.py) - MySQL/MariaDB named locks
  - [postgresql.py](src/sqlalchemy_dlock/lock/postgresql.py) - PostgreSQL advisory locks
  - [mssql.py](src/sqlalchemy_dlock/lock/mssql.py) - MSSQL application locks
  - [oracle.py](src/sqlalchemy_dlock/lock/oracle.py) - Oracle user locks
- [statement/](src/sqlalchemy_dlock/statement/) - SQL statement templates for each database
- [registry.py](src/sqlalchemy_dlock/registry.py) - Engine name to lock class mapping

**Test Structure:**
- [tests/](tests/) - Synchronous tests
- [tests/asyncio/](tests/asyncio/) - Asynchronous tests
- [tests/engines.py](tests/engines.py) - Test database connection factory

## Gotchas

### Critical
- **Thread-local locks:** `BaseSadLock` extends `threading.local` - lock objects CANNOT be safely passed between threads. Each thread must create its own lock instance.
- **MySQL re-entrant behavior:** MySQL allows acquiring the same named lock multiple times on the same connection. This is NOT true mutual exclusion.
- **Lock lifetime:** Locks are tied to database connections. Closing a connection releases all associated locks.

### Database-Specific
- **Key hashing:** PostgreSQL and Oracle convert string keys to 64-bit integers via BLAKE2b hash.
- **PostgreSQL timeout:** Implemented through polling, may have ~1 second variance.
- **Oracle lock ID range:** 0-1073741823 (uses `DBMS_LOCK.REQUEST`)
- **Oracle Free limitation:** Oracle Database Free (23c/23ai) does NOT support `DBMS_LOCK.REQUEST`. This is a fundamental limitation of the Free/Express edition. CI skips Oracle tests; test locally with `docker compose -f db.docker-compose.yml up` which uses the official Oracle image.
- **MSSQL driver:** Requires ODBC driver installation (`msodbcsql18` on Ubuntu)

### Resource Requirements
- **MSSQL container:** Requires at least 2GB RAM
- **Oracle container:** Requires at least 2GB RAM

### API Notes
- `contextual_timeout` parameter ONLY affects `with` statements, not direct `acquire()` calls
- Async lock classes are separate (`*AsyncSadLock`) but defined in same modules as sync variants

## Environment

**Python:** 3.9+ (CI tests 3.10-3.14)

**Testing Databases:** Optional Docker services in [db.docker-compose.yml](db.docker-compose.yml)
- MySQL: `mysql://test:test@127.0.0.1:3306/test`
- PostgreSQL: `postgresql://postgres:test@127.0.0.1:5432/`
- MSSQL: `mssql+pyodbc://sa:YourStrongPassword123@127.0.0.1:1433/master`
- Oracle: `oracle+oracledb://sys:YourStrong@Passw0rd@127.0.0.1:1521/?service_name=FREEPDB1`

**Environment Variables:** Test URLs can be set via `TEST_URLS` and `TEST_ASYNC_URLS`, or loaded from `tests/.env`

## Code Style

- **Formatter:** Ruff (line length: 128)
- **Linter:** Ruff with import sorting (`I`)
- **Type checker:** mypy
- **Source layout:** `src/` directory with setuptools
- **Config:** [.ruff.toml](.ruff.toml), [.mypy.ini](.mypy.ini)

## Workflow

When adding support for a new database:
1. Create lock implementation in [lock/](src/sqlalchemy_dlock/lock/) inheriting from `BaseSadLock` / `BaseAsyncSadLock`
2. Create SQL templates in [statement/](src/sqlalchemy_dlock/statement/)
3. Add entry to `REGISTRY` and `ASYNCIO_REGISTRY` in [registry.py](src/sqlalchemy_dlock/registry.py)
4. Add tests in [tests/](tests/) and [tests/asyncio/](tests/asyncio/)
5. Update [db.docker-compose.yml](db.docker-compose.yml) if testing locally
