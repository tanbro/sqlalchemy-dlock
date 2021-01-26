from textwrap import dedent
from time import time
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
    """

    def __init__(self,
                 connection: Connection,
                 key,
                 *,
                 convert: Optional[TConvertFunction] = None,
                 **kwargs  # noqa
                 ):
        """
        MySQL named lock requires the key given by string.

        If `key` is not a :class:`str`:

        - When :class:`int` or :class:`float`,
          the constructor converts it to :class:`str` directly::

            key = str(key)

        - When :class:`bytes`,
          the constructor tries to decode it with default encoding.

        - Or you can specify a `convert` function to that argument.
          The function is like::

            def convert(val: Any) -> str:
                # do something ...
                return string
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
                block: bool = True,
                timeout: Union[float, int, None] = None,
                **kwargs  # noqa
                ) -> bool:
        if self._acquired:
            raise RuntimeError('invoked on a locked lock')
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                timeout = -1
            elif timeout < 0:
                # negative value for `timeout` are equivalent to a `timeout` of zero
                timeout = 0
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

    def release(self, **kwargs):  # noqa
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
