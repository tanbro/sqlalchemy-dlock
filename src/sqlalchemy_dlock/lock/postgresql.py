import sys
from time import sleep, time
from typing import Any, Callable, Optional, Union
from warnings import warn

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..statement.postgresql import (
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
from ..utils import ensure_int64, to_int64_key
from .base import BaseSadLock

if sys.version_info < (3, 12):  # pragma: no cover
    from .._sa_types_backward import TConnectionOrSession
else:  # pragma: no cover
    from .._sa_types import TConnectionOrSession


class PostgresqlSadLockMixin:
    """A Mix-in class for PostgreSQL advisory lock"""

    def __init__(
        self, *, key, shared: bool = False, xact: bool = False, convert: Optional[Callable[[Any], int]] = None, **kwargs
    ):
        """
        Args:
            key: PostgreSQL advisory lock requires the key given by ``INT64``.

                * When ``key`` is :class:`int`, the constructor tries to ensure it to be ``INT64``.
                  :class:`OverflowError` is raised if too big or too small for that.

                * When ``key`` is :class:`str` or :class:`bytes` or alike, the constructor calculates its checksum by :func:`hashlib.blake2b`, and takes the hash result integer value as actual key.

                * Or you can specify a ``convert`` function to that argument::

                    def convert(val: Any) -> int:
                        int64_key: int = do_sth(val)
                        return int64_key

            shared: for :attr:`.shared`
            xact: for :attr:`.xact`
            convert: Custom function to covert ``key`` to required data type.
        """  # noqa: E501
        if convert:
            key = ensure_int64(convert(key))
        elif isinstance(key, int):
            key = ensure_int64(key)
        else:
            key = to_int64_key(key)
        self._actual_key = key
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

    @property
    def shared(self):
        """Is the advisory lock shared or exclusive"""
        return self._shared

    @property
    def xact(self):
        """Is the advisory lock transaction level or session level"""
        return self._xact


class PostgresqlSadLock(BaseSadLock, PostgresqlSadLockMixin):
    """A distributed lock implemented by PostgreSQL advisory lock

    See also:
        https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS

    Tip:
        Locks can be either shared or exclusive: a shared lock does not conflict with other shared locks on the same resource, only with exclusive locks.
        Locks can be taken at session level (so that they are held until released or the session ends) or at transaction level (so that they are held until the current transaction ends; there is no provision for manual release).
        Multiple session-level lock requests stack, so that if the same resource identifier is locked three times there must then be three unlock requests to release the resource in advance of session end.
    """

    def __init__(self, connection_or_session: TConnectionOrSession, key, **kwargs):
        """
        Args:
            connection_or_session: see :attr:`.BaseSadLock.connection_or_session`
            key: see :attr:`.BaseSadLock.key`
            shared: see :attr:`.PostgresqlSadLockMixin.shared`
            xact: see :attr:`.PostgresqlSadLockMixin.xact`
            convert: see :class:`.PostgresqlSadLockMixin`
            **kwargs: other named parameters pass to :class:`.BaseSadLock` and :class:`.PostgresqlSadLockMixin`
        """  # noqa: E501
        PostgresqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseSadLock.__init__(self, connection_or_session, self._actual_key, **kwargs)

    def acquire(
        self,
        block: bool = True,
        timeout: Union[float, int, None] = None,
        interval: Union[float, int, None] = None,
    ) -> bool:
        """
        See Also:
            :meth:`.BaseSadLock.acquire`

        Attention:
            PostgreSQL's advisory lock has no timeout mechanism in itself.
            When ``timeout`` is a non-negative number, we simulate it by **looping** and **sleeping**.

            The ``interval`` argument specifies the sleep seconds(``1`` by default).

            That is:
                The actual timeout won't be precise when ``interval`` is big;
                while small ``interval`` will cause high CPU usage and frequent SQL execution.
        """  # noqa: E501
        if self._acquired:
            raise ValueError("invoked on a locked lock")
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                _ = self.connection_or_session.execute(self._stmt_lock).all()
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
                    ret_val = self.connection_or_session.execute(self._stmt_try_lock).scalar_one()
                    if ret_val:  # succeed
                        self._acquired = True
                        break
                    if time() - ts_begin > timeout:  # expired
                        break
                    sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            ret_val = self.connection_or_session.execute(self._stmt_try_lock).scalar_one()
            self._acquired = bool(ret_val)
        #
        return self._acquired

    def release(self):
        if self._stmt_unlock is None:
            warn(
                "PostgreSQL transaction level advisory locks are held until the current transaction ends; there is no provision for manual release.",
                RuntimeWarning,
            )
            return
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        ret_val = self.connection_or_session.execute(self._stmt_unlock).scalar_one()
        if ret_val:
            self._acquired = False
        else:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self.key!r} was not held.")
