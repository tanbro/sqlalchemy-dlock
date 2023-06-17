from importlib import import_module

from sqlalchemy.engine import Connection

from .baselock import BaseSadLock, TConnectionOrSession
from .utils import safe_name

__all__ = ["create_sadlock"]


def create_sadlock(connection_or_session: TConnectionOrSession, key, *args, **kwargs) -> BaseSadLock:
    """Create a database distributed lock object

    Parameters
    ----------
    connection_or_session :
        Connection or Session object SQL locking functions will be invoked on it.

    key:
        ID or name of the SQL locking function

    Returns
    -------
    BaseSadLock
        New created lock object.

        Type of the lock object is sub-class of :class:`.BaseSadLock`,
        which depends on the passed-in SQLAlchemy `connection` or `session`.

        MySQL and PostgreSQL connection/session are supported til now.
    """
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
    lock_cls = getattr(mod, "SadLock")
    return lock_cls(connection_or_session, key, *args, **kwargs)
