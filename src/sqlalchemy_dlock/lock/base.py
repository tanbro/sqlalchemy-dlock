import sys
from abc import ABC, abstractmethod
from threading import local
from typing import Callable, Generic, Optional, TypeVar, Union

if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import Self
else:  # pragma: no cover
    from typing_extensions import Self

if sys.version_info < (3, 12):  # pragma: no cover
    from typing_extensions import override
else:  # pragma: no cover
    from typing import override

from ..typing import AsyncConnectionOrSessionT, ConnectionOrSessionT

VKTV = TypeVar("VKTV")
AKTV = TypeVar("AKTV")
ConnT = TypeVar("ConnT", bound=ConnectionOrSessionT)
AsyncConnT = TypeVar("AsyncConnT", bound=AsyncConnectionOrSessionT)


class AbstractLockMixin(Generic[VKTV, AKTV], ABC):
    @abstractmethod
    def __init__(self, *, key: VKTV, convert: Optional[Callable[[VKTV], AKTV]] = None, **kwargs):
        pass

    @abstractmethod
    def get_actual_key(self) -> AKTV:
        pass

    @property
    def actual_key(self) -> AKTV:
        return self.get_actual_key()


class BaseSadLock(AbstractLockMixin, Generic[VKTV, ConnT], local, ABC):
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
        self, connection_or_session: ConnT, key: VKTV, /, contextual_timeout: Union[float, int, None] = None, **kwargs
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
    def connection_or_session(self) -> ConnT:
        """Connection or Session object SQL locking functions will be invoked on it

        It returns ``connection_or_session`` parameter of the class's constructor.
        """
        return self._connection_or_session

    @property
    def key(self) -> VKTV:
        """ID or name of the SQL locking function

        It returns ``key`` parameter of the class's constructor"""
        return self._key

    @property
    def locked(self) -> bool:
        """locked/unlocked state property

        :data:`True` if the lock is acquired, else :data:`False`
        """
        return self._acquired

    @abstractmethod
    def acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        """Acquire the lock, blocking or non-blocking.

        * With the ``block`` argument set to :data:`True` (the default), the method call will block until the lock is in an unlocked state, then set it to locked and return :data:`True`.

        * With the ``block`` argument set to :data:`False`, the method call does not block.
          If the lock is currently in a locked state, return :data:`False`; otherwise set the lock to a locked state and return :data:`True`.

        * When invoked with a positive, floating-point value for `timeout`, block for at most the number of seconds specified by timeout as long as the lock can not be acquired.
          Invocations with a negative value for `timeout` are equivalent to a `timeout` of zero.
          Invocations with a `timeout` value of ``None`` (the default) set the timeout period to infinite.
          The ``timeout`` parameter has no practical implications if the ``block`` argument is set to :data:`False` and is thus ignored.
          Returns :data:`True` if the lock has been acquired or :data:`False` if the timeout period has elapsed.
        """
        pass

    @abstractmethod
    def release(self, *args, **kwargs) -> None:
        """Release the lock.

        Since the class is thread-local, this cannot be called from other thread or process,
        and also can not be called from other connection.
        (Although PostgreSQL's shared advisory lock supports so).

        When the lock is locked, reset it to unlocked, and return.
        If any other threads are blocked waiting for the lock to become unlocked, allow exactly one of them to proceed.

        When invoked on an unlocked lock, a :class:`ValueError` is raised.

        There is no return value.
        """
        raise NotImplementedError()

    def close(self, *args, **kwargs) -> None:
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


class BaseAsyncSadLock(AbstractLockMixin, Generic[VKTV, AsyncConnT], local, ABC):
    """Async version of :class:`.BaseSadLock`"""

    def __init__(
        self, connection_or_session: AsyncConnT, key: VKTV, /, contextual_timeout: Union[float, int, None] = None, **kwargs
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
    def connection_or_session(self) -> AsyncConnT:
        return self._connection_or_session

    @property
    def key(self) -> VKTV:
        return self._key

    @property
    def locked(self) -> bool:
        return self._acquired

    @abstractmethod
    async def acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        pass

    @abstractmethod
    async def release(self, *args, **kwargs) -> None:
        pass

    async def close(self, *args, **kwargs) -> None:
        if self._acquired:
            await self.release(*args, **kwargs)
