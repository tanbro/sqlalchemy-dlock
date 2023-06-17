from textwrap import dedent

from sqlalchemy import text

STATEMENTS = {
    "lock": text(
        dedent(
            """
            SELECT GET_LOCK(:str, :timeout)
            """
        ).strip()
    ),
    "unlock": text(
        dedent(
            """
            SELECT RELEASE_LOCK(:str)
            """
        ).strip()
    ),
}
