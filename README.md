# sqlalchemy-dlock

[![Python package](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml/badge.svg)](https://github.com/tanbro/sqlalchemy-dlock/actions/workflows/python-package.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-dlock)](https://pypi.org/project/sqlalchemy-dlock/)
[![Documentation Status](https://readthedocs.org/projects/sqlalchemy-dlock/badge/?version=latest)](https://sqlalchemy-dlock.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/tanbro/sqlalchemy-dlock/branch/main/graph/badge.svg)](https://codecov.io/gh/tanbro/sqlalchemy-dlock)

`sqlalchemy-dlock` is a distributed-lock library based on Database and [SQLAlchemy][].

It currently supports below locks:

 Database  |                                             Lock
---------- | ---------------------------------------------------------------------------------------------
MySQL      | [named lock](https://dev.mysql.com/doc/refman/en/locking-functions.html)
PostgreSQL | [advisory lock](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS)

## Install

```bash
pip install sqlalchemy-dlock
```

## Usage

- Work with [SQLAlchemy][] [`Connection`](https://docs.sqlalchemy.org/20/core/connections.html):

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy_dlock import create_sadlock

  key = 'user/001'

  engine = create_engine('postgresql://scott:tiger@127.0.0.1/')
  conn = engine.connect()

  # Create the D-Lock on the connection
  lock = create_sadlock(conn, key)

  # it's not lock when constructed
  assert not lock.locked

  # lock
  lock.acquire()
  assert lock.locked

  # un-lock
  lock.release()
  assert not lock.locked
  ```

- `with` statement

  ```python
  from contextlib import closing

  from sqlalchemy import create_engine
  from sqlalchemy_dlock import create_sadlock

  key = 'user/001'

  engine = create_engine('postgresql://scott:tiger@127.0.0.1/')
  with engine.connect() as conn:

      # Create the D-Lock on the connection
      with create_sadlock(conn, key) as lock:
          # It's locked
          assert lock.locked

      # Auto un-locked
      assert not lock.locked

      # If do not want to be locked in `with`, a `closing` wrapper may help
      with closing(create_sadlock(conn, key)) as lock2:
          # It's NOT locked here !!!
          assert not lock2.locked
          # lock it now:
          lock2.acquire()
          assert lock2.locked

      # Auto un-locked
      assert not lock2.locked
  ```

- Work with [SQLAlchemy][] [`ORM` `Session`](https://docs.sqlalchemy.org/en/20/orm/session.html):

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from sqlalchemy_dlock import create_sadlock

  key = 'user/001'

  engine = create_engine('postgresql://scott:tiger@127.0.0.1/')
  Session = sessionmaker(bind=engine)

  with Session() as session:
    with create_sadlock(session, key) as lock:
        assert lock.locked
    assert not lock.locked
  ```

- Asynchronous I/O Support

  > 💡 **TIP**
  >
  > - [SQLAlchemy][] `1.x`'s asynchronous I/O: <https://docs.sqlalchemy.org/14/orm/extensions/asyncio.html>
  > - [SQLAlchemy][] `2.x`'s asynchronous I/O: <https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html>

  ```python
  from sqlalchemy.ext.asyncio import create_async_engine
  from sqlalchemy_dlock.asyncio import create_async_sadlock

  key = 'user/001'

  engine = create_async_engine('postgresql+asyncpg://scott:tiger@127.0.0.1/')

  async with engine.connect() as conn:
      async with create_async_sadlock(conn, key) as lock:
          assert lock.locked
          await lock.release()
          assert not lock.locked
          await lock.acquire()
      assert not lock.locked
  ```

  > ℹ️ **NOTE** \
  > [aiomysql][], [asyncpg][] and [psycopg][] are tested asynchronous drivers.
  >
  > We can install it with asynchronous DB libraries:
  >
  > ```bash
  > pip install SQLAlchemy[asyncio] aiomysql sqlalchemy-dlock
  > ```
  >
  > or
  >
  > ```bash
  > pip install SQLAlchemy[asyncio] asyncpg sqlalchemy-dlock
  > ```

## Test

Following drivers are tested:

- MySQL:
  - [mysqlclient][] (synchronous)
  - [pymysql][] (synchronous)
  - [aiomysql][] (asynchronous)
- Postgres:
  - [psycopg2][] (synchronous)
  - [asyncpg][] (asynchronous)
  - [psycopg][] (synchronous and asynchronous)

You can run unit-tests

- on local environment:

  1. Install the project in editable mode with `asyncio` optional dependencies, and libraries/drivers needed in test. A virtual environment ([venv][]) is strongly advised:

     ```bash
     pip install -e .[asyncio] -r tests/requirements.txt
     ```

  1. start up mysql and postgresql service

     There is a docker [compose][] file `db.docker-compose.yml` in project's top directory,
     which can be used to run mysql and postgresql develop environment conveniently:

     ```bash
     docker compose -f db.docker-compose.yml up
     ```

  1. set environment variables `TEST_URLS` and `TEST_ASYNC_URLS` for sync and async database connection url.
     Multiple connections separated by space.

     eg: (following values are also the defaults, and can be omitted)

     ```ini
     TEST_URLS=mysql://test:test@127.0.0.1/test postgresql://postgres:test@127.0.0.1/
     TEST_ASYNC_URLS=mysql+aiomysql://test:test@127.0.0.1/test postgresql+asyncpg://postgres:test@127.0.0.1/
     ```

     > ℹ️ **NOTE** \
     > The test cases would load environment variables from dot-env file `tests/.env`.

  1. run unit-test

     ```bash
     python -m unittest
     ```

- or on docker [compose][]:

  `tests/docker-compose.yml` defines a Python and [SQLAlchemy][] version matrix -- it combines Python `3.8` to `3.12` and [SQLAlchemy][] `v1`/`v2` for test cases. We can run it by:

  ```bash
  cd tests
  docker-compose up --abort-on-container-exit
  ```

[SQLAlchemy]: https://www.sqlalchemy.org/ "The Python SQL Toolkit and Object Relational Mapper"
[venv]: https://docs.python.org/library/venv.html "The venv module supports creating lightweight “virtual environments”, each with their own independent set of Python packages installed in their site directories. "
[mysqlclient]: https://pypi.org/project/mysqlclient/ "Python interface to MySQL"
[psycopg2]: https://pypi.org/project/psycopg2/ "PostgreSQL database adapter for Python"
[psycopg]: https://pypi.org/project/psycopg/ "Psycopg 3 is a modern implementation of a PostgreSQL adapter for Python."
[aiomysql]: https://pypi.org/project/aiomysql/ "aiomysql is a “driver” for accessing a MySQL database from the asyncio (PEP-3156/tulip) framework."
[asyncpg]: https://pypi.org/project/asyncpg/ "asyncpg is a database interface library designed specifically for PostgreSQL and Python/asyncio. "
[pymysql]: https://pypi.org/project/pymysql/ "Pure Python MySQL Driver"
[compose]: https://docs.docker.com/compose/ "Compose is a tool for defining and running multi-container Docker applications."
