from sqlalchemy import text


LOCK = text("SELECT pg_advisory_lock(:key)")
LOCK_SHARED = text("SELECT pg_advisory_lock_shared(:key)")
LOCK_XACT = text("SELECT pg_advisory_xact_lock(:key)")
LOCK_XACT_SHARED = text("SELECT pg_advisory_xact_lock_shared(:key)")

TRY_LOCK = text("SELECT pg_try_advisory_lock(:key)")
TRY_LOCK_SHARED = text("SELECT pg_try_advisory_lock_shared(:key)")
TRY_LOCK_XACT = text("SELECT pg_try_advisory_xact_lock(:key)")
TRY_LOCK_XACT_SHARED = text("SELECT pg_try_advisory_xact_lock_shared(:key)")

UNLOCK = text("SELECT pg_advisory_unlock(:key)")
UNLOCK_SHARED = text("SELECT pg_advisory_unlock_shared(:key)")


SLEEP_INTERVAL_DEFAULT = 1
SLEEP_INTERVAL_MIN = 0.1
