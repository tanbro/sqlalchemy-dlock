import asyncio
import sys
from time import sleep, time
from typing import Any, Callable, Optional, TypeVar, Union
from warnings import catch_warnings, warn

if sys.version_info < (3, 12):  # pragma: no cover
    from typing_extensions import override
else:  # pragma: no cover
    from typing import override

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
from ..types import AsyncConnectionOrSessionT, ConnectionOrSessionT
from ..utils import ensure_int64, to_int64_key
from .base import BaseAsyncSadLock, BaseSadLock

KT = TypeVar("KT", bound=Any)


class PostgresqlSadLockMixin:
    """A Mix-in class for PostgreSQL advisory lock"""

    def __init__(
        self, *, key: KT, shared: bool = False, xact: bool = False, convert: Optional[Callable[[KT], int]] = None, **kwargs
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

            shared: :attr:`.shared`
            xact: :attr:`.xact`
            convert: Custom function to covert ``key`` to required data type.
        """  # noqa: E501
        if convert:
            self._actual_key = ensure_int64(convert(key))
        else:
            self._actual_key = to_int64_key(key)
        #
        self._shared = bool(shared)
        self._xact = bool(xact)
        #
        self._stmt_unlock = None
        if not shared and not xact:
            self._stmt_lock = LOCK.params(key=self._actual_key)
            self._stmt_try_lock = TRY_LOCK.params(key=self._actual_key)
            self._stmt_unlock = UNLOCK.params(key=self._actual_key)
        elif shared and not xact:
            self._stmt_lock = LOCK_SHARED.params(key=self._actual_key)
            self._stmt_try_lock = TRY_LOCK_SHARED.params(key=self._actual_key)
            self._stmt_unlock = UNLOCK_SHARED.params(key=self._actual_key)
        elif not shared and xact:
            self._stmt_lock = LOCK_XACT.params(key=self._actual_key)
            self._stmt_try_lock = TRY_LOCK_XACT.params(key=self._actual_key)
        else:
            self._stmt_lock = LOCK_XACT_SHARED.params(key=self._actual_key)
            self._stmt_try_lock = TRY_LOCK_XACT_SHARED.params(key=self._actual_key)

    @property
    def shared(self) -> bool:
        """Is the advisory lock shared or exclusive"""
        return self._shared

    @property
    def xact(self) -> bool:
        """Is the advisory lock transaction level or session level"""
        return self._xact

    @property
    def actual_key(self) -> int:
        """The actual key used in PostgreSQL advisory lock"""
        return self._actual_key


class PostgresqlSadLock(PostgresqlSadLockMixin, BaseSadLock[int]):
    """A distributed lock implemented by PostgreSQL advisory lock

    See also:
        https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS

    Tip:
        Locks can be either shared or exclusive: a shared lock does not conflict with other shared locks on the same resource, only with exclusive locks.
        Locks can be taken at session level (so that they are held until released or the session ends) or at transaction level (so that they are held until the current transaction ends; there is no provision for manual release).
        Multiple session-level lock requests stack, so that if the same resource identifier is locked three times there must then be three unlock requests to release the resource in advance of session end.
    """

    @override
    def __init__(self, connection_or_session: ConnectionOrSessionT, key, **kwargs):
        """
        Args:
            connection_or_session: see :attr:`.BaseSadLock.connection_or_session`
            key: :attr:`.BaseSadLock.key`
            shared: :attr:`.PostgresqlSadLockMixin.shared`
            xact: :attr:`.PostgresqlSadLockMixin.xact`
            convert: :class:`.PostgresqlSadLockMixin`
            **kwargs: other named parameters pass to :class:`.BaseSadLock` and :class:`.PostgresqlSadLockMixin`
        """  # noqa: E501
        PostgresqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    def acquire(
        self,
        block: bool = True,
        timeout: Union[float, int, None] = None,
        interval: Union[float, int, None] = None,
        *args,
        **kwargs,
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
                self.connection_or_session.execute(self._stmt_lock).all()
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

    @override
    def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        if self._stmt_unlock is None:
            warn(
                "PostgreSQL transaction level advisory locks are held until the current transaction ends; "
                "there is no provision for manual release.",
                RuntimeWarning,
            )
            return
        ret_val = self.connection_or_session.execute(self._stmt_unlock).scalar_one()
        if ret_val:
            self._acquired = False
        else:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self.key!r} was not held.")

    @override
    def close(self):
        if self._acquired:
            if sys.version_info < (3, 11):
                with catch_warnings():
                    return self.release()
            else:
                with catch_warnings(category=RuntimeWarning):
                    return self.release()


class PostgresqlAsyncSadLock(PostgresqlSadLockMixin, BaseAsyncSadLock[int]):
    @override
    def __init__(self, connection_or_session: AsyncConnectionOrSessionT, key, **kwargs):
        PostgresqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseAsyncSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
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

    @override
    async def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        if self._stmt_unlock is None:
            warn(
                "PostgreSQL transaction level advisory locks are held until the current transaction ends; "
                "there is no provision for manual release.",
                RuntimeWarning,
            )
            return
        ret_val = (await self.connection_or_session.execute(self._stmt_unlock)).scalar_one()
        if ret_val:
            self._acquired = False
        else:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self.key!r} was not held.")

    @override
    async def close(self):
        if self._acquired:
            if sys.version_info < (3, 11):
                with catch_warnings():
                    return await self.release()
            else:
                with catch_warnings(category=RuntimeWarning):
                    return await self.release()
