import sys
from typing import Any, Callable, Union

from ...exceptions import SqlAlchemyDLockDatabaseError
from ...lock.mysql import MysqlSadLockMixin
from ...statement.mysql import LOCK, UNLOCK
from .base import BaseAsyncSadLock

if sys.version_info < (3, 12):  # pragma: no cover
    from .._sa_types_backward import TAsyncConnectionOrSession
else:  # pragma: no cover
    from .._sa_types import TAsyncConnectionOrSession

MYSQL_LOCK_NAME_MAX_LENGTH = 64

TConvertFunction = Callable[[Any], str]


def default_convert(key: Union[bytearray, bytes, int, float]) -> str:
    if isinstance(key, (bytearray, bytes)):
        result = key.decode()
    elif isinstance(key, (int, float)):
        result = str(key)
    else:
        raise TypeError(f"{type(key)}")
    return result


class MysqlAsyncSadLock(BaseAsyncSadLock, MysqlSadLockMixin):
    def __init__(self, connection_or_session: TAsyncConnectionOrSession, key, **kwargs):
        MysqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseAsyncSadLock.__init__(self, connection_or_session, self._actual_key, **kwargs)

    async def acquire(self, block: bool = True, timeout: Union[float, int, None] = None) -> bool:
        if self._acquired:
            raise ValueError("invoked on a locked lock")
        if block:
            # None: set the timeout period to infinite.
            if timeout is None:
                timeout = -1
            # negative value for `timeout` are equivalent to a `timeout` of zero
            elif timeout < 0:
                timeout = 0
        else:
            timeout = 0
        stmt = LOCK.params(str=self.key, timeout=timeout)
        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()
        if ret_val == 1:
            self._acquired = True
        elif ret_val == 0:
            pass  # 直到超时也没有成功锁定
        elif ret_val is None:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"An error occurred while attempting to obtain the lock {self.key!r}")
        else:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"GET_LOCK({self.key!r}, {timeout}) returns {ret_val}")
        return self._acquired

    async def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        stmt = UNLOCK.params(str=self.key)
        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()
        if ret_val == 1:
            self._acquired = False
        elif ret_val == 0:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                f"The named lock {self.key!r} was not established by this thread, " "and the lock is not released."
            )
        elif ret_val is None:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                f"The named lock {self.key!r} did not exist, "
                "was never obtained by a call to GET_LOCK(), "
                "or has previously been released."
            )
        else:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"RELEASE_LOCK({self.key!r}) returns {ret_val}")
