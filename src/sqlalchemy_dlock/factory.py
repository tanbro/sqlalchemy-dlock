from typing import Union

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from .lock.base import BaseAsyncSadLock, BaseSadLock
from .types import AsyncConnectionOrSessionT, ConnectionOrSessionT
from .utils import find_lock_class

__all__ = ["create_sadlock", "create_async_sadlock"]


def create_sadlock(
    connection_or_session: ConnectionOrSessionT, key, /, contextual_timeout: Union[float, int, None] = None, **kwargs
) -> BaseSadLock:
    """Create a database distributed lock object

    All arguments will be passed to a sub-class of :class:`.BaseSadLock`, depend on the type of ``connection_session``'s SQLAlchemy engine.

    Args:

        connection_or_session:
            Connection or Session object SQL locking functions will be invoked on it.

        key:
            ID or name of the SQL locking function

        contextual_timeout:
            Timeout(seconds) for Context Managers.

            When called in a :keyword:`with` statement, the new created lock object will pass it to ``timeout`` argument of :meth:`.BaseSadLock.acquire`.

            A :exc:`TimeoutError` will be thrown if can not acquire after ``contextual_timeout``

    Returns:
        New created lock object

        Type of the lock object is a sub-class of :class:`.BaseSadLock`, which depends on the passed-in SQLAlchemy `connection` or `session`.

        MySQL and PostgreSQL connection/session are supported til now.
    """  # noqa: E501
    if isinstance(connection_or_session, Connection):
        engine = connection_or_session.engine
    else:
        bind = connection_or_session.get_bind()
        if isinstance(bind, Connection):
            engine = bind.engine
        else:
            engine = bind

    class_ = find_lock_class(engine.name)
    return class_(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)


def create_async_sadlock(
    connection_or_session: AsyncConnectionOrSessionT, key, /, contextual_timeout: Union[float, int, None] = None, **kwargs
) -> BaseAsyncSadLock:
    """AsyncIO version of :func:`create_sadlock`"""
    if isinstance(connection_or_session, AsyncConnection):
        engine = connection_or_session.engine
    else:
        bind = connection_or_session.get_bind()
        if isinstance(bind, Connection):
            engine = bind.engine
        else:
            engine = bind

    class_ = find_lock_class(engine.name, True)
    return class_(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)
