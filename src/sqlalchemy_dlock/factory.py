from collections.abc import Callable
from typing import TypeGuard, TypeVar, cast

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session
from sqlalchemy.orm import Session, scoped_session

from .lock.base import AsyncConnectionTV, BaseAsyncSadLock, BaseSadLock, ConnectionTV
from .registry import find_lock_class

__all__ = ("create_async_sadlock", "create_sadlock")


KTV = TypeVar("KTV")
AKTV = TypeVar("AKTV")


def create_sadlock(
    connection_or_session: ConnectionTV,
    key: KTV,
    /,
    contextual_timeout: float | None = None,
    convert: Callable[[KTV], AKTV] | None = None,
    **kwargs,
) -> BaseSadLock[KTV, ConnectionTV, AKTV]:
    """Create a database distributed lock object

    All arguments will be passed to a sub-class of :class:`.BaseSadLock`, depend on the type of ``connection_session``'s SQLAlchemy engine.

    Args:

        connection_or_session:
            Connection or Session object SQL locking functions will be invoked on it.

        key:
            ID or name of the SQL locking function.

        contextual_timeout:
            Timeout(seconds) for Context Managers.

            When called in a :keyword:`with` statement, the new created lock object will pass it to ``timeout`` argument of :meth:`.BaseSadLock.acquire`.

            A :exc:`TimeoutError` will be thrown if can not acquire after ``contextual_timeout``.

        convert:
            Custom function that converts ``key`` to the backend-specific type exposed by :attr:`.BaseSadLock.actual_key`.

    Returns:
        New created lock object

        Type of the lock object is a sub-class of :class:`.BaseSadLock`, which depends on the passed-in SQLAlchemy `connection` or `session`.

        MySQL, MariaDB, MSSQL, Oracle, and PostgreSQL connection/session are supported til now.
    """
    if isinstance(connection_or_session, Connection):
        engine_name = connection_or_session.engine.name
    elif isinstance(connection_or_session, (Session, scoped_session)):
        bind = connection_or_session.get_bind()
        if isinstance(bind, Connection):
            engine_name = bind.engine.name
        else:
            engine_name = bind.name
    else:
        raise TypeError(f"Unsupported connection_or_session type: {type(connection_or_session)}")

    class_ = find_lock_class(engine_name)
    if not is_sadlock_type(class_):
        raise TypeError(f"Unsupported connection_or_session type: {type(connection_or_session)}")
    result = class_(connection_or_session, key, contextual_timeout=contextual_timeout, convert=convert, **kwargs)
    return cast(BaseSadLock[KTV, ConnectionTV, AKTV], result)


def create_async_sadlock(
    connection_or_session: AsyncConnectionTV,
    key: KTV,
    /,
    contextual_timeout: float | None = None,
    convert: Callable[[KTV], AKTV] | None = None,
    **kwargs,
) -> BaseAsyncSadLock[KTV, AsyncConnectionTV, AKTV]:
    """Create an async database distributed lock.

    Parameters are equivalent to :func:`create_sadlock`.
    """
    if isinstance(connection_or_session, AsyncConnection):
        engine_name = connection_or_session.engine.name
    elif isinstance(connection_or_session, (AsyncSession, async_scoped_session)):
        bind = connection_or_session.get_bind()
        if isinstance(bind, Connection):
            engine_name = bind.engine.name
        else:
            engine_name = bind.name
    else:
        raise TypeError(f"Unsupported connection_or_session type: {type(connection_or_session)}")

    class_ = find_lock_class(engine_name, is_asyncio=True)
    if not is_async_sadlock_type(class_):
        raise TypeError(f"Unsupported connection_or_session type: {type(connection_or_session)}")
    result = class_(connection_or_session, key, contextual_timeout=contextual_timeout, convert=convert, **kwargs)
    return cast(BaseAsyncSadLock[KTV, AsyncConnectionTV, AKTV], result)


def is_sadlock_type(cls: type) -> TypeGuard[type[BaseSadLock]]:
    """Check if the passed-in class type is :class:`.BaseSadLock` object"""
    return issubclass(cls, BaseSadLock)


def is_async_sadlock_type(cls: type) -> TypeGuard[type[BaseAsyncSadLock]]:
    """Check if the passed-in class type is :class:`.BaseAsyncSadLock` object"""
    return issubclass(cls, BaseAsyncSadLock)
