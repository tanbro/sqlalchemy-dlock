# SQLAlchemy-DLock

Distributed lock based on Database and SQLAlchemy.

It currently supports locks of:

- MySQL: <https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html>
- PostgreSQL: <https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS>

It's not stable and **DO NOT** use it in production.

## Usages

Basic usage:

```python
# ...
from sqlalchemy import create_engine
from sqlalchemy_dlock import make_sa_dlock

# ...

lock_key = 'user/001'

# ...

engine = create_engine('postgresql://scott:tiger@localhost/')

# ...

with engine.connect() as conn:
    with make_sa_dlock(conn, lock_key):
        # do sth...
        pass
# ...
```

Work with SQLAlchemy's Session:

```python
# ...
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_dlock import make_sa_dlock
# ...

lock_key = 'user/001'

# ...

engine = create_engine('postgresql://scott:tiger@localhost/')
Session = sessionmaker(bind=engine)

# ...

session = Session()

# ...

with session.bind.connect() as conn:
    with make_sa_dlock(conn, lock_key):
        # ...
        user = session.query('User').filter(id='001').one()
        user.password = 'new password'
        session.commit()
        # ...
# ...
```
