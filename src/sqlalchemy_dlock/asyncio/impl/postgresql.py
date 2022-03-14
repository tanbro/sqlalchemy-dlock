import asyncio
from collections import deque
from textwrap import dedent
from time import time
from typing import Any, Callable, Optional, Union

from sqlalchemy import text

from ...exceptions import SqlAlchemyDLockDatabaseError
from ...utils import ensure_int64, to_int64_key
from ..types import BaseAsyncSadLock, TAsyncConnectionOrSession

SLEEP_INTERVAL_DEFAULT = 1

STATEMENTS = {
    'session': {
        'lock': text(dedent('''
            SELECT pg_advisory_lock(:key)
            ''').strip()),
        'trylock': text(dedent('''
            SELECT pg_try_advisory_lock(:key)
            ''').strip()),
        'unlock': text(dedent('''
            SELECT pg_advisory_unlock(:key)
            ''').strip()),
    },
    'shared': {
        'lock': text(dedent('''
            SELECT pg_advisory_lock_shared(:key)
            ''').strip()),
        'trylock': text(dedent('''
            SELECT pg_try_advisory_lock_shared(:key)
            ''').strip()),
        'unlock': text(dedent('''
            SELECT pg_advisory_unlock_shared(:key)
            ''').strip()),
    },
    'transaction': {
        'lock': text(dedent('''
            SELECT pg_advisory_xact_lock(:key)
            ''').strip()),
        'trylock': text(dedent('''
            SELECT pg_try_advisory_xact_lock(:key)
            ''').strip()),
        'unlock': text(dedent('''
            SELECT pg_advisory_xact_unlock(:key)
            ''').strip()),
    },
}


TConvertFunction = Callable[[Any], int]


class AsyncSadLock(BaseAsyncSadLock):
    def __init__(self,
                 connection_or_session: TAsyncConnectionOrSession,
                 key,
                 level: Optional[str] = None,
                 interval: Union[float, int, None] = None,
                 convert: Optional[TConvertFunction] = None,
                 *args, **kwargs
                 ):
        if convert:
            key = ensure_int64(convert(key))
        elif isinstance(key, int):
            key = ensure_int64(key)
        else:
            key = to_int64_key(key)
        #
        self._interval = SLEEP_INTERVAL_DEFAULT if interval is None else interval
        self._level = level or 'session'
        self._stmt_dict = STATEMENTS[self._level]
        #
        super().__init__(connection_or_session, key)

    async def acquire(self,
                      block: bool = True,
                      timeout: Union[float, int, None] = None,
                      interval: Union[float, int, None] = None,
                      *args, **kwargs
                      ) -> bool:
        if self._acquired:
            raise ValueError('invoked on a locked lock')
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                stmt = self._stmt_dict['lock'].params(key=self._key)
                r = await self.connection_or_session.execute(stmt)
                deque(r, maxlen=0)
                self._acquired = True
            else:
                # negative value for `timeout` are equivalent to a `timeout` of zero.
                if timeout < 0:
                    timeout = 0
                interval = self._interval if interval is None else interval
                if interval < 0:
                    raise ValueError('interval must not be smaller than 0')
                stmt = self._stmt_dict['trylock'].params(key=self._key)
                ts_begin = time()
                while True:
                    r = await self.connection_or_session.stream(stmt)
                    ret_val = (await r.one())[0]
                    if ret_val:  # succeed
                        self._acquired = True
                        break
                    if time() - ts_begin > timeout:  # expired
                        break
                    await asyncio.sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            stmt = self._stmt_dict['trylock'].params(key=self._key)
            r = await self.connection_or_session.stream(stmt)
            ret_val = (await r.one())[0]
            self._acquired = bool(ret_val)
        #
        return self._acquired

    async def release(self, *args, **kwargs):
        if not self._acquired:
            raise ValueError('invoked on an unlocked lock')
        stmt = self._stmt_dict['unlock'].params(key=self._key)
        r = await self.connection_or_session.stream(stmt)
        ret_val = (await r.one())[0]
        if ret_val:
            self._acquired = False
        else:
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                'The advisory lock "{}" was not held.'.format(self._key))

    @property
    def level(self) -> str:
        return self._level
