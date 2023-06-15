# SQLAlchemy-DLock

[![Python package](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml/badge.svg)](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-dlock)](https://pypi.org/project/sqlalchemy-dlock/)
[![Documentation Status](https://readthedocs.org/projects/sqlalchemy-dlock/badge/?version=latest)](https://sqlalchemy-dlock.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/tanbro/sqlalchemy-dlock/branch/main/graph/badge.svg?token=GfcDT1ckFX)](https://codecov.io/gh/tanbro/sqlalchemy-dlock)

Distributed lock based on Database and [SQLAlchemy][].

It currently supports below locks:

 Database  |                                             Lock
---------- | ---------------------------------------------------------------------------------------------
MySQL      | [named lock](https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html)
PostgreSQL | [advisory lock](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS)

## Usages

- Work with [SQLAlchemy][] `Connection`:

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

- `with` statement

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

- Work with [SQLAlchemy][] `ORM` session:

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

- Asynchronous I/O Support

  > ℹ️ **info**:
  >
  > - [SQLAlchemy][] `1.x`: <https://docs.sqlalchemy.org/14/orm/extensions/asyncio.html>
  > - [SQLAlchemy][] `2.x`: <https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html>

  ```python
  from sqlalchemy.ext.asyncio import create_async_engine
  from sqlalchemy_dlock.asyncio import create_async_sadlock

  key = 'user/001'

  engine = create_async_engine('postgresql+asyncpg://scott:tiger@localhost/')

  async with engine.begin() as conn:
      async with create_async_sadlock(conn, key) as lock:
          assert lock.locked
          await lock.release()
          assert not lock.locked
          await lock.acquire()
      assert not lock.locked
  ```

## Tests

Following [SQLAlchemy][] engines are tested:

- MySQL:

  - mysqlclient
  - PyMySQL
  - aiomysql ([asyncio][])

- Postgres:

  - psycopg2
  - asyncpg ([asyncio][])

You can run unit-tests:

- directly:

  1. Install the project (A virtual environment ([venv][]) is strongly advised):

     ```bash
     pip install -e .
     ```

  1. Start up your mysql and postgresql

  1. Set environment variables `TEST_URLS` and `TEST_ASYNC_URLS` for sync and async database connection url.
     Multiple connections separated by space.
     The test cases load environment variables in `tests/.env`.

     eg (and also the defaults):

     ```ini
     TEST_URLS=mysql://test:test@localhost/test postgresql://postgres:test@localhost/
     TEST_ASYNC_URLS=mysql+aiomysql://test:test@localhost/test postgresql+asyncpg://postgres:test@localhost/
     ```

  1. run unit-test

     ```bash
     python -m unittest
     ```

- in docker-compose:

  1. build the project

     ```bash
     python -m pip install build && python -m build -w
     ```

  1. run unit-test

     ```bash
     cd tests
     docker compose up
     ```

[SQLAlchemy]: https://www.sqlalchemy.org/ "The Python SQL Toolkit and Object Relational Mapper"
[asyncio]: https://docs.python.org/library/asyncio.html "asyncio is a library to write concurrent code using the async/await syntax."
[venv]: https://docs.python.org/library/venv.html "The venv module supports creating lightweight “virtual environments”, each with their own independent set of Python packages installed in their site directories. "
