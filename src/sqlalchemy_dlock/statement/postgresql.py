from textwrap import dedent

from sqlalchemy import text

STATEMENTS = {
    "session": {
        "lock": text(
            dedent(
                """
                SELECT pg_advisory_lock(:key)
                """
            ).strip()
        ),
        "trylock": text(
            dedent(
                """
                SELECT pg_try_advisory_lock(:key)
                """
            ).strip()
        ),
        "unlock": text(
            dedent(
                """
                SELECT pg_advisory_unlock(:key)
                """
            ).strip()
        ),
    },
    "shared": {
        "lock": text(
            dedent(
                """
                SELECT pg_advisory_lock_shared(:key)
                """
            ).strip()
        ),
        "trylock": text(
            dedent(
                """
                SELECT pg_try_advisory_lock_shared(:key)
                """
            ).strip()
        ),
        "unlock": text(
            dedent(
                """
                SELECT pg_advisory_unlock_shared(:key)
                """
            ).strip()
        ),
    },
    "transaction": {
        "lock": text(
            dedent(
                """
                SELECT pg_advisory_xact_lock(:key)
                """
            ).strip()
        ),
        "trylock": text(
            dedent(
                """
                SELECT pg_try_advisory_xact_lock(:key)
                """
            ).strip()
        ),
        "unlock": text(
            dedent(
                """
                SELECT pg_advisory_xact_unlock(:key)
                """
            ).strip()
        ),
    },
}
