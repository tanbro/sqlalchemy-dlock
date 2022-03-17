from importlib import import_module

from sqlalchemy.engine import Connection

from .types import BaseSadLock, TConnectionOrSession
from .utils import safe_name

__all__ = ['create_sadlock']


def create_sadlock(
        connection_or_session: TConnectionOrSession,
        key,
        *args, **kwargs
) -> BaseSadLock:
    """Create a database distributed lock object

    Parameters
    ----------
    connection_or_session :
        sqlalchemy Connection or orm Session/ScopedSession object.
        Database Connection on which the SQL locking functions will be invoked

    key:
        Key/name or sth like that used as SQL locking function's ID

    Returns
    -------
    BaseSadLock
        New created lock object, whose type is a subclass of :class:`BaseSadLock`.

        The actual type of the lock object depends on the type of `connection` object.

        MySQL and PostgreSQL are supported til now.
    """
    if isinstance(connection_or_session, Connection):
        name = safe_name(connection_or_session.engine.name)
    else:
        name = safe_name(connection_or_session.get_bind().name)
    try:
        mod = import_module('..impl.{}'.format(name), __name__)
    except ImportError as exception:  # pragma: no cover
        raise NotImplementedError('{}: {}'.format(name, exception))
    lock_cls = getattr(mod, 'SadLock')
    return lock_cls(connection_or_session, key, *args, **kwargs)
