from importlib import import_module

from sqlalchemy.ext.asyncio import AsyncConnection

from ..utils import safe_name
from .types import BaseAsyncSadLock, TAsyncConnectionOrSession

__all__ = ['create_async_sadlock']


def create_async_sadlock(
        connection_or_engine: TAsyncConnectionOrSession,
        key,
        *args, **kwargs
) -> BaseAsyncSadLock:
    """Create a session level distributed lock object

    Parameters
    ----------
    connection_or_engine :
        sqlalchemy Connection or orm Session/ScoptedSession object.
        Database Connection on which the SQL locking functions will be invoked

    key:
        Key/name or sth like that used as SQL locking function's ID

    Returns
    -------
    BaseAsyncSadLock
        New created lock object, whose type is a sub-class of :class:`BaseAsyncSadLock`.

        The actual type of the lock object depends on the type of `connection` object.

        MySQL and PostgreSQL are supported til now.
    """
    if isinstance(connection_or_engine, AsyncConnection):
        name = safe_name(connection_or_engine.sync_engine.engine.name)
    else:
        name = safe_name(connection_or_engine.get_bind().name)
    try:
        mod = import_module('..impl.{}'.format(name), __name__)
    except ImportError as exception:
        raise NotImplementedError('{}: {}'.format(name, exception))
    lock_cls = getattr(mod, 'AsyncSadLock')
    return lock_cls(connection_or_engine, key, **kwargs)
