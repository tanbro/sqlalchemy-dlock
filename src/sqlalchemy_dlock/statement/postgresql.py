from typing import Final

from sqlalchemy import text

LOCK: Final = text("SELECT pg_advisory_lock(:key)")
LOCK_SHARED: Final = text("SELECT pg_advisory_lock_shared(:key)")
LOCK_XACT: Final = text("SELECT pg_advisory_xact_lock(:key)")
LOCK_XACT_SHARED: Final = text("SELECT pg_advisory_xact_lock_shared(:key)")

TRY_LOCK: Final = text("SELECT pg_try_advisory_lock(:key)")
TRY_LOCK_SHARED: Final = text("SELECT pg_try_advisory_lock_shared(:key)")
TRY_LOCK_XACT: Final = text("SELECT pg_try_advisory_xact_lock(:key)")
TRY_LOCK_XACT_SHARED: Final = text("SELECT pg_try_advisory_xact_lock_shared(:key)")

UNLOCK: Final = text("SELECT pg_advisory_unlock(:key)")
UNLOCK_SHARED: Final = text("SELECT pg_advisory_unlock_shared(:key)")


SLEEP_INTERVAL_DEFAULT: Final = 1
SLEEP_INTERVAL_MIN: Final = 0.1
