from importlib import import_module
from typing import Union

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from ..utils import pascal_case, safe_name
from .lock.base import BaseAsyncSadLock, TAsyncConnectionOrSession

__all__ = ["create_async_sadlock"]


def create_async_sadlock(
    connection_or_session: TAsyncConnectionOrSession, key, contextual_timeout: Union[float, int, None] = None, **kwargs
) -> BaseAsyncSadLock:
    if isinstance(connection_or_session, AsyncConnection):
        sync_engine = connection_or_session.sync_engine
    else:
        bind = connection_or_session.get_bind()
        if isinstance(bind, Connection):
            sync_engine = bind.engine
        else:
            sync_engine = bind
    engine_name = safe_name(sync_engine.name)
    try:
        mod = import_module(f"..lock.{engine_name}", __name__)
    except ImportError as exception:  # pragma: no cover
        raise NotImplementedError(f"{engine_name}: {exception}")
    clz = getattr(mod, f"{pascal_case(engine_name)}AsyncSadLock")
    return clz(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)
