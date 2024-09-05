import asyncio
from time import time
from typing import Union
from warnings import warn

from ...exceptions import SqlAlchemyDLockDatabaseError
from ...lock.postgresql import PostgresqlSadLockMixin
from ...statement.postgresql import SLEEP_INTERVAL_DEFAULT, SLEEP_INTERVAL_MIN
from ..types import TAsyncConnectionOrSession
from .base import BaseAsyncSadLock


class PostgresqlAsyncSadLock(PostgresqlSadLockMixin, BaseAsyncSadLock[int]):
    def __init__(self, connection_or_session: TAsyncConnectionOrSession, key, **kwargs):
        PostgresqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseAsyncSadLock.__init__(self, connection_or_session, self._actual_key, **kwargs)

    async def acquire(
        self,
        block: bool = True,
        timeout: Union[float, int, None] = None,
        interval: Union[float, int, None] = None,
        *args,
        **kwargs,
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
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self.key!r} was not held.")
