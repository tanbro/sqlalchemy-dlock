from importlib import import_module

from sqlalchemy.engine import Connection  # noqa

from .sessionlevellock import AbstractSessionLevelLock
from .utils import safe_name

__all__ = ['make_sa_dlock']  # noqa


def make_sa_dlock(  # noqa
        connection: Connection,
        key,
        **kwargs
) -> AbstractSessionLevelLock:
    """Create a session level distributed lock object

    Parameters
    ----------

    connection: sqlalchemy.engine.Connection
        Database Connection on which the SQL locking functions will be invoked

    key:
        Key/name or sth like that used as SQL locking function's ID

    Returns
    -------
    AbstractSessionLevelLock
        New created lock object

        Actual type of the lock object depends on ``connection`` parameter.

        MySQL and PostgreSQL are supported til now
    """
    name = safe_name(connection.engine.name)
    mod = import_module('..impl.{}'.format(name), __name__)
    lock_cls = getattr(mod, 'SessionLevelLock')
    return lock_cls(connection, key, **kwargs)
