# sqlalchemy-dlock

Distributed lock based on Database and SQLAlchemy.

It currently supports locks of:

- MySQL: https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html
- PostgreSQL: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS

## Usages

Basic:

```python
from sqlalchemy import create_engine
from sqlalchemy_dlock import make_session_level_lock as sd_lock

# ...

lock_key = 'user/001'

# ...

engine = create_engine()

# ...

with engine.connect() as conn:
    with sd_lock(conn, lock_key):
        # do sth...
        pass
# ...
```

Made from SQLAlchemy's Session:

```python
# ...

lock_key = 'user/001'

# ...

with Session.bind.connect() as conn:
    with sd_lock(conn, lock_key):
        # ...
        user = Session.query(User).filter(id='001').one()
        user.password = new_pass
        Session.commit()
        # ...
# ...
```

Or, if the `session` has no `commit`, `rollback`, `close`:

```python
# ...

lock_key = 'user/001'

# ...

with sd_lock(Session.connection(), lock_key):
    # ...
    user = Session.query(User).filter(id='001').one()
    password = user.password
    # ...
# ...
```
