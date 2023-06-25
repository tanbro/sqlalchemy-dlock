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


def make_lock_stmt_mapping(level: str):
    if level in ("", "session"):
        return {
            "lock": LOCK,
            "try_lock": TRY_LOCK,
            "unlock": UNLOCK,
        }
    elif level in ("share", "shared"):
        return {
            "lock": LOCK_SHARED,
            "try_lock": TRY_LOCK_SHARED,
            "unlock": UNLOCK_SHARED,
        }
    elif level in ("tran", "trans", "transact", "transaction", "xact"):
        return {
            "lock": LOCK_XACT,
            "try_lock": TRY_LOCK_XACT,
            "unlock": UNLOCK_XACT,
        }
    else:
        raise ValueError(f"Unknown postgresql advisory lock level {level!r}. It should be in ('session', 'shared', 'xact')")
