import asyncio
import sys
from time import time
from typing import Any, Callable, Optional, Union
from warnings import warn

from ...exceptions import SqlAlchemyDLockDatabaseError
from ...statement.postgresql import (
    LOCK,
    LOCK_SHARED,
    LOCK_XACT,
    LOCK_XACT_SHARED,
    SLEEP_INTERVAL_DEFAULT,
    SLEEP_INTERVAL_MIN,
    TRY_LOCK,
    TRY_LOCK_SHARED,
    TRY_LOCK_XACT,
    TRY_LOCK_XACT_SHARED,
    UNLOCK,
    UNLOCK_SHARED,
)
from ...utils import ensure_int64, to_int64_key
from .base import BaseAsyncSadLock

if sys.version_info < (3, 12):  # pragma: no cover
    from .._sa_types_backward import TAsyncConnectionOrSession
else:  # pragma: no cover
    from .._sa_types import TAsyncConnectionOrSession


class PostgresqlAsyncSadLock(BaseAsyncSadLock):
    def __init__(
        self,
        connection_or_session: TAsyncConnectionOrSession,
        key,
        /,
        shared: bool = False,
        xact: bool = False,
        convert: Optional[Callable[[Any], int]] = None,
        **kwargs,
    ):
        if convert:
            key = ensure_int64(convert(key))
        elif isinstance(key, int):
            key = ensure_int64(key)
        else:
            key = to_int64_key(key)
        #
        self._shared = bool(shared)
        self._xact = bool(xact)
        #
        if not shared and not xact:
            self._stmt_lock = LOCK.params(key=key)
            self._stmt_try_lock = TRY_LOCK.params(key=key)
            self._stmt_unlock = UNLOCK.params(key=key)
        elif shared and not xact:
            self._stmt_lock = LOCK_SHARED.params(key=key)
            self._stmt_try_lock = TRY_LOCK_SHARED.params(key=key)
            self._stmt_unlock = UNLOCK_SHARED.params(key=key)
        elif not shared and xact:
            self._stmt_lock = LOCK_XACT.params(key=key)
            self._stmt_try_lock = TRY_LOCK_XACT.params(key=key)
            self._stmt_unlock = None
        else:
            self._stmt_lock = LOCK_XACT_SHARED.params(key=key)
            self._stmt_try_lock = TRY_LOCK_XACT_SHARED.params(key=key)
            self._stmt_unlock = None
        #
        super().__init__(connection_or_session, key, **kwargs)

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
                _ = (await self.connection_or_session.execute(self._stmt_lock)).all()
                self._acquired = True
            else:
                # negative value for `timeout` are equivalent to a `timeout` of zero.
                if timeout < 0:
                    timeout = 0
                interval = SLEEP_INTERVAL_DEFAULT if interval is None else interval
                if interval < SLEEP_INTERVAL_MIN:  # pragma: no cover
                    raise ValueError("interval too small")
                ts_begin = time()
                while True:
                    ret_val = (await self.connection_or_session.execute(self._stmt_try_lock)).scalar_one()
                    if ret_val:  # succeed
                        self._acquired = True
                        break
                    if time() - ts_begin > timeout:  # expired
                        break
                    await asyncio.sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            ret_val = (await self.connection_or_session.execute(self._stmt_try_lock)).scalar_one()
            self._acquired = bool(ret_val)
        #
        return self._acquired

    async def release(self):
        if self._stmt_unlock is None:
            warn(
                "PostgreSQL transaction level advisory locks are held until the current transaction ends; there is no provision for manual release.",
                RuntimeWarning,
            )
            return
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        ret_val = (await self.connection_or_session.execute(self._stmt_unlock)).scalar_one()
        if ret_val:
            self._acquired = False
        else:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self._key!r} was not held.")

    @property
    def shared(self):
        """Is the advisory lock shared or exclusive"""
        return self._shared

    @property
    def xact(self):
        """Is the advisory lock transaction level or session level"""
        return self._xact
