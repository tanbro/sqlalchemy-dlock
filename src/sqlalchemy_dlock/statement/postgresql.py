from sqlalchemy import text


LOCK = text("SELECT pg_advisory_lock(:key)")
LOCK_SHARED = text("SELECT pg_advisory_lock_shared(:key)")
LOCK_XACT = text("SELECT pg_advisory_xact_lock(:key)")
TRY_LOCK = text("SELECT pg_try_advisory_lock(:key)")
TRY_LOCK_SHARED = text("SELECT pg_try_advisory_lock_shared(:key)")
TRY_LOCK_XACT = text("SELECT pg_try_advisory_xact_lock(:key)")
UNLOCK = text("SELECT pg_advisory_unlock(:key)")
UNLOCK_SHARED = text("SELECT pg_advisory_unlock_shared(:key)")
UNLOCK_XACT = text("SELECT pg_advisory_xact_unlock(:key)")


SLEEP_INTERVAL_DEFAULT = 1
SLEEP_INTERVAL_MIN = 0.1

STATEMENT_DICT = {
    "session": {
        "lock": LOCK,
        "try_lock": TRY_LOCK,
        "unlock": UNLOCK,
    },
    "shared": {
        "lock": LOCK_SHARED,
        "try_lock": TRY_LOCK_SHARED,
        "unlock": UNLOCK_SHARED,
    },
    "transaction": {
        "lock": LOCK_XACT,
        "try_lock": TRY_LOCK_XACT,
        "unlock": UNLOCK_XACT,
    },
}

STATEMENT_DICT.update(  # Alias of the keys
    {
        "sess": STATEMENT_DICT["session"],
        "share": STATEMENT_DICT["shared"],
        "xact": STATEMENT_DICT["transaction"],
        "trans": STATEMENT_DICT["transaction"],
    }
)
