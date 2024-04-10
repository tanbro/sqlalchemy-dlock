from importlib import import_module
import sys
from typing import Union, Type

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from ..utils import pascal_case, safe_name
from .lock.base import BaseAsyncSadLock

if sys.version_info >= (3, 12):  # pragma: no cover
    from ._sa_types import TAsyncConnectionOrSession
else:  # pragma: no cover
    from ._sa_types_backward import TAsyncConnectionOrSession

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
    clz: Type[BaseAsyncSadLock] = getattr(mod, f"{pascal_case(engine_name)}AsyncSadLock")
    return clz(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)
