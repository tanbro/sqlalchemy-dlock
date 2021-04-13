# SQLAlchemy-DLock

[![Documentation Status](https://readthedocs.org/projects/sqlalchemy-dlock/badge/?version=latest)](https://sqlalchemy-dlock.readthedocs.io/en/latest/?badge=latest)

Distributed lock based on Database and [SQLAlchemy][].

It currently supports locks of:

- `MySQL`: <https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html>
- `PostgreSQL`: <https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS>

It's not stable and **DO NOT** use it in production.

## Usages

Basic usage:

```python
# ...
from sqlalchemy import create_engine
from sqlalchemy_dlock import sadlock

# ...

lock_key = 'user/001'

# ...

engine = create_engine('postgresql://scott:tiger@localhost/')

# ...

with engine.connect() as conn:
    with sadlock(conn, lock_key):
        pass
        # locked here!
        # ...
    pass
    # unlocked here!
    # ...
# ...
```

Work with [SQLAlchemy][]'s Session:

```python
# ...
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_dlock import sadlock

# ...

lock_key = 'user/001'

# ...

engine = create_engine('postgresql://scott:tiger@localhost/')
Session = sessionmaker(bind=engine)

# ...

session = Session()

# ...

with session.bind.connect() as conn:
    with sadlock(conn, lock_key):
        # locked here!
        # ...
        user = session.query('User').filter(id='001').one()
        user.password = 'new password'
        session.commit()
        # ...
    pass
    # unlocked here!
    # ...
# ...
```

[SQLAlchemy]: https://www.sqlalchemy.org/ "The Python SQL Toolkit and Object Relational Mapper"
