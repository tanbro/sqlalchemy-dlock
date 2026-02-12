# sqlalchemy-dlock

[![CI](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml/badge.svg)](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml)
[![GitHub Release](https://img.shields.io/github/v/release/tanbro/sqlalchemy-dlock)](https://github.com/tanbro/sqlalchemy-dlock/releases)
[![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-dlock)](https://pypi.org/project/sqlalchemy-dlock/)
[![Documentation Status](https://readthedocs.org/projects/sqlalchemy-dlock/badge/?version=latest)](https://sqlalchemy-dlock.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/tanbro/sqlalchemy-dlock/branch/main/graph/badge.svg)](https://codecov.io/gh/tanbro/sqlalchemy-dlock)
[![License](https://img.shields.io/pypi/l/sqlalchemy-dlock)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A distributed lock library based on databases and [SQLAlchemy][].

sqlalchemy-dlock provides distributed locking capabilities using your existing database infrastructure—no additional services like Redis or ZooKeeper required. It currently supports:

| Database   | Lock Mechanism                                                                                                                                 |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| MySQL      | [Named Lock](https://dev.mysql.com/doc/refman/en/locking-functions.html) (`GET_LOCK` / `RELEASE_LOCK`)                                         |
| MariaDB    | [Named Lock](https://mariadb.com/kb/en/get_lock/) (compatible with MySQL)                                                                      |
| MSSQL      | [Application Lock](https://learn.microsoft.com/sql/relational-databases/system-stored-procedures/sp-getapplock-transact-sql) (`sp_getapplock`) |
| Oracle     | [User Lock](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_LOCK.html) (`DBMS_LOCK`) |
| PostgreSQL | [Advisory Lock](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS) |

> ⚠️ **Oracle Not Tested:**
> Oracle Database Free (23c/23ai) does NOT support `DBMS_LOCK.REQUEST`. We do NOT test Oracle in CI or integration tests. Use with Oracle Enterprise/Standard Edition at your own risk.

---

## Why sqlalchemy-dlock?

**Distributed locks** coordinate access to shared resources across multiple processes or servers. Here's how database-based locking compares to other approaches:

| Solution          | Pros                                          | Cons                                                | Best For                             |
| ----------------- | --------------------------------------------- | --------------------------------------------------- | ------------------------------------ |
| **Redis**         | High performance                              | Additional infrastructure, consistency complexities | High-throughput scenarios            |
| **ZooKeeper**     | Strong consistency                            | Complex deployment, high operational cost           | Financial/mission-critical systems   |
| **Database Lock** | Zero additional dependencies, ACID guarantees | Lower performance than in-memory solutions          | Applications with existing databases |

**sqlalchemy-dlock is ideal for:**
- Projects already using MySQL, MariaDB, MSSQL, Oracle, or PostgreSQL
- Teams wanting zero additional infrastructure
- Low to medium concurrency distributed synchronization
- Applications requiring strong consistency guarantees

**Not recommended for:**
- High-concurrency scenarios (consider Redis instead)
- Situations sensitive to database load

---

## Quick Start

### Installation

```bash
pip install sqlalchemy-dlock
```

**Requirements:**
- Python 3.9+
- SQLAlchemy 1.4.3+ or 2.x
- Appropriate database driver for your database (see below)

### Database Drivers

This library requires a database driver to be installed separately. Since you're already using SQLAlchemy, you likely have the appropriate driver installed. For a complete list of SQLAlchemy-supported drivers, see the [SQLAlchemy Dialects documentation](https://docs.sqlalchemy.org/en/latest/dialects/).

> ℹ️ **Notes**:
> - **MSSQL**: The `pyodbc` driver requires the Microsoft ODBC driver to be installed on your system. On Ubuntu/Debian:
>   ```bash
>   sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
>   ```
> - **Oracle**:
>   Oracle Database Free (23c/23ai) does NOT support `DBMS_LOCK.REQUEST` which is required for distributed lock functionality. For production use with Oracle, a full Oracle Database (Enterprise/Standard Edition) installation is required.

### Basic Usage

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('postgresql://user:pass@localhost/db')

with engine.connect() as conn:
    # Create a lock
    lock = create_sadlock(conn, 'my-resource-key')

    # Acquire the lock
    lock.acquire()
    assert lock.locked

    # Release the lock
    lock.release()
    assert not lock.locked
```

### Using Context Managers

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('postgresql://user:pass@localhost/db')

with engine.connect() as conn:
    # Automatically acquires and releases the lock
    with create_sadlock(conn, 'my-resource-key') as lock:
        assert lock.locked
        # Your critical section here

    # Lock is automatically released
    assert not lock.locked
```

### With Timeout

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('postgresql://user:pass@localhost/db')

with engine.connect() as conn:
    try:
        # Raises TimeoutError if lock cannot be acquired within 5 seconds
        with create_sadlock(conn, 'my-resource-key', contextual_timeout=5) as lock:
            pass
    except TimeoutError:
        print("Could not acquire lock - resource is busy")
```

---

## Common Use Cases

### Use Case 1: Preventing Duplicate Task Execution

Prevent multiple workers from processing the same task simultaneously:

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

def process_monthly_billing(user_id: int):
    engine = create_engine('postgresql://user:pass@localhost/db')
    with engine.connect() as conn:
        # Ensure billing for a user is only processed once at a time
        lock_key = f'billing:user:{user_id}'
        with create_sadlock(conn, lock_key, contextual_timeout=0):
            # If another worker is already processing this user's billing,
            # this will fail immediately (timeout=0)
            perform_billing_calculation(user_id)
            send_bill(user_id)
```

### Use Case 2: API Rate Limiting & Debouncing

Prevent simultaneous expensive operations on the same resource:

```python
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy_dlock import create_async_sadlock

app = FastAPI()
engine = create_async_engine('postgresql+asyncpg://user:pass@localhost/db')
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@app.post("/api/resources/{resource_id}/export")
async def export_resource(resource_id: str):
    async with AsyncSessionLocal() as session:
        # Try to acquire lock without blocking
        lock = create_async_sadlock(session, f'export:{resource_id}')
        acquired = await lock.acquire(block=False)
        if not acquired:
            raise HTTPException(status_code=409, detail="Export already in progress")

        try:
            return await perform_export(resource_id)
        finally:
            await lock.release()
```

### Use Case 3: Scheduled Job Coordination

Ensure scheduled jobs don't overlap across multiple servers:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

def data_sync_job():
    engine = create_engine('mysql://user:pass@localhost/db')
    with engine.connect() as conn:
        lock_key = 'scheduled-job:data-sync'

        # Only proceed if no other server is running this job
        lock = create_sadlock(conn, lock_key, contextual_timeout=60)
        with lock:
            perform_data_sync()

scheduler = BackgroundScheduler()
scheduler.add_job(data_sync_job, 'interval', minutes=30)
scheduler.start()
```

### Use Case 4: Decorator Pattern for Clean Code

Create a reusable decorator for locking functions:

```python
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

def with_db_lock(key_func, timeout=None):
    """Decorator that acquires a database lock before executing the function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            engine = create_engine('postgresql://user:pass@localhost/db')
            lock_key = key_func(*args, **kwargs)

            with engine.connect() as conn:
                with create_sadlock(conn, lock_key, contextual_timeout=timeout):
                    return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@with_db_lock(lambda user_id: f'user:update:{user_id}', timeout=10)
def update_user_profile(user_id: int, profile_data: dict):
    # This function is protected from concurrent execution
    # for the same user_id
    ...
```

---

## Working with SQLAlchemy ORM

Using locks with SQLAlchemy ORM sessions:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_dlock import create_sadlock

engine = create_engine('postgresql://user:pass@localhost/db')
Session = sessionmaker(bind=engine)

with Session() as session:
    with create_sadlock(session, 'my-resource-key') as lock:
        # Use the session within the locked context
        user = session.query(User).get(user_id)
        user.balance += 100
        session.commit()
```

---

## Asynchronous I/O Support

Full async/await support for asynchronous applications:

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy_dlock import create_async_sadlock

engine = create_async_engine('postgresql+asyncpg://user:pass@localhost/db')

async def main():
    async with engine.connect() as conn:
        async with create_async_sadlock(conn, 'my-resource-key') as lock:
            assert lock.locked
            # Your async critical section here
        assert not lock.locked
```

**Supported async drivers:**
- MySQL: [aiomysql](https://pypi.org/project/aiomysql/)
- PostgreSQL: [asyncpg](https://pypi.org/project/asyncpg/), [psycopg](https://pypi.org/project/psycopg/) (v3+)

---

## PostgreSQL Lock Types

PostgreSQL provides multiple advisory lock types. Choose based on your scenario:

| Lock Type             | Parameters               | Description                                  | Use Case                           |
| --------------------- | ------------------------ | -------------------------------------------- | ---------------------------------- |
| Session-exclusive     | (default)                | Held until manually released or session ends | Long-running tasks                 |
| Session-shared        | `shared=True`            | Multiple shared locks can coexist            | Multi-reader scenarios             |
| Transaction-exclusive | `xact=True`              | Automatically released when transaction ends | Transaction-scoped operations      |
| Transaction-shared    | `shared=True, xact=True` | Shared locks within transaction              | Transactional read-heavy workloads |

### Example: Transaction-Level Lock

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('postgresql://user:pass@localhost/db')

with engine.connect() as conn:
    # Transaction-level lock - automatically released on commit/rollback
    with create_sadlock(conn, 'my-key', xact=True) as lock:
        conn.execute(text("INSERT INTO ..."))
        conn.commit()  # Lock is released here
```

### Example: Shared Lock for Read-Heavy Workloads

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('postgresql://user:pass@localhost/db')

# Multiple readers can hold shared locks simultaneously
def read_resource(resource_id: str):
    with engine.connect() as conn:
        with create_sadlock(conn, f'resource:{resource_id}', shared=True):
            return conn.execute(text("SELECT * FROM resources WHERE id = :id"), {"id": resource_id})

# Writers need exclusive locks
def write_resource(resource_id: str, data: dict):
    with engine.connect() as conn:
        # This will wait for all shared locks to be released
        with create_sadlock(conn, f'resource:{resource_id}') as lock:
            conn.execute(text("UPDATE resources SET ..."))
            conn.commit()
```

---

## MSSQL Lock Types

SQL Server's `sp_getapplock` supports multiple lock modes:

| Lock Mode             | Parameters    | Description                                                  | Use Case                            |
| --------------------- | ------------- | ------------------------------------------------------------ | ----------------------------------- |
| `Exclusive` (default) | (default)     | Full exclusive access                                        | Write operations, critical sections |
| `Shared`              | `shared=True` | Multiple readers can hold lock concurrently                  | Read-heavy workloads                |
| `Update`              | `update=True` | Intended for update operations; compatible with Shared locks | Read-then-write patterns            |

### Example: Exclusive Lock for Writing (Default)

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('mssql+pyodbc://user:pass@localhost/db')

with engine.connect() as conn:
    # Exclusive lock for writing (default)
    with create_sadlock(conn, 'my-resource') as lock:
        conn.execute(text("UPDATE resources SET ..."))
```

### Example: Shared Lock for Reading

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('mssql+pyodbc://user:pass@localhost/db')

# Multiple readers can hold shared locks simultaneously
def read_resource(resource_id: str):
    with engine.connect() as conn:
        with create_sadlock(conn, f'resource:{resource_id}', shared=True):
            return conn.execute(text("SELECT * FROM resources WHERE id = :id"), {"id": resource_id})
```

### Example: Update Lock for Read-Then-Write Patterns

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('mssql+pyodbc://user:pass@localhost/db')

with engine.connect() as conn:
    # Update lock - compatible with shared locks, used for read-then-write patterns
    with create_sadlock(conn, 'my-resource', update=True) as lock:
        data = conn.execute(text("SELECT * FROM resources WHERE id = :id"), {"id": resource_id})
        # Perform read operations
        # Then upgrade to exclusive lock for writing
        conn.execute(text("UPDATE resources SET ..."))
```

---

## Oracle Lock Types

Oracle's `DBMS_LOCK.REQUEST` supports 6 lock modes with different compatibility:

| Lock Mode | Constant | Description | Use Case |
|-----------|----------|-------------|----------|
| `X` (default) | X_MODE | Exclusive - full exclusive access | Write operations, critical sections |
| `S` | S_MODE | Shared - multiple readers | Read-heavy workloads |
| `SS` | SS_MODE | Sub-Shared - share locks on subparts | Aggregate object read |
| `SX` | SX_MODE | Sub-Exclusive (Row Exclusive) | Row-level updates |
| `SSX` | SSX_MODE | Shared Sub-Exclusive | Read with pending write |
| `NL` | NL_MODE | Null - no actual lock | Testing/coordination only |

### Example: Exclusive Lock for Writing (Default)

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('oracle+oracledb://user:pass@localhost/db')

with engine.connect() as conn:
    # Exclusive lock for writing (default)
    with create_sadlock(conn, 'my-resource') as lock:
        conn.execute(text("UPDATE resources SET ..."))
```

### Example: Shared Lock for Reading

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('oracle+oracledb://user:pass@localhost/db')

# Multiple readers can hold shared locks simultaneously
def read_resource(resource_id: str):
    with engine.connect() as conn:
        with create_sadlock(conn, f'resource:{resource_id}', lock_mode="S"):
            return conn.execute(text("SELECT * FROM resources WHERE id = :id"), {"id": resource_id})
```

### Example: Transaction-Level Lock

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('oracle+oracledb://user:pass@localhost/db')

with engine.connect() as conn:
    # Transaction-level lock - automatically released on commit/rollback
    with create_sadlock(conn, 'my-resource', release_on_commit=True) as lock:
        conn.execute(text("INSERT INTO ..."))
        conn.commit()  # Lock is released here
```

### Example: Using Integer Lock ID Directly

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

engine = create_engine('oracle+oracledb://user:pass@localhost/db')

with engine.connect() as conn:
    # Direct integer lock ID (no hashing needed)
    with create_sadlock(conn, 12345, lock_mode="X") as lock:
        # Direct lock ID usage
        pass
```

**Note:** String keys are converted to integer IDs using blake2b hash (similar to PostgreSQL).

---

### Performance Considerations

- Database lock operations require network round-trips and are slower than in-memory solutions like Redis
- PostgreSQL timeout is implemented through polling and may have ~1 second variance
- Consider your concurrency requirements before choosing database-based locks

### Thread Safety

- Lock objects are **thread-local** and cannot be safely passed between threads
- Each thread must create its own lock instance
- Cross-process/cross-server locking works normally

### MySQL-Specific Behavior

⚠️ **Warning:** MySQL allows acquiring the same named lock multiple times on the same connection. This can lead to unexpected cascading locks:

```python
# DANGER: On MySQL, the second acquisition succeeds immediately
with create_sadlock(conn, 'my-key') as lock1:
    # This immediately returns without waiting - no real mutual exclusion!
    with create_sadlock(conn, 'my-key') as lock2:
        pass
```

To avoid this, use separate connections or implement additional checking logic.

### Lock Lifetime

- Locks are tied to your database connection
- Closing a connection releases all associated locks
- Properly manage Connection/Session lifecycle to avoid accidental lock releases

---

## FAQ

**Q: What happens if the database goes down?**

A: Locks are automatically released when the database connection is lost. This is intentional behavior to prevent deadlocks.

**Q: Can I pass a lock object between threads?**

A: No. Lock objects are thread-local for safety reasons. Each thread should create its own lock instance pointing to the same lock key.

**Q: How do I choose between MySQL and PostgreSQL?**

A: Both are fully supported. PostgreSQL offers more lock types (shared/transaction-level), while MySQL's implementation is simpler.

**Q: Are locks inherited by child processes?**

A: No. Child processes must establish their own database connections and create new lock objects.

**Q: How can I debug lock status?**

A:
- **MySQL:** `SELECT * FROM performance_schema.metadata_locks;`
- **PostgreSQL:** `SELECT * FROM pg_locks WHERE locktype = 'advisory';`

**Q: What's the maximum lock key size?**

A:
- **MySQL:** 64 characters
- **MSSQL:** 255 characters
- **PostgreSQL:** Keys are converted to 64-bit integers via BLAKE2b hash
- **Oracle:** Keys are converted to integers (0-1073741823) via BLAKE2b hash

**Q: Can I use this with SQLite?**

A: No. SQLite does not support the same named/advisory lock mechanisms as MySQL or PostgreSQL.

---

## Testing

The following database drivers are tested:

**MySQL:**
- [mysqlclient](https://pypi.org/project/mysqlclient/) (synchronous)
- [pymysql](https://pypi.org/project/pymysql/) (synchronous)
- [aiomysql](https://pypi.org/project/aiomysql/) (asynchronous)

**PostgreSQL:**
- [psycopg2](https://pypi.org/project/psycopg2/) (synchronous)
- [psycopg](https://pypi.org/project/psycopg/) (v3, synchronous and asynchronous)
- [asyncpg](https://pypi.org/project/asyncpg/) (asynchronous)

**MSSQL:**
- [pyodbc](https://pypi.org/project/pyodbc/) (synchronous)
- [pymssql](https://pypi.org/project/pymssql/) (synchronous)
- [aioodbc](https://pypi.org/project/aioodbc/) (asynchronous)

**Oracle:**
- [oracledb](https://pypi.org/project/oracledb/) (synchronous & asynchronous)
- [cx_Oracle](https://pypi.org/project/cx-Oracle/) (synchronous, legacy)

### Running Tests Locally

1. Install the project with development dependencies:

```bash
uv sync --group test
uv pip install mysqlclient aiomysql psycopg2 asyncpg
```

2. Start MySQL and PostgreSQL services using Docker:

```bash
docker compose -f db.docker-compose.yml up
```

3. Set environment variables for database connections (or use defaults):

```bash
export TEST_URLS="mysql://test:test@127.0.0.1:3306/test postgresql://postgres:test@127.0.0.1:5432/"
export TEST_ASYNC_URLS="mysql+aiomysql://test:test@127.0.0.1:3306/test postgresql+asyncpg://postgres:test@127.0.0.1:5432/"
```

> ℹ️ **Note:** Test cases also load environment variables from `tests/.env`.

4. Run tests:

```bash
python -m unittest
```

### Running Tests with Docker Compose

The project includes a comprehensive test matrix across Python and SQLAlchemy versions:

```bash
cd tests
docker compose up --abort-on-container-exit
```

---

## Documentation

Full API documentation is available at [https://sqlalchemy-dlock.readthedocs.io/](https://sqlalchemy-dlock.readthedocs.io/en/latest/)

---

## Links

- **Source Code:** [https://github.com/tanbro/sqlalchemy-dlock](https://github.com/tanbro/sqlalchemy-dlock)
- **Issue Tracker:** [https://github.com/tanbro/sqlalchemy-dlock/issues](https://github.com/tanbro/sqlalchemy-dlock/issues)
- **PyPI:** [https://pypi.org/project/sqlalchemy-dlock/](https://pypi.org/project/sqlalchemy-dlock/)

[SQLAlchemy]: https://www.sqlalchemy.org/
