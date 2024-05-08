import sys
from typing import Generic, TypeVar, Union

if sys.version_info >= (3, 11):  # pragma: no cover
    from typing import Self
else:  # pragma: no cover
    from typing_extensions import Self

from ..types import TAsyncConnectionOrSession

TKey = TypeVar("TKey")


class BaseAsyncSadLock(Generic[TKey]):
    def __init__(
        self,
        connection_or_session: TAsyncConnectionOrSession,
        key: TKey,
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
    def connection_or_session(self) -> TAsyncConnectionOrSession:
        return self._connection_or_session

    @property
    def key(self) -> TKey:
        return self._key

    @property
    def locked(self) -> bool:
        return self._acquired

    async def acquire(
        self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs
    ) -> bool:  # pragma: no cover
        raise NotImplementedError()

    async def release(self, *args, **kwargs) -> None:  # pragma: no cover
        raise NotImplementedError()

    async def close(self, *args, **kwargs) -> None:
        if self._acquired:
            await self.release(*args, **kwargs)
