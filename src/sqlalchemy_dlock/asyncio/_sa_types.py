from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session

type TAsyncConnectionOrSession = AsyncConnection | AsyncSession | async_scoped_session
