from typing import Type, TypeGuard, TypeVar, Union

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session
from sqlalchemy.orm import Session, scoped_session

from .lock.base import AsyncConnT, BaseAsyncSadLock, BaseSadLock, ConnT
from .registry import find_lock_class

__all__ = ("create_sadlock", "create_async_sadlock")


KTV = TypeVar("KTV")


def create_sadlock(
    connection_or_session: ConnT, key: KTV, /, contextual_timeout: Union[float, int, None] = None, **kwargs
) -> BaseSadLock[KTV, ConnT]:
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
    return class_(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)


def create_async_sadlock(
    connection_or_session: AsyncConnT, key: KTV, /, contextual_timeout: Union[float, int, None] = None, **kwargs
) -> BaseAsyncSadLock[KTV, AsyncConnT]:
    """AsyncIO version of :func:`create_sadlock`"""
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

    class_ = find_lock_class(engine_name, True)
    if not is_async_sadlock_type(class_):
        raise TypeError(f"Unsupported connection_or_session type: {type(connection_or_session)}")
    return class_(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)


def is_sadlock_type(cls: Type) -> TypeGuard[Type[BaseSadLock]]:
    """Check if the passed-in class type is :class:`.BaseSadLock` object"""
    return issubclass(cls, BaseSadLock)


def is_async_sadlock_type(cls: Type) -> TypeGuard[Type[BaseAsyncSadLock]]:
    """Check if the passed-in class type is :class:`.BaseAsyncSadLock` object"""
    return issubclass(cls, BaseAsyncSadLock)
