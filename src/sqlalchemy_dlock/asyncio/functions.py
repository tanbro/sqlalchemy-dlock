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
    if isinstance(connection_or_engine, AsyncConnection):
        name = safe_name(connection_or_engine.sync_engine.engine.name)
    else:
        name = safe_name(connection_or_engine.get_bind().name)
    try:
        mod = import_module('..impl.{}'.format(name), __name__)
    except ImportError as exception:  # pragma: no cover
        raise NotImplementedError('{}: {}'.format(name, exception))
    lock_cls = getattr(mod, 'AsyncSadLock')
    return lock_cls(connection_or_engine, key, *args, **kwargs)
