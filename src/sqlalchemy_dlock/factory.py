import sys
from importlib import import_module
from typing import Type, Union

from sqlalchemy.engine import Connection

from .lock.base import BaseSadLock
from .utils import pascal_case, safe_name

if sys.version_info < (3, 12):  # pragma: no cover
    from ._sa_types_backward import TConnectionOrSession
else:  # pragma: no cover
    from ._sa_types import TConnectionOrSession

__all__ = ["create_sadlock"]


def create_sadlock(
    connection_or_session: TConnectionOrSession, key, /, contextual_timeout: Union[float, int, None] = None, **kwargs
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
    engine_name = safe_name(engine.name)
    try:
        mod = import_module(f"..lock.{engine_name}", __name__)
    except ImportError as exception:  # pragma: no cover
        raise NotImplementedError(f"{engine_name}: {exception}")
    clz: Type[BaseSadLock] = getattr(mod, f"{pascal_case(engine_name)}SadLock")
    return clz(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)
