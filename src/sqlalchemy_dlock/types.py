from typing import TypeVar, Union

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session
from sqlalchemy.orm import Session, scoped_session

__all__ = ("ConnectionOrSessionT", "AsyncConnectionOrSessionT", "KT")

KT = TypeVar("KT")
ConnectionOrSessionT = TypeVar("ConnectionOrSessionT", bound=Union[Connection, Session, scoped_session])
AsyncConnectionOrSessionT = TypeVar(
    "AsyncConnectionOrSessionT", bound=Union[AsyncConnection, AsyncSession, async_scoped_session]
)
