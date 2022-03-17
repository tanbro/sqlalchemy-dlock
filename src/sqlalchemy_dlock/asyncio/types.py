from typing import Any, Union

from sqlalchemy.ext.asyncio import (AsyncConnection, AsyncSession,
                                    async_scoped_session)

TAsyncConnectionOrSession = Union[AsyncConnection,
                                  AsyncSession, async_scoped_session]


class BaseAsyncSadLock:
    def __init__(self,
                 connection_or_session: TAsyncConnectionOrSession,
                 key: Any,
                 *args, **kwargs
                 ):
        self._acquired = False
        self._connection_or_session = connection_or_session
        self._key = key

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, type_, value, traceback):
        await self.close()

    def __str__(self):  # pragma: no cover
        return '<{} {} key={} at 0x{:x}>'.format(
            'locked' if self._acquired else 'unlocked',
            self.__class__.__name__,
            self._key, id(self)
        )

    @property
    def connection_or_session(self) -> TAsyncConnectionOrSession:
        return self._connection_or_session

    @property
    def key(self):
        return self._key

    @property
    def acquired(self) -> bool:
        return self._acquired

    @property
    def locked(self) -> bool:
        return self.acquired

    async def acquire(self,
                      block: bool = True,
                      timeout: Union[float, int, None] = None,
                      *args, **kwargs
                      ) -> bool:
        raise NotImplementedError()

    async def release(self, *args, **kwargs):
        raise NotImplementedError()

    async def close(self, *args, **kwargs):
        if self._acquired:
            await self.release(*args, **kwargs)
