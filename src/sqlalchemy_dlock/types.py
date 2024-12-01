import sys
from typing import Union

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:  # pragma: no cover
    from typing import TypeAlias

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session
from sqlalchemy.orm import Session, scoped_session

__all__ = ["ConnectionOrSessionT", "AsyncConnectionOrSessionT"]

ConnectionOrSessionT: TypeAlias = Union[Connection, Session, scoped_session]
AsyncConnectionOrSessionT: TypeAlias = Union[AsyncConnection, AsyncSession, async_scoped_session]
