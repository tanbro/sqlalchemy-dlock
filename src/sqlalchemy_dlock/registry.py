from __future__ import annotations

from importlib import import_module
from string import Template
from typing import TYPE_CHECKING, Type, Union

if TYPE_CHECKING:
    from .lock.base import BaseAsyncSadLock, BaseSadLock


REGISTRY = {
    "mysql": {
        "module": ".lock.mysql",
        "package": "${package}",  # module name relative to the package
        "class": "MysqlSadLock",
    },
    "postgresql": {
        "module": ".lock.postgresql",
        "package": "${package}",  # module name relative to the package
        "class": "PostgresqlSadLock",
    },
}

ASYNCIO_REGISTRY = {
    "mysql": {
        "module": ".lock.mysql",
        "package": "${package}",  # module name relative to the package
        "class": "MysqlAsyncSadLock",
    },
    "postgresql": {
        "module": ".lock.postgresql",
        "package": "${package}",  # module name relative to the package
        "class": "PostgresqlAsyncSadLock",
    },
}


def find_lock_class(engine_name, is_asyncio=False) -> Type[Union[BaseSadLock, BaseAsyncSadLock]]:
    reg = ASYNCIO_REGISTRY if is_asyncio else REGISTRY
    conf = reg[engine_name]
    package = conf.get("package")
    if package:
        package = Template(package).safe_substitute(package=__package__)
    module = import_module(conf["module"], package)
    class_ = getattr(module, conf["class"])
    return class_
