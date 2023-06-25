from sqlalchemy import text

LOCK = text("SELECT GET_LOCK(:str, :timeout)")
UNLOCK = text("SELECT RELEASE_LOCK(:str)")
