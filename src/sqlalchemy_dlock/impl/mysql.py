from textwrap import dedent
from typing import Any, Callable, Optional, Union

from sqlalchemy import text
from sqlalchemy.engine import Connection  # noqa

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..sessionlevellock import AbstractSessionLevelLock

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


class SessionLevelLock(AbstractSessionLevelLock):
    """MySQL named-lock

    .. seealso:: https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html

    .. attention:: Multiple simultaneous locks can be acquired and GET_LOCK() does not release any existing locks
    """

    def __init__(self,
                 connection: Connection,
                 key,
                 *,
                 convert: Optional[TConvertFunction] = None,
                 **_
                 ):
        """
        MySQL named lock requires the key given by string.
        You can specify a custom function in ``convert`` argument, if your key is not :class:`str`
        """
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
        super().__init__(connection, key)

    def acquire(self,
                blocking: Optional[bool] = None,
                timeout: Union[float, int, None] = None,
                **_
                ) -> bool:
        if self._acquired:
            raise RuntimeError('invoked on a locked lock')
        if blocking is None:
            blocking = True
        if blocking:
            if timeout is None:
                timeout = -1
            else:
                timeout = round(timeout)
        else:
            timeout = 0
        stmt = GET_LOCK.params(str=self.key, timeout=timeout)
        ret_val = self.connection.execute(stmt).scalar()
        if ret_val == 1:
            self._acquired = True
        elif ret_val == 0:
            pass  # 直到超时也没有成功锁定
        elif ret_val is None:
            raise SqlAlchemyDLockDatabaseError(
                'An error occurred while attempting to obtain the lock "{}"'.format(self._key))
        else:
            raise SqlAlchemyDLockDatabaseError(
                'GET_LOCK("{}", {}) returns {}'.format(self._key, timeout, ret_val))
        return self._acquired

    def release(self, **_):
        if not self._acquired:
            raise RuntimeError('invoked on an unlocked lock')
        stmt = RELEASE_LOCK.params(str=self.key)
        ret_val = self.connection.execute(stmt).scalar()
        if ret_val == 1:
            self._acquired = False
        elif ret_val == 0:
            raise SqlAlchemyDLockDatabaseError(
                'The named lock "{}" was not established by this thread, '
                'and the lock is not released.'.format(self._key))
        elif ret_val is None:
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                'The named lock "{}" did not exist， was never obtained by a call to GET_LOCK()， '
                'or has previously been released.'.format(self._key)
            )
        else:
            raise SqlAlchemyDLockDatabaseError(
                'RELEASE_LOCK("{}") returns {}'.format(self._key, ret_val))
