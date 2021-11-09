from importlib import import_module

from sqlalchemy.engine import Connection

from .sessionlevellock import AbstractSessionLevelLock
from .types import TConnectionOrSession
from .utils import safe_name

__all__ = ['sadlock']


def sadlock(
        connection_or_session: TConnectionOrSession,
        key,
        **kwargs
) -> AbstractSessionLevelLock:
    """Create a session level distributed lock object

    Parameters
    ----------
    connection_or_engine : sqlalchemy Connection or orm Session/ScoptedSession object.
        Database Connection on which the SQL locking functions will be invoked

    key:
        Key/name or sth like that used as SQL locking function's ID

    Returns
    -------
    AbstractSessionLevelLock
        New created lock object, whose type is a sub-class of :class:`AbstractSessionLevelLock`.

        The actual type of the lock object depends on the type of `connection` object.

        MySQL and PostgreSQL are supported til now.
    """
    if isinstance(connection_or_session, Connection):
        name = safe_name(connection_or_session.engine.name)
    else:
        name = safe_name(connection_or_session.get_bind().name)
    try:
        mod = import_module('..impl.{}'.format(name), __name__)
    except ImportError as exception:
        raise NotImplementedError('{}: {}'.format(name, exception))
    lock_cls = getattr(mod, 'SessionLevelLock')
    return lock_cls(connection_or_session, key, **kwargs)
