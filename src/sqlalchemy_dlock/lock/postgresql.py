from collections import deque
from time import sleep, time
from typing import Any, Callable, Optional, Union

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..statement.postgresql import STATEMENTS
from ..baselock import BaseSadLock, TConnectionOrSession
from ..utils import ensure_int64, to_int64_key

SLEEP_INTERVAL_DEFAULT = 1

TConvertFunction = Callable[[Any], int]


class SadLock(BaseSadLock):
    """PostgreSQL advisory lock

    .. seealso:: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
    """

    def __init__(
        self,
        connection_or_session: TConnectionOrSession,
        key,
        level: Optional[str] = None,
        interval: Union[float, int, None] = None,
        convert: Optional[TConvertFunction] = None,
    ):
        """
        PostgreSQL advisory lock requires the key given by ``INT64``.

        - When `key` is :class:`int`, the constructor tries to ensure it to be ``INT64``.
          :class:`OverflowError` is raised if too big or too small for an ``INT64``.

        - When `key` is :class:`str` or :class:`bytes` or alike,
          the constructor calculates its checksum by :func:`hashlib.blake2b`,
          and takes the hash result integer value as actual key.

        - Or you can specify a ``convert`` function to that argument.
          The function is like::

            def convert(val: Any) -> int:
                # do something ...
                return integer

        The ``level`` argument should be one of:

        - ``"session"`` (Omitted): locks an application-defined resource.
            If another session already holds a lock on the same resource identifier, this function will wait until the resource becomes available.
            The lock is exclusive. Multiple lock requests stack, so that if the same resource is locked three times it must then be unlocked three times to be released for other sessions' use.

        - ``"shared"``: works the same as session level lock, except the lock can be shared with other sessions requesting shared locks.
            Only would-be exclusive lockers are locked out.

        - ``"transaction"``: works the same as session level lock, except the lock is automatically released at the end of the current transaction and cannot be released explicitly.

        .. attention::

            PostgreSQL's advisory lock has no timeout mechanism in itself.
            When ``timeout`` is a non-negative number, we simulate it by **looping** and **sleeping**.

            The ``interval`` argument specifies the sleep seconds, whose default is ``1``.

            That is: actual timeout won't be precise when ``interval`` is big,
            while small ``interval`` will cause high CPU usage and frequent SQL execution.
        """
        if convert:
            key = ensure_int64(convert(key))
        elif isinstance(key, int):
            key = ensure_int64(key)
        else:
            key = to_int64_key(key)
        #
        self._interval = SLEEP_INTERVAL_DEFAULT if interval is None else interval
        self._level = level or "session"
        try:
            self._stmt_dict = STATEMENTS[self._level]
        except KeyError:
            raise ValueError(f"Value of `level` must be in {list(STATEMENTS.keys())}")
        #
        super().__init__(connection_or_session, key)

    def acquire(
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
                stmt = self._stmt_dict["lock"].params(key=self._key)
                r = self.connection_or_session.execute(stmt)
                deque(r, maxlen=0)
                self._acquired = True
            else:
                # negative value for `timeout` are equivalent to a `timeout` of zero.
                if timeout < 0:
                    timeout = 0
                interval = self._interval if interval is None else interval
                if interval < 0:  # pragma: no cover
                    raise ValueError("interval must not be smaller than 0")
                stmt = self._stmt_dict["trylock"].params(key=self._key)
                ts_begin = time()
                while True:
                    r = self.connection_or_session.execute(stmt)
                    if r.scalar_one():  # succeed
                        self._acquired = True
                        break
                    if time() - ts_begin > timeout:  # expired
                        break
                    sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            stmt = self._stmt_dict["trylock"].params(key=self._key)
            ret_val = self.connection_or_session.execute(stmt).scalar_one()
            self._acquired = bool(ret_val)
        #
        return self._acquired

    def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        stmt = self._stmt_dict["unlock"].params(key=self._key)
        ret_val = self.connection_or_session.execute(stmt).scalar_one()
        if ret_val:
            self._acquired = False
        else:
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self._key!r} was not held.")

    @property
    def level(self) -> str:
        return self._level
