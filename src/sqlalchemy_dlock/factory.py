from importlib import import_module
from string import Template
from typing import Any, Mapping, Type, Union

from sqlalchemy.engine import Connection

from .lock.base import BaseSadLock
from .types import TConnectionOrSession

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

    conf: Mapping[str, Any] = getattr(import_module(".registry", __package__), "REGISTRY")[engine.name]
    package: Union[str, None] = conf.get("package")
    if package:
        package = Template(package).safe_substitute(package=__package__)
    mod = import_module(conf["module"], package)
    clz: Type[BaseSadLock] = getattr(mod, conf["class"])
    return clz(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)
