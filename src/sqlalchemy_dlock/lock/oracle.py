"""Oracle database lock implementation using DBMS_LOCK"""

import sys
from hashlib import blake2b
from typing import Any, Callable, Literal, Optional, TypeVar, Union

if sys.version_info < (3, 12):  # pragma: no cover
    from typing_extensions import override
else:  # pragma: no cover
    from typing import override

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..statement.oracle import MAXWAIT, NL_MODE, RELEASE, REQUEST, S_MODE, SS_MODE, SSX_MODE, SX_MODE, X_MODE
from ..typing import AsyncConnectionOrSessionT, ConnectionOrSessionT
from .base import AbstractLockMixin, BaseAsyncSadLock, BaseSadLock

# Oracle lock ID range: 0 to 1073741823
ORACLE_LOCK_ID_MIN = 0
ORACLE_LOCK_ID_MAX = 1073741823

ConvertibleKT = Union[bytes, bytearray, memoryview, str, int, float]
KT = Any
KTV = TypeVar("KTV", bound=KT)


class OracleSadLockMixin(AbstractLockMixin[KTV, int]):
    """Mixin class for Oracle DBMS_LOCK"""

    # Lock mode constants (matching DBMS_LOCK)
    NL_MODE = NL_MODE  # 1 - Null
    SS_MODE = SS_MODE  # 2 - Sub-Shared
    SX_MODE = SX_MODE  # 3 - Sub-Exclusive
    S_MODE = S_MODE  # 4 - Shared
    SSX_MODE = SSX_MODE  # 5 - Shared Sub-Exclusive
    X_MODE = X_MODE  # 6 - Exclusive

    @override
    def __init__(
        self,
        *,
        key: KTV,
        convert: Optional[Callable[[KTV], int]] = None,
        lock_mode: Literal["NL", "SS", "SX", "S", "SSX", "X"] = "X",
        release_on_commit: bool = False,
        **kwargs,
    ):
        """
        Args:
            key: Oracle lock identifier
                - When :class:`int`: used directly as lock ID (must be 0-1073741823)
                - When :class:`str`/:class:`bytes`: hashed to integer via blake2b
                - Other types are converted using default or custom converter

            convert: Custom function to convert key to int

            lock_mode: Lock mode to use
                - "X" (default): Exclusive mode - full exclusive access
                - "S": Shared mode - multiple readers
                - "SS": Sub-Shared - for aggregate objects
                - "SX": Sub-Exclusive (Row Exclusive)
                - "SSX": Shared Sub-Exclusive (Share Row Exclusive)
                - "NL": Null mode - no actual locking

            release_on_commit: Whether to release lock on commit/rollback
                - False (default): Lock held until explicit release or session ends
                - True: Lock released when transaction ends

        Lock Mode Compatibility Matrix:
        (Held Mode vs Get Mode: S=Success, F=Fail)
        Held\\Get | NL | SS | SX | S  | SSX | X
        ---------|----|----|----|----|-----|---
        NL       | S  | S  | S  | S  | S   | S
        SS       | S  | S  | S  | S  | S   | F
        SX       | S  | S  | S  | F  | F   | F
        S        | S  | S  | F  | S  | F   | F
        SSX      | S  | S  | F  | F  | F   | F
        X        | S  | F  | F  | F  | F   | F
        """
        if convert:
            self._actual_key = convert(key)
        else:
            self._actual_key = self.convert(key)

        # Ensure the key is in Oracle's valid range
        self._actual_key = self.ensure_valid_id(self._actual_key)

        # Validate and store lock mode
        valid_modes = {"NL", "SS", "SX", "S", "SSX", "X"}
        lock_mode_upper = lock_mode.upper()
        if lock_mode_upper not in valid_modes:
            raise ValueError(f"Invalid lock_mode: {lock_mode!r}. Must be one of: {', '.join(sorted(valid_modes))}")
        self._lock_mode = lock_mode_upper

        # Store release_on_commit setting
        self._release_on_commit = bool(release_on_commit)

        # Convert lock mode string to integer constant
        self._lock_mode_int = getattr(self, f"{lock_mode_upper}_MODE")

    @override
    def get_actual_key(self) -> int:
        """The actual key used in Oracle DBMS_LOCK"""
        return self._actual_key

    @classmethod
    def convert(cls, k: ConvertibleKT) -> int:
        """Default key converter for Oracle DBMS_LOCK

        Similar to PostgreSQL: strings/bytes are hashed using blake2b.
        """
        if isinstance(k, int):
            return k
        if isinstance(k, str):
            d = k.encode()
        elif isinstance(k, (bytes, bytearray)):
            d = k
        elif isinstance(k, memoryview):
            d = k.tobytes()
        elif isinstance(k, float):
            # For numeric types, convert to string first then hash
            # This ensures consistent behavior with PostgreSQL
            d = str(k).encode()
        else:
            raise TypeError(type(k).__name__)

        # Use blake2b to get 8 bytes (64 bits), then map to Oracle's range
        hash_bytes = blake2b(d, digest_size=8).digest()
        hash_int = int.from_bytes(hash_bytes, sys.byteorder, signed=False)

        # Map to Oracle's valid range (0-1073741823)
        # Using modulo to ensure we stay in range
        return hash_int % (ORACLE_LOCK_ID_MAX + 1)

    @classmethod
    def ensure_valid_id(cls, i: int) -> int:
        """Ensure the integer is in Oracle's lock ID range (0 to 1073741823)

        Args:
            i: Integer to validate

        Returns:
            Valid lock ID in range [0, 1073741823]

        Raises:
            TypeError: If input is not an integer
        """
        if not isinstance(i, int):
            raise TypeError(f"int type expected, but actual type is {type(i).__name__}")

        # Use modulo to bring into valid range
        if i < ORACLE_LOCK_ID_MIN or i > ORACLE_LOCK_ID_MAX:
            i = i % (ORACLE_LOCK_ID_MAX + 1)

        return i

    @property
    def lock_mode(self) -> Literal["NL", "SS", "SX", "S", "SSX", "X"]:
        """The lock mode being used"""
        return self._lock_mode  # type: ignore[return-value]

    @property
    def lock_mode_int(self) -> int:
        """The lock mode as integer (for DBMS_LOCK)"""
        return self._lock_mode_int

    @property
    def release_on_commit(self) -> bool:
        """Whether the lock is released on commit/rollback"""
        return self._release_on_commit


