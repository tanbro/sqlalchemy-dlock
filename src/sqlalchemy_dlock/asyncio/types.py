from typing import Union

from sqlalchemy.ext.asyncio import (AsyncConnection, AsyncSession,
                                    async_scoped_session)

TConnectionOrSession = Union[AsyncConnection,
                             AsyncSession, async_scoped_session]
