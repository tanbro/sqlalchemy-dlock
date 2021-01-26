from sys import byteorder
from textwrap import dedent
from time import sleep, time
from typing import Any, Callable, Optional, Union

import libscrc
from sqlalchemy import text
from sqlalchemy.engine import Connection  # noqa

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..sessionlevellock import AbstractSessionLevelLock

INT64_MAX = +0x7fff_ffff_ffff_ffff  # max of signed int64: 2**63-1
INT64_MIN = -0x8000_0000_0000_0000  # min of signed int64: -2**63

SLEEP_INTERVAL_DEFAULT = 1

LOCK = text(dedent('''
SELECT pg_advisory_lock(:key)
''').strip())

TRY_LOCK = text(dedent('''
SELECT pg_try_advisory_lock(:key)
''').strip())

UNLOCK = text(dedent('''
SELECT pg_advisory_unlock(:key)
''').strip())

TConvertFunction = Callable[[Any], int]


def default_convert(key: Union[bytearray, bytes, str]) -> int:
    if isinstance(key, str):
        key = key.encode()
    if isinstance(key, (bytearray, bytes)):
        result = libscrc.iso(key)  # type: ignore
    else:
        raise TypeError('{}'.format(type(key)))
    return ensure_int64(result)


def ensure_int64(i: int) -> int:
    if i > INT64_MAX:
        i = int.from_bytes(
            i.to_bytes(8, byteorder, signed=False),
            byteorder, signed=True
        )
    elif i < INT64_MIN:
        raise OverflowError('int too small to convert')
    return i


class SessionLevelLock(AbstractSessionLevelLock):
    """PostgreSQL advisory lock

    .. seealso:: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
    """

    def __init__(self,
                 connection: Connection,
                 key,
                 *,
                 convert: Optional[TConvertFunction] = None,
                 interval: Union[float, int, None] = None,
                 **kwargs  # noqa
                 ):
        """
        PostgreSQL advisory lock requires the key given by ``INT64``.

        - When `key` is :class:`int`, the constructor ensures it to be ``INT64``.
          :class:`OverflowError` is raised if too big or too small for an ``INT64``.

        - When `key` is :class:`str` or :class:`bytes`,
          the constructor calculates its checksum using *CRC-64(ISO)*,
          and takes the checksum as actual key.
          
          .. seealso:: https://en.wikipedia.org/wiki/Cyclic_redundancy_check

        - Or you can specify a `convert` function to that argument.
          The function is like::

            def convert(val: Any) -> int:
                # do something ...
                return integer

        .. tip::

            PostgreSQL's advisory lock has no timeout mechanism in itself.
            When `timeout` is a non-negative number, we simulate it by looping and sleeping.
            The `interval` argument specifies the sleep seconds, whose default is ``1``.
        """
        if convert:
            key = ensure_int64(convert(key))
        elif isinstance(key, int):
            key = ensure_int64(key)
        else:
            key = default_convert(key)
        #
        self._interval = SLEEP_INTERVAL_DEFAULT if interval is None else interval
        #
        super().__init__(connection, key)

    def acquire(self,
                block: bool = True,
                timeout: Union[float, int, None] = None,
                *,
                interval: Union[float, int, None] = None,
                **kwargs  # noqa
                ) -> bool:
        if self._acquired:
            raise ValueError('invoked on a locked lock')
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                stmt = LOCK.params(key=self.key)
                self.connection.execute(stmt).fetchall()
                self._acquired = True
            else:
                if timeout < 0:
                    # negative value for `timeout` are equivalent to a `timeout` of zero.
                    timeout = 0
                if interval is None:
                    interval = self._interval
                if interval < 0:
                    raise ValueError('interval must not be smaller than 0')
                stmt = TRY_LOCK.params(key=self.key)
                ts_begin = time()
                while True:
                    ret_val = self.connection.execute(stmt).scalar()
                    if ret_val:  # succeed
                        self._acquired = True
                        break
                    if time() - ts_begin > timeout:  # expired
                        break
                    sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            stmt = TRY_LOCK.params(key=self.key)
            ret_val = self.connection.execute(stmt).scalar()
            self._acquired = bool(ret_val)
        #
        return self._acquired

    def release(self, **kwargs):  # noqa
        if not self._acquired:
            raise ValueError('invoked on an unlocked lock')
        stmt = UNLOCK.params(key=self.key)
        ret_val = self.connection.execute(stmt).scalar()
        if ret_val:
            self._acquired = False
        else:
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                'PostgreSQL advisory lock "{}" was not held.'.format(self._key))