class OracleSadLock(OracleSadLockMixin, BaseSadLock[int, ConnectionOrSessionT]):
    """Distributed lock implemented by Oracle DBMS_LOCK

    See Also:
        https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_LOCK.html

    Tip:
        Oracle user locks are identified with the prefix "UL" and can be viewed
        in Enterprise Manager lock monitor or appropriate V$ views.

        Locks are automatically released when a session terminates.

        String keys are converted to integer IDs using blake2b hash, similar to
        PostgreSQL's advisory lock implementation.
    """

    @override
    def __init__(self, connection_or_session: ConnectionOrSessionT, key: KT, **kwargs):
        """
        Args:
            connection_or_session: see :attr:`.BaseSadLock.connection_or_session`
            key: :attr:`.BaseSadLock.key`
            lock_mode: :attr:`.OracleSadLockMixin.lock_mode`
            release_on_commit: :attr:`.OracleSadLockMixin.release_on_commit`
            convert: :class:`.OracleSadLockMixin`
            **kwargs: other named parameters pass to :class:`.BaseSadLock` and :class:`.OracleSadLockMixin`
        """
        OracleSadLockMixin.__init__(self, key=key, **kwargs)
        BaseSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    def do_acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        """
        Acquire the lock using DBMS_LOCK.REQUEST.

        Returns:
            0: Success
            1: Timeout
            2: Deadlock
            3: Parameter error
            4: Already own lock
            5: Illegal lock ID
        """
        # Convert timeout to integer seconds
        if block:
            if timeout is None:
                timeout_sec = MAXWAIT  # Infinite wait
            elif timeout < 0:
                timeout_sec = 0
            elif timeout > MAXWAIT:
                timeout_sec = MAXWAIT
            else:
                timeout_sec = int(timeout)
        else:
            timeout_sec = 0  # No wait

        stmt = REQUEST.params(
            lock_id=self._actual_key,
            lockmode=self._lock_mode_int,
            timeout=timeout_sec,
            release_on_commit=int(self._release_on_commit),
        )

        ret_val = self.connection_or_session.execute(stmt).scalar_one()

        if ret_val == 0:
            return True  # Success
        elif ret_val == 1:
            return False  # Timeout
        elif ret_val == 2:
            raise SqlAlchemyDLockDatabaseError(f"Deadlock detected while acquiring lock {self.key!r}")
        elif ret_val == 3:
            raise SqlAlchemyDLockDatabaseError(
                f"Parameter error for lock {self.key!r} (mode={self._lock_mode}, timeout={timeout_sec})"
            )
        elif ret_val == 4:
            # Already own the lock - treat as success
            return True
        elif ret_val == 5:
            raise SqlAlchemyDLockDatabaseError(
                f"Illegal lock ID {self._actual_key}. Oracle lock IDs must be in range [0, 1073741823]."
            )
        else:
            raise SqlAlchemyDLockDatabaseError(f"DBMS_LOCK.REQUEST({self.key!r}) returned unexpected value: {ret_val}")

    @override
    def do_release(self):
        """Release the lock using DBMS_LOCK.RELEASE.

        Returns:
            0: Success
            3: Parameter error
            4: Don't own lock
            5: Illegal lock ID
        """
        stmt = RELEASE.params(lock_id=self._actual_key)

        ret_val = self.connection_or_session.execute(stmt).scalar_one()

        if ret_val == 0:
            return  # Success
        elif ret_val == 3:
            raise SqlAlchemyDLockDatabaseError(f"Parameter error while releasing lock {self.key!r}")
        elif ret_val == 4:
            raise SqlAlchemyDLockDatabaseError(f"The lock {self.key!r} was not held by this session")
        elif ret_val == 5:
            raise SqlAlchemyDLockDatabaseError(
                f"Illegal lock ID {self._actual_key}. Oracle lock IDs must be in range [0, 1073741823]."
            )
        else:
            raise SqlAlchemyDLockDatabaseError(f"DBMS_LOCK.RELEASE({self.key!r}) returned unexpected value: {ret_val}")


