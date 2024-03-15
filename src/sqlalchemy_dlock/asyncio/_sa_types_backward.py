import sys
from warnings import warn

if not sys.version_info < (3, 12):  # pragma: no cover
    warn("Python version greater than or equal to 3.12 should import “_sa_types” module")

from typing import Union

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:  # pragma: no cover
    from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_scoped_session

TAsyncConnectionOrSession: TypeAlias = Union[AsyncConnection, AsyncSession, async_scoped_session]
