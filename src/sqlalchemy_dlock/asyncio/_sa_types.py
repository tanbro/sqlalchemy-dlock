from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session

__all__ = ["TAsyncConnectionOrSession"]

type TAsyncConnectionOrSession = AsyncConnection | AsyncSession | async_scoped_session
