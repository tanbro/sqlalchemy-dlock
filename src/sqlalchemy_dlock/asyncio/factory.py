from importlib import import_module
from string import Template
from typing import Any, Mapping, Type, Union

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

from .lock.base import BaseAsyncSadLock
from .types import TAsyncConnectionOrSession

__all__ = ["create_async_sadlock"]


def create_async_sadlock(
    connection_or_session: TAsyncConnectionOrSession, key, contextual_timeout: Union[float, int, None] = None, **kwargs
) -> BaseAsyncSadLock:
    if isinstance(connection_or_session, AsyncConnection):
        engine = connection_or_session.sync_engine
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
    clz: Type[BaseAsyncSadLock] = getattr(mod, conf["class"])
    return clz(connection_or_session, key, contextual_timeout=contextual_timeout, **kwargs)
