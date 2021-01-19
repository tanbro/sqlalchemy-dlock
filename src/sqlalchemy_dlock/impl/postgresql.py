from hashlib import blake2b
from sys import byteorder
from textwrap import dedent
from time import sleep, time
from typing import Any, Callable, Optional, Union

from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..sessionlevellock import AbstractSessionLevelLock

INT8_MAX = +0x7fff_ffff_ffff_ffff  # max of signed int64: 2**63-1
INT8_MIN = -0x8000_0000_0000_0000  # min of signed int64: -2**63

SLEEP_INTERVAL_DEFAULT = 1

STMT_LOCK = text(dedent('''
SELECT pg_advisory_lock(:key)
''').strip())

STMT_TRY_LOCK = text(dedent('''
SELECT pg_try_advisory_lock(:key)
''').strip())

STMT_UNLOCK = text(dedent('''
SELECT  pg_advisory_unlock(:key)
''').strip())


TConvertFunction = Callable[[Any], int]


def default_convert(key: Union[bytes, str]) -> int:
    if isinstance(key, str):
        key = key.encode()
    if isinstance(key, bytes):
        digest = blake2b(key, digest_size=8).digest()
        result = int.from_bytes(digest, byteorder, signed=True)
    else:
        raise TypeError('%s'.format(type(key)))
    return ensure_int8(result)


def ensure_int8(i: int) -> int:
    if i > INT8_MAX:
        i = int.from_bytes(
            i.to_bytes(8, byteorder, signed=False),
            byteorder, signed=True
        )
    elif i < INT8_MIN:
        raise OverflowError('int too small to convert')
    return i


class SessionLevelLock(AbstractSessionLevelLock):
    """PostgreSQL advisory lock

    .. attention:: A lock can be acquired multiple times by its owning process

    :ref: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
    """
    def __init__(self,
                 connection: Connection,
                 key,
                 *,
                 convert: Optional[TConvertFunction] = None,
                 interval: Union[float, int, None] = None
                 ):
        """
        PostgreSQL advisory lock requires the key given by ``INT8``

        - When ``key`` is :class:`int`, the constructor ensures it to be ``INT8``
        - When ``key`` is :class:`str` or :class:`bytes`,
          the constructor calculates its 8-bytes hash code with :func:`hashlib.blake2b`,
          and takes the code as actual key.
        - Or you can specify a custom function in ``convert`` argument

        PostgreSQL's advisory lock has no timeout.
        We simulate it in a loop with sleep delay.
        The ``interval`` parameter specifies the sleep interval in second.
        It's default value is ``1``
        """
        if convert:
            key = convert(key)
        else:
            if isinstance(key, (bytes, str)):
                key = default_convert(key)
        if not isinstance(key, int):
            raise TypeError(
                'PostgreSQL advisory lock requires the key given by integer')
        key = ensure_int8(key)
        #
        if interval is None:
            interval = SLEEP_INTERVAL_DEFAULT
        self._interval = interval
        #
        super().__init__(connection, key)

    def acquire(self, blocking: bool = True, timeout: int = -1, interval: Union[float, int, None] = None) -> bool:
        if self._acquired:
            raise RuntimeError('invoked on a locked lock')
        if blocking:
            if timeout < 0:
                stmt = STMT_LOCK.params(key=self.key)
                self.connection.execute(stmt).fetchall()
                self._acquired = True
            else:
                if interval is None:
                    interval = self._interval
                begin_ts = time()
                while True:
                    stmt = STMT_TRY_LOCK.params(key=self.key)
                    ret_val = self.connection.execute(stmt).scalar()
                    if ret_val:  # succeed
                        self._acquired = True
                        break
                    if time() - begin_ts > timeout:  # expired
                        break
                    sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            stmt = STMT_TRY_LOCK.params(key=self.key)
            ret_val = self.connection.execute(stmt).scalar()
            self._acquired = bool(ret_val)
        #
        return self._acquired

    def release(self):
        if not self._acquired:
            raise RuntimeError('invoked on an unlocked lock')
        stmt = STMT_UNLOCK.params(key=self.key)
        ret_val = self.connection.execute(stmt).scalar()
        if ret_val:
            self._acquired = False
        else:
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                'PostgreSQL advisory lock "{}" was not held.'.format(self._key))
