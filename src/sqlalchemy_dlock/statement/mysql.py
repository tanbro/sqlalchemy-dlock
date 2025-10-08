from typing import Final

from sqlalchemy import text

LOCK: Final = text("SELECT GET_LOCK(:str, :timeout)")
UNLOCK: Final = text("SELECT RELEASE_LOCK(:str)")
