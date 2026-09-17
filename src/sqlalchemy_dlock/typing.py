from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session
from sqlalchemy.orm import Session, scoped_session

ConnectionOrSessionT = Connection | Session | scoped_session
AsyncConnectionOrSessionT = AsyncConnection | AsyncSession | async_scoped_session
