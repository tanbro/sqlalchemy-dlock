import sys
from abc import ABC, abstractmethod
from threading import local
from typing import Callable, Generic, Optional, TypeVar, Union, final

if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import Self
else:  # pragma: no cover
    from typing_extensions import Self

if sys.version_info < (3, 12):  # pragma: no cover
    from typing_extensions import override
else:  # pragma: no cover
    from typing import override

from ..typing import AsyncConnectionOrSessionT, ConnectionOrSessionT

KeyTV = TypeVar("KeyTV")
ActualKeyTV = TypeVar("ActualKeyTV")
ConnectionTV = TypeVar("ConnectionTV", bound=ConnectionOrSessionT)
AsyncConnectionTV = TypeVar("AsyncConnectionTV", bound=AsyncConnectionOrSessionT)


class AbstractLockMixin(Generic[KeyTV, ActualKeyTV], ABC):
    @abstractmethod
    def __init__(self, *, key: KeyTV, convert: Optional[Callable[[KeyTV], ActualKeyTV]] = None, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def get_actual_key(self) -> ActualKeyTV:
        raise NotImplementedError()

    @property
    def actual_key(self) -> ActualKeyTV:
        return self.get_actual_key()


class BaseSadLock(AbstractLockMixin, Generic[KeyTV, ConnectionTV], local, ABC):
    """Base class of database lock implementation

    Note:
        * It's Thread-Local (:class:`threading.local`)
        * It's an abstract class, do not manual instantiate

    The :meth:`acquire` and :meth:`release` methods can be used as context managers for a :keyword:`with` statement.
    :meth:`acquire` will be called when the block is entered, and :meth:`release` will be called when the block is exited.
    Hence, the following snippet::

        with some_lock:
            # do something...
            pass

    is equivalent to::

        some_lock.acquire()
        try:
            # do something...
            pass
        finally:
            some_lock.release()

    Note:
        A :exc:`TimeoutError` will be thrown if acquire timeout in :keyword:`with` statement.
    """

    @override
    def __init__(
        self, connection_or_session: ConnectionTV, key: KeyTV, /, contextual_timeout: Union[float, int, None] = None, **kwargs
    ):
        """
        Args:

            connection_or_session: Connection or Session object SQL locking functions will be invoked on it

            key: ID or name of the SQL locking function

            contextual_timeout: Timeout(seconds) for Context Managers.

                When called in a :keyword:`with` statement, the new created lock object will pass it to ``timeout`` argument of :meth:`.BaseSadLock.acquire`.

                Attention:
                    **ONLY** affects :keyword:`with` statements.

                Example:
                    ::

                        try:
                            with create_sadlock(conn, k, contextual_timeout=5) as lck:
                                # do something...
                                pass
                        except TimeoutError:
                            # can not acquire after 5 seconds
                            pass

                Note:
                    The default value of `timeout` is still :data:`None`, when invoking :meth:`.acquire`
        """
        self._acquired = False
        self._connection_or_session = connection_or_session
        self._key = key
        self._contextual_timeout = contextual_timeout

    def __enter__(self) -> Self:
        if self._contextual_timeout is None:  # timeout period is infinite
            self.acquire()
        elif not self.acquire(timeout=self._contextual_timeout):  # the timeout period has elapsed and not acquired
            raise TimeoutError()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __str__(self) -> str:
        return "<{} {} key={} at 0x{:x}>".format(
            "locked" if self._acquired else "unlocked",
            self.__class__.__name__,
            self._key,
            id(self),
        )

    @property
    def connection_or_session(self) -> ConnectionTV:
        """Connection or Session object SQL locking functions will be invoked on it

        It returns ``connection_or_session`` parameter of the class's constructor.
        """
        return self._connection_or_session

    @property
    def key(self) -> KeyTV:
        """ID or name of the SQL locking function

        It returns ``key`` parameter of the class's constructor"""
        return self._key

    @property
    def locked(self) -> bool:
        """locked/unlocked state property

        :data:`True` if the lock is acquired, else :data:`False`
        """
        return self._acquired

    @final
    def acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        """Acquire the lock in blocking or non-blocking mode.

        The implementation (:meth:`do_acquire`) should provide the following behavior:

        * When ``block`` is :data:`True` (the default), the method blocks until the lock is in an unlocked state,
          then sets it to locked and returns :data:`True`.

        * When ``block`` is :data:`False`, the method call is non-blocking.
          If the lock is currently locked, it returns :data:`False`; otherwise, it sets the lock to locked state and returns :data:`True`.

        * When invoked with a positive floating-point value for ``timeout``, it blocks for at most the specified number
          of seconds until the lock can be acquired.

        * Invocations with a negative ``timeout`` value are equivalent to a ``timeout`` of zero.

        * When ``timeout`` is ``None`` (the default), the timeout period is infinite.
          The ``timeout`` parameter has no effect when ``block`` is :data:`False` and is thus ignored.

        * Returns :data:`True` if the lock has been acquired or :data:`False` if the timeout period has elapsed.
        """
        if self._acquired:
            raise ValueError("invoked on a locked lock")
        return self.do_acquire(block, timeout, *args, **kwargs)

    @abstractmethod
    def do_acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        raise NotImplementedError()

    @final
    def release(self, *args, **kwargs):
        """Release the lock.

        Since the class is thread-local, this method cannot be called from another thread or process,
        nor can it be called from another connection.
        (Although PostgreSQL's shared advisory lock supports this).

        The implementation (:meth:`do_release`) should provide the following behavior:

        * Reset the lock to unlocked state and return when the lock is currently locked.
        * Allow exactly one of any other threads blocked waiting for the lock to become unlocked to proceed.
        * Raise a :class:`ValueError` when invoked on an unlocked lock.
        * Not return a value.
        """
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        return self.do_release(*args, **kwargs)

    @abstractmethod
    def do_release(self, *args, **kwargs):
        raise NotImplementedError()

    @final
    def close(self, *args, **kwargs):
        """Same as :meth:`release`

        Except that the :class:`ValueError` is **NOT** raised when invoked on an unlocked lock.

        An invocation of this method is equivalent to::

            if not some_lock.locked:
                some_lock.release()

        This method maybe useful together with :func:`contextlib.closing`, when we need a :keyword:`with` statement, but don't want it to acquire at the beginning of the block.

        Example:
            ::

                # ...

                from contextlib import closing
                from sqlalchemy_dlock import create_sadlock

                # ...

                with closing(create_sadlock(some_connection, some_key)) as lock:
                    # will **NOT** acquire at the begin of with-block
                    assert not lock.locked
                    # ...
                    # lock when need
                    lock.acquire()
                    assert lock.locked
                    # ...

                # `close` will be called at the end with-block
                assert not lock.locked
        """
        if self._acquired:
            self.release(*args, **kwargs)


class BaseAsyncSadLock(AbstractLockMixin, Generic[KeyTV, AsyncConnectionTV], local, ABC):
    """Async version of :class:`.BaseSadLock`"""

    def __init__(
        self,
        connection_or_session: AsyncConnectionTV,
        key: KeyTV,
        /,
        contextual_timeout: Union[float, int, None] = None,
        **kwargs,
    ):
        self._acquired = False
        self._connection_or_session = connection_or_session
        self._key = key
        self._contextual_timeout = contextual_timeout

    async def __aenter__(self) -> Self:
        if self._contextual_timeout is None:
            await self.acquire()
        elif not await self.acquire(timeout=self._contextual_timeout):
            # the timeout period has elapsed and not acquired
            raise TimeoutError()
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        await self.close()

    def __str__(self):
        return "<{} {} key={} at 0x{:x}>".format(
            "locked" if self._acquired else "unlocked",
            self.__class__.__name__,
            self._key,
            id(self),
        )

    @property
    def connection_or_session(self) -> AsyncConnectionTV:
        return self._connection_or_session

    @property
    def key(self) -> KeyTV:
        return self._key

    @property
    def locked(self) -> bool:
        return self._acquired

    @abstractmethod
    async def acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def release(self, *args, **kwargs) -> None:
        raise NotImplementedError()

    async def close(self, *args, **kwargs) -> None:
        if self._acquired:
            await self.release(*args, **kwargs)
