import sys
from typing import Any, Callable, Literal, Optional, TypeVar, Union

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..statement.mssql import (
    LOCK_EXCLUSIVE,
    LOCK_SHARED,
    LOCK_UPDATE,
    UNLOCK,
)
from ..typing import AsyncConnectionOrSessionT, ConnectionOrSessionT
from .base import AbstractLockMixin, BaseAsyncSadLock, BaseSadLock

MSSQL_LOCK_RESOURCE_MAX_LENGTH = 255

ConvertibleKT = Union[bytes, bytearray, memoryview, str, int, float]
KT = Any
KTV = TypeVar("KTV", bound=KT)


class MssqlSadLockMixin(AbstractLockMixin[KTV, str]):
    """Mixin class for SQL Server application lock"""

    MSSQL_LOCK_RESOURCE_MAX_LENGTH = 255

    @override
    def __init__(
        self, *, key: KTV, convert: Optional[Callable[[KTV], str]] = None, shared: bool = False, update: bool = False, **kwargs
    ):
        """
        Args:
            key: SQL Server requires the resource name as a string (max 255 chars)
            convert: Custom function to convert key to string
            shared: :attr:`.shared` - Whether to use Shared lock mode
            update: :attr:`.update` - Whether to use Update lock mode
                Note: Shared and Update are mutually exclusive. If both are True, Update takes precedence.
        """
        if convert:
            self._actual_key = convert(key)
        else:
            self._actual_key = self.convert(key)

        if not isinstance(self._actual_key, str):
            raise TypeError("SQL Server application lock requires the key to be a string")
        if len(self._actual_key) > MSSQL_LOCK_RESOURCE_MAX_LENGTH:
            raise ValueError(
                f"SQL Server enforces a maximum length of {MSSQL_LOCK_RESOURCE_MAX_LENGTH} characters for lock resource names"
            )

        # Determine lock mode: update takes precedence over shared
        self._update = bool(update)
        self._shared = bool(shared) and not bool(update)

        # Select appropriate statement based on lock mode
        if self._update:
            self._stmt_lock = LOCK_UPDATE
        elif self._shared:
            self._stmt_lock = LOCK_SHARED
        else:
            self._stmt_lock = LOCK_EXCLUSIVE

    @override
    def get_actual_key(self) -> str:
        """The actual key used in SQL Server application lock"""
        return self._actual_key

    @property
    def shared(self) -> bool:
        """Is the lock mode Shared"""
        return self._shared

    @property
    def update(self) -> bool:
        """Is the lock mode Update"""
        return self._update

    @property
    def lock_mode(self) -> Literal["Shared", "Update", "Exclusive"]:
        """The lock mode being used (for informational purposes)"""
        if self._update:
            return "Update"
        elif self._shared:
            return "Shared"
        else:
            return "Exclusive"

    @classmethod
    def convert(cls, k: ConvertibleKT) -> str:
        """Default key converter for SQL Server application lock"""
        if isinstance(k, str):
            return k
        if isinstance(k, (int, float)):
            return str(k)
        if isinstance(k, (bytes, bytearray)):
            return k.decode()
        if isinstance(k, memoryview):
            return k.tobytes().decode()
        raise TypeError(type(k).__name__)


class MssqlSadLock(MssqlSadLockMixin, BaseSadLock[str, ConnectionOrSessionT]):
    """Distributed lock implemented by SQL Server application lock (sp_getapplock)

    See Also:
        https://learn.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-getapplock-transact-sql
    """

    @override
    def __init__(self, connection_or_session: ConnectionOrSessionT, key: KT, **kwargs):
        MssqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    def do_acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        """
        Acquire the lock using sp_getapplock.

        sp_getapplock returns:
        - >= 0: Success (lock owner)
        - -1: Timeout
        - -2: Canceled
        - -3: Parameter error
        - -999: Generic error
        """
        # Convert timeout to milliseconds (MSSQL uses ms, Python uses seconds)
        if block:
            if timeout is None:
                timeout_ms = -1  # Infinite wait
            elif timeout < 0:
                timeout_ms = 0
            else:
                timeout_ms = int(timeout * 1000)  # Convert seconds to milliseconds
        else:
            timeout_ms = 0  # No wait

        # Use the pre-selected statement based on lock mode
        stmt = self._stmt_lock.params(resource=self.key, timeout=timeout_ms)
        ret_val = self.connection_or_session.execute(stmt).scalar_one()

        if ret_val >= 0:
            return True  # Success
        elif ret_val == -1:
            return False  # Timeout
        elif ret_val == -3:
            raise SqlAlchemyDLockDatabaseError(f"Parameter validation failed for lock resource {self.key!r}")
        else:  # -2, -999, or other errors
            raise SqlAlchemyDLockDatabaseError(f"sp_getapplock({self.key!r}, {timeout_ms}ms) returned {ret_val}")

    @override
    def do_release(self):
        """
        Release the lock using sp_releaseapplock.

        Returns:
        - >= 0: Success
        - -999: Generic error
        """
        stmt = UNLOCK.params(resource=self.key)
        ret_val = self.connection_or_session.execute(stmt).scalar_one()

        if ret_val < 0:
            raise SqlAlchemyDLockDatabaseError(f"sp_releaseapplock({self.key!r}) returned {ret_val}")


class MssqlAsyncSadLock(MssqlSadLockMixin, BaseAsyncSadLock[str, AsyncConnectionOrSessionT]):
    """Async IO version of MssqlSadLock"""

    @override
    def __init__(self, connection_or_session: AsyncConnectionOrSessionT, key: KT, **kwargs):
        MssqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseAsyncSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    async def do_acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        if block:
            if timeout is None:
                timeout_ms = -1
            elif timeout < 0:
                timeout_ms = 0
            else:
                timeout_ms = int(timeout * 1000)
        else:
            timeout_ms = 0

        # Use the pre-selected statement based on lock mode
        stmt = self._stmt_lock.params(resource=self.key, timeout=timeout_ms)
        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()

        if ret_val >= 0:
            return True
        elif ret_val == -1:
            return False
        elif ret_val == -3:
            raise SqlAlchemyDLockDatabaseError(f"Parameter validation failed for lock resource {self.key!r}")
        else:
            raise SqlAlchemyDLockDatabaseError(f"sp_getapplock({self.key!r}, {timeout_ms}ms) returned {ret_val}")

    @override
    async def do_release(self):
        stmt = UNLOCK.params(resource=self.key)
        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()

        if ret_val < 0:
            raise SqlAlchemyDLockDatabaseError(f"sp_releaseapplock({self.key!r}) returned {ret_val}")
