# SQLAlchemy-DLock

[![GitHub](https://img.shields.io/github/license/tanbro/sqlalchemy-dlock)](https://github.com/tanbro/sqlalchemy-dlock)
[![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/tanbro/sqlalchemy-dlock)](https://github.com/tanbro/sqlalchemy-dlock/tags)
[![Python package](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml/badge.svg)](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml)
[![PyPI - Status](https://img.shields.io/pypi/status/sqlalchemy-dlock)](https://pypi.org/project/sqlalchemy-dlock/)
[![PyPI - License](https://img.shields.io/pypi/l/sqlalchemy-dlock)](https://pypi.org/project/sqlalchemy-dlock/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sqlalchemy-dlock)](https://pypi.org/project/sqlalchemy-dlock/)
[![Documentation Status](https://readthedocs.org/projects/sqlalchemy-dlock/badge/?version=latest)](https://sqlalchemy-dlock.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/tanbro/sqlalchemy-dlock/branch/main/graph/badge.svg?token=GfcDT1ckFX)](https://codecov.io/gh/tanbro/sqlalchemy-dlock)

Distributed lock based on Database and [SQLAlchemy][].

It currently supports blow locks:

- `MySQL` named lock: <https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html>
- `PostgreSQL` advisory lock: <https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS>

> ❗ **Note**:
>
> The project is not stable enough and **DO NOT** use it in production.

## Usages

- Work with [SQLAlchemy][]'s `Connection` object:

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy_dlock import create_sadlock

  key = 'user/001'

  engine = create_engine('postgresql://scott:tiger@localhost/')
  conn = engine.connect()

  # Create the D-Lock on the connection
  lock = create_sadlock(conn, key)

  # it's not lock when constructed
  assert not lock.acquired

  # lock
  lock.acquire()
  assert lock.acquired

  # un-lock
  lock.release()
  assert not lock.acquired
  ```

- Use in `with` statement

  ```python
  from contextlib import closing

  from sqlalchemy import create_engine
  from sqlalchemy_dlock import create_sadlock

  key = 'user/001'

  engine = create_engine('postgresql://scott:tiger@localhost/')
  with engine.connect() as conn:

      # Create the D-Lock on the connection
      with create_sadlock(conn, key) as lock:
          # It's locked
          assert lock.acquired

      # Auto un-locked
      assert not lock.acquired

      # If do not want to be locked in `with`, a `closing` wrapper may help
      with closing(create_sadlock(conn, key)) as lock2:
          # It's NOT locked here
          assert not lock2.acquired
          # lock it now:
          lock2.acquire()
          assert lock2.acquired

      # Auto un-locked
      assert not lock2.acquired
  ```

- Work with [SQLAlchemy][]'s `ORM` session:

  > ❗ **Note**:
  >
  > According to <https://docs.sqlalchemy.org/14/orm/extensions/asyncio.html>:
  >
  > - The asyncio extension as of SQLAlchemy 1.4.3 can now be considered to be **beta level** software.
  > - The asyncio extension requires at least Python version 3.6

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from sqlalchemy_dlock import create_sadlock

  key = 'user/001'

  engine = create_engine('postgresql://scott:tiger@localhost/')
  Session = sessionmaker(bind=engine)

  with Session() as session:
    with create_sadlock(session, key) as lock:
        assert lock.acquired
    assert not lock.acquired
  ```

- Work asynchronously

  ```python
  from sqlalchemy.ext.asyncio import create_async_engine
  from sqlalchemy_dlock.asyncio import create_async_sadlock

  key = 'user/001'

  engine = create_async_engine('postgresql+asyncpg://scott:tiger@localhost/')

  async with engine.begin() as conn:
      async with create_async_sadlock(conn, key) as lock:
          assert lock.acquired
      assert not lock.acquired
  ```

## Tests

Just `up` the docker-compose in `tests` directory:

```bash
(cd tests; docker-compose up --abort-on-container-exit --exit-code-from pytest; docker-compose down)
```

[SQLAlchemy]: https://www.sqlalchemy.org/ "The Python SQL Toolkit and Object Relational Mapper"
