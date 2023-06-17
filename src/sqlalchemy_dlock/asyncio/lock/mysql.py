from typing import Any, Callable, Optional, Union

from ...exceptions import SqlAlchemyDLockDatabaseError
from ...statement.mysql import STATEMENTS
from ..baselock import BaseAsyncSadLock, TAsyncConnectionOrSession

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


class AsyncSadLock(BaseAsyncSadLock):
    def __init__(
        self,
        connection_or_session: TAsyncConnectionOrSession,
        key,
        convert: Optional[TConvertFunction] = None,
    ):
        if convert:
            key = convert(key)
        elif not isinstance(key, str):
            key = default_convert(key)
        if not isinstance(key, str):
            raise TypeError("MySQL named lock requires the key given by string")
        if len(key) > MYSQL_LOCK_NAME_MAX_LENGTH:
            raise ValueError(f"MySQL enforces a maximum length on lock names of {MYSQL_LOCK_NAME_MAX_LENGTH} characters.")
        #
        super().__init__(connection_or_session, key)

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
        stmt = STATEMENTS["lock"].params(str=self._key, timeout=timeout)
        r = await self.connection_or_session.stream(stmt)
        ret_val = (await r.one())[0]

        if ret_val == 1:
            self._acquired = True
        elif ret_val == 0:
            pass  # 直到超时也没有成功锁定
        elif ret_val is None:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"An error occurred while attempting to obtain the lock {self._key!r}")
        else:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"GET_LOCK({self._key!r}, {timeout}) returns {ret_val}")
        return self._acquired

    async def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        stmt = STATEMENTS["unlock"].params(str=self._key)
        r = await self.connection_or_session.stream(stmt)
        ret_val = (await r.one())[0]
        if ret_val == 1:
            self._acquired = False
        elif ret_val == 0:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                f"The named lock {self._key!r} was not established by this thread, " "and the lock is not released."
            )
        elif ret_val is None:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                f"The named lock {self._key!r} did not exist, "
                "was never obtained by a call to GET_LOCK(), "
                "or has previously been released."
            )
        else:
            raise SqlAlchemyDLockDatabaseError(f"RELEASE_LOCK({self._key!r}) returns {ret_val}")
