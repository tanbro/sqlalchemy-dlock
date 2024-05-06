import sys
from typing import Union

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:  # pragma: no cover
    from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session

__all__ = ["TAsyncConnectionOrSession"]

TAsyncConnectionOrSession: TypeAlias = Union[AsyncConnection, AsyncSession, async_scoped_session]