class OracleAsyncSadLock(OracleSadLockMixin, BaseAsyncSadLock[int, AsyncConnectionOrSessionT]):
    """Async IO version of OracleSadLock"""

    @override
    def __init__(self, connection_or_session: AsyncConnectionOrSessionT, key: KT, **kwargs):
        OracleSadLockMixin.__init__(self, key=key, **kwargs)
        BaseAsyncSadLock.__init__(self, connection_or_session, self.actual_key, **kwargs)

    @override
    async def do_acquire(self, block: bool = True, timeout: Union[float, int, None] = None, *args, **kwargs) -> bool:
        if block:
            if timeout is None:
                timeout_sec = MAXWAIT
            elif timeout < 0:
                timeout_sec = 0
            elif timeout > MAXWAIT:
                timeout_sec = MAXWAIT
            else:
                timeout_sec = int(timeout)
        else:
            timeout_sec = 0

        stmt = REQUEST.params(
            lock_id=self._actual_key,
            lockmode=self._lock_mode_int,
            timeout=timeout_sec,
            release_on_commit=int(self._release_on_commit),
        )

        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()

        if ret_val == 0:
            return True
        elif ret_val == 1:
            return False
        elif ret_val == 2:
            raise SqlAlchemyDLockDatabaseError(f"Deadlock detected while acquiring lock {self.key!r}")
        elif ret_val == 3:
            raise SqlAlchemyDLockDatabaseError(
                f"Parameter error for lock {self.key!r} (mode={self._lock_mode}, timeout={timeout_sec})"
            )
        elif ret_val == 4:
            return True
        elif ret_val == 5:
            raise SqlAlchemyDLockDatabaseError(
                f"Illegal lock ID {self._actual_key}. Oracle lock IDs must be in range [0, 1073741823]."
            )
        else:
            raise SqlAlchemyDLockDatabaseError(f"DBMS_LOCK.REQUEST({self.key!r}) returned unexpected value: {ret_val}")

    @override
    async def do_release(self):
        stmt = RELEASE.params(lock_id=self._actual_key)

        ret_val = (await self.connection_or_session.execute(stmt)).scalar_one()

        if ret_val == 0:
            return
        elif ret_val == 3:
            raise SqlAlchemyDLockDatabaseError(f"Parameter error while releasing lock {self.key!r}")
        elif ret_val == 4:
            raise SqlAlchemyDLockDatabaseError(f"The lock {self.key!r} was not held by this session")
        elif ret_val == 5:
            raise SqlAlchemyDLockDatabaseError(
                f"Illegal lock ID {self._actual_key}. Oracle lock IDs must be in range [0, 1073741823]."
            )
        else:
            raise SqlAlchemyDLockDatabaseError(f"DBMS_LOCK.RELEASE({self.key!r}) returned unexpected value: {ret_val}")
