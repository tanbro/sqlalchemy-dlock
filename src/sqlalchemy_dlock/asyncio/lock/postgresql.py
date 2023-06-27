import asyncio
from time import time
from typing import Any, Callable, Optional, Union

from ...exceptions import SqlAlchemyDLockDatabaseError
from ...statement.postgresql import (
    SLEEP_INTERVAL_DEFAULT,
    SLEEP_INTERVAL_MIN,
    make_lock_stmt_mapping,
)
from ...utils import ensure_int64, to_int64_key
from .base import AsyncBaseSadLock, TAsyncConnectionOrSession

TConvertFunction = Callable[[Any], int]


class AsyncPostgresqlSadLock(AsyncBaseSadLock):
    def __init__(
        self,
        connection_or_session: TAsyncConnectionOrSession,
        key,
        level: Optional[str] = None,
        convert: Optional[TConvertFunction] = None,
    ):
        if convert:
            key = ensure_int64(convert(key))
        elif isinstance(key, int):
            key = ensure_int64(key)
        else:
            key = to_int64_key(key)
        #
        level = (level or "session").strip().lower()
        self._lock_stmt_mapping = make_lock_stmt_mapping(level)
        self._level = level
        #
        super().__init__(connection_or_session, key)

    async def acquire(
        self,
        block: bool = True,
        timeout: Union[float, int, None] = None,
        interval: Union[float, int, None] = None,
    ) -> bool:
        if self._acquired:
            raise ValueError("invoked on a locked lock")
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                stmt = self._lock_stmt_mapping["lock"].params(key=self._key)
                _ = (await self.connection_or_session.execute(stmt)).all()
                self._acquired = True
            else:
                # negative value for `timeout` are equivalent to a `timeout` of zero.
                if timeout < 0:
                    timeout = 0
                interval = SLEEP_INTERVAL_DEFAULT if interval is None else interval
                if interval < SLEEP_INTERVAL_MIN:  # pragma: no cover
                    raise ValueError("interval too small")
                stmt = self._lock_stmt_mapping["try_lock"].params(key=self._key)
                ts_begin = time()
                while True:
                    ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()
                    if ret_val:  # succeed
                        self._acquired = True
                        break
                    if time() - ts_begin > timeout:  # expired
                        break
                    await asyncio.sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            stmt = self._lock_stmt_mapping["try_lock"].params(key=self._key)
            ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()
            self._acquired = bool(ret_val)
        #
        return self._acquired

    async def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        stmt = self._lock_stmt_mapping["unlock"].params(key=self._key)
        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()
        if ret_val:
            self._acquired = False
        else:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self._key!r} was not held.")

    @property
    def level(self) -> str:
        return self._level
