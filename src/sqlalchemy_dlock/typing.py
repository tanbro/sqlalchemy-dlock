from typing import Union

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session
from sqlalchemy.orm import Session, scoped_session

ConnectionOrSessionT = Union[Connection, Session, scoped_session]
AsyncConnectionOrSessionT = Union[AsyncConnection, AsyncSession, async_scoped_session]
