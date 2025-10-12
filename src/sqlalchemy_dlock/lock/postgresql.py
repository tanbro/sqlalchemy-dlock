import asyncio
import sys
from hashlib import blake2b
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
from ..typing import AsyncConnectionOrSessionT, ConnectionOrSessionT
from .base import AbstractLockMixin, BaseAsyncSadLock, BaseSadLock

ConvertibleKT = Union[bytes, bytearray, memoryview, str, int, float]
KT = Any
KTV = TypeVar("KTV", bound=KT)


class PostgresqlSadLockMixin(AbstractLockMixin[KTV, int]):
    """A Mix-in class for PostgreSQL advisory lock"""

    @override
    def __init__(
        self, *, key: KTV, convert: Optional[Callable[[KTV], int]] = None, shared: bool = False, xact: bool = False, **kwargs
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
        """
        if convert:
            self._actual_key = convert(key)
        else:
            self._actual_key = self.convert(key)
        self._actual_key = self.ensure_int64(self._actual_key)
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

    @override
    def get_actual_key(self) -> int:
        """The actual key used in MySQL named lock"""
        return self._actual_key

    @classmethod
    def convert(cls, k: ConvertibleKT) -> int:
        """The default key converter for PostgreSQL advisory lock"""
        if isinstance(k, int):
            return k
        if isinstance(k, str):
            d = k.encode()
        elif isinstance(k, (bytes, bytearray)):
            d = k
        elif isinstance(k, memoryview):
            d = k.tobytes()
        else:
            raise TypeError(type(k).__name__)
        return int.from_bytes(blake2b(d, digest_size=8).digest(), sys.byteorder, signed=True)

    @classmethod
    def ensure_int64(cls, i: int) -> int:
        """ensure the integer in PostgreSQL advisory lock's range (Signed INT64)

        * max of signed int64: ``2**63-1`` (``+0x7FFF_FFFF_FFFF_FFFF``)
        * min of signed int64: ``-2**63`` (``-0x8000_0000_0000_0000``)

        Returns:
            Signed int64 key
        """
        ## no force convert UINT greater than 2**63-1 to SINT
        # if i > 0x7FFF_FFFF_FFFF_FFFF:
        #     return int.from_bytes(i.to_bytes(8, byteorder, signed=False), byteorder, signed=True)
        if not isinstance(i, int):
            raise TypeError(f"int type expected, but actual type is {type(i).__name__}")
        if i > 0x7FFF_FFFF_FFFF_FFFF:
            raise OverflowError("int too big")
        if i < -0x8000_0000_0000_0000:
            raise OverflowError("int too small")
        return i

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


class PostgresqlSadLock(PostgresqlSadLockMixin, BaseSadLock[KT, ConnectionOrSessionT]):
    """A distributed lock implemented by PostgreSQL advisory lock

    See also:
        https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS

    Tip:
        Locks can be either shared or exclusive: a shared lock does not conflict with other shared locks on the same resource, only with exclusive locks.
        Locks can be taken at session level (so that they are held until released or the session ends) or at transaction level (so that they are held until the current transaction ends; there is no provision for manual release).
        Multiple session-level lock requests stack, so that if the same resource identifier is locked three times there must then be three unlock requests to release the resource in advance of session end.
    """

    @override
    def __init__(self, connection_or_session: ConnectionOrSessionT, key: KT, **kwargs):
        """
        Args:
            connection_or_session: see :attr:`.BaseSadLock.connection_or_session`
            key: :attr:`.BaseSadLock.key`
            shared: :attr:`.PostgresqlSadLockMixin.shared`
            xact: :attr:`.PostgresqlSadLockMixin.xact`
            convert: :class:`.PostgresqlSadLockMixin`
            **kwargs: other named parameters pass to :class:`.BaseSadLock` and :class:`.PostgresqlSadLockMixin`
        """
        PostgresqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    def do_acquire(
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
        """
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                self.connection_or_session.execute(self._stmt_lock).all()
                return True
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
                        return True
                    if time() - ts_begin > timeout:  # expired
                        return False
                    sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            ret_val = self.connection_or_session.execute(self._stmt_try_lock).scalar_one()
            return bool(ret_val)

    @override
    def do_release(self):
        if self._stmt_unlock is None:
            warn(
                "PostgreSQL transaction level advisory locks are held until the current transaction ends; "
                "there is no provision for manual release.",
                RuntimeWarning,
            )
            return
        ret_val = self.connection_or_session.execute(self._stmt_unlock).scalar_one()
        if not ret_val:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self.key!r} was not held.")

    # Force override close, and disable transaction level advisory locks warning it the method
    def close(self):  # type: ignore
        if self.locked:
            if sys.version_info < (3, 11):
                with catch_warnings():
                    return self.release()
            else:
                with catch_warnings(category=RuntimeWarning):
                    return self.release()


class PostgresqlAsyncSadLock(PostgresqlSadLockMixin, BaseAsyncSadLock[int, AsyncConnectionOrSessionT]):
    """Async IO version of :class:`PostgresqlSadLock`"""

    @override
    def __init__(self, connection_or_session: AsyncConnectionOrSessionT, key: KT, **kwargs):
        PostgresqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseAsyncSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    async def do_acquire(
        self,
        block: bool = True,
        timeout: Union[float, int, None] = None,
        interval: Union[float, int, None] = None,
        *args,
        **kwargs,
    ) -> bool:
        if block:
            if timeout is None:
                # None: set the timeout period to infinite.
                _ = (await self.connection_or_session.execute(self._stmt_lock)).all()
                return True
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
                        return True
                    if time() - ts_begin > timeout:  # expired
                        return False
                    await asyncio.sleep(interval)
        else:
            # This will either obtain the lock immediately and return true,
            # or return false without waiting if the lock cannot be acquired immediately.
            ret_val = (await self.connection_or_session.execute(self._stmt_try_lock)).scalar_one()
            return bool(ret_val)

    @override
    async def do_release(self):
        if self._stmt_unlock is None:
            warn(
                "PostgreSQL transaction level advisory locks are held until the current transaction ends; "
                "there is no provision for manual release.",
                RuntimeWarning,
            )
            return
        ret_val = (await self.connection_or_session.execute(self._stmt_unlock)).scalar_one()
        if not ret_val:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"The advisory lock {self.key!r} was not held.")

    @override
    async def close(self):
        if self.locked:
            if sys.version_info < (3, 11):
                with catch_warnings():
                    return await self.release()
            else:
                with catch_warnings(category=RuntimeWarning):
                    return await self.release()
