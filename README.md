# SQLAlchemy-DLock

[![Documentation Status](https://readthedocs.org/projects/sqlalchemy-dlock/badge/?version=latest)](https://sqlalchemy-dlock.readthedocs.io/en/latest/?badge=latest)

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
  from sqlalchemy_dlock import sadlock
  
  key = 'user/001'
  
  engine = create_engine('postgresql://scott:tiger@localhost/')
  conn = engine.connect()
  
  # Create the D-Lock on the connection
  lock = sadlock(conn, key)
  
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
  from sqlalchemy_dlock import sadlock
  
  key = 'user/001'
  
  engine = create_engine('postgresql://scott:tiger@localhost/')
  with engine.connect() as conn:

      # Create the D-Lock on the connection
      with sadlock(conn, key) as lock:
          # It's locked
          assert lock.acquired

      # Auto un-locked
      assert not lock.acquired
  
      # If do not want to be locked in `with`, a `closing` wrapper may help
      with closing(sadlock(conn, key)) as lock2:
          # It's NOT locked here
          assert not lock2.acquired
          # lock it now:
          lock2.acquire()
          assert lock2.acquired

      # Auto un-locked
      assert not lock2.acquired
  ```

- Work with [SQLAlchemy][]'s `Session` object:

  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import scoped_session, sessionmaker
  from sqlalchemy_dlock import sadlock
  
  engine = create_engine('postgresql://scott:tiger@localhost/')
  factory = sessionmaker(bind=engine)
  Session = scoped_session(factory)
  session = Session()
  
  key = 'user/001'
  
  with sadlock(session, key) as lock:
      assert lock.acquired
  assert not lock.acquired
  ```

- Work with `asycio`

  ```python
  from sqlalchemy.ext.asyncio import create_async_engine
  from sqlalchemy_dlock.asyncio import sadlock
  
  engine = create_async_engine('postgresql+asyncpg://scott:tiger@localhost/')
  
  async with engine.begin() as conn:
      async with sadlock(conn, key) as lock:
          assert lock.acquired
      assert not lock.acquired
  ```

[SQLAlchemy]: https://www.sqlalchemy.org/ "The Python SQL Toolkit and Object Relational Mapper"
