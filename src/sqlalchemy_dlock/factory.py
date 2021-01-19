from importlib import import_module
from sqlalchemy.engine import Connection

from .sessionlevellock import AbstractSessionLevelLock
from .utils import safe_name

__all__ = ['make_session_level_lock']


def make_session_level_lock(
    connection: Connection,
    key,
    *args, **kwargs
) -> AbstractSessionLevelLock:
    name = safe_name(connection.engine.name)
    mod = import_module('..impl.{}'.format(name), __name__)
    lock_cls = getattr(mod, 'SessionLevelLock')
    return lock_cls(connection, key, *args, **kwargs)
