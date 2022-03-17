from textwrap import dedent
from typing import Any, Callable, Optional, Union

from sqlalchemy import text

from ...exceptions import SqlAlchemyDLockDatabaseError
from ..types import BaseAsyncSadLock, TAsyncConnectionOrSession

MYSQL_LOCK_NAME_MAX_LENGTH = 64

GET_LOCK = text(dedent('''
SELECT GET_LOCK(:str, :timeout)
''').strip())

RELEASE_LOCK = text(dedent('''
SELECT RELEASE_LOCK(:str)
''').strip())

TConvertFunction = Callable[[Any], str]


def default_convert(key: Union[bytearray, bytes, int, float]) -> str:
    if isinstance(key, (bytearray, bytes)):
        result = key.decode()
    elif isinstance(key, (int, float)):
        result = str(key)
    else:
        raise TypeError('{}'.format(type(key)))
    return result


class AsyncSadLock(BaseAsyncSadLock):
    def __init__(self,
                 connection_or_session: TAsyncConnectionOrSession,
                 key,
                 convert: Optional[TConvertFunction] = None,
                 *args, **kwargs
                 ):
        if convert:
            key = convert(key)
        elif not isinstance(key, str):
            key = default_convert(key)
        if not isinstance(key, str):
            raise TypeError(
                'MySQL named lock requires the key given by string')
        if len(key) > MYSQL_LOCK_NAME_MAX_LENGTH:
            raise ValueError(
                'MySQL enforces a maximum length on lock names of {} characters.'.format(
                    MYSQL_LOCK_NAME_MAX_LENGTH))
        #
        super().__init__(connection_or_session, key)

    async def acquire(self,
                      block: bool = True,
                      timeout: Union[float, int, None] = None,
                      *args, **kwargs
                      ) -> bool:
        if self._acquired:
            raise ValueError('invoked on a locked lock')
        if block:
            # None: set the timeout period to infinite.
            if timeout is None:
                timeout = -1
            # negative value for `timeout` are equivalent to a `timeout` of zero
            elif timeout < 0:
                timeout = 0
        else:
            timeout = 0
        stmt = GET_LOCK.params(str=self._key, timeout=timeout)
        r = await self.connection_or_session.stream(stmt)
        ret_val = (await r.one())[0]

        if ret_val == 1:
            self._acquired = True
        elif ret_val == 0:
            pass  # 直到超时也没有成功锁定
        elif ret_val is None:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(
                'An error occurred while attempting to obtain the lock "{}"'.format(self._key))
        else:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(
                'GET_LOCK("{}", {}) returns {}'.format(self._key, timeout, ret_val))
        return self._acquired

    async def release(self, *args, **kwargs):
        if not self._acquired:
            raise ValueError('invoked on an unlocked lock')
        stmt = RELEASE_LOCK.params(str=self._key)
        r = await self.connection_or_session.stream(stmt)
        ret_val = (await r.one())[0]
        if ret_val == 1:
            self._acquired = False
        elif ret_val == 0:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                'The named lock "{}" was not established by this thread, '
                'and the lock is not released.'.format(self._key))
        elif ret_val is None:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                'The named lock "{}" did not exist, '
                'was never obtained by a call to GET_LOCK(), '
                'or has previously been released.'.format(self._key)
            )
        else:
            raise SqlAlchemyDLockDatabaseError(
                'RELEASE_LOCK("{}") returns {}'.format(self._key, ret_val))
