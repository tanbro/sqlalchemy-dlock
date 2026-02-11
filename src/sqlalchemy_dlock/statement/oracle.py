"""SQL statements for Oracle DBMS_LOCK"""

from typing import Final

from sqlalchemy import text

# Lock modes constants
X_MODE = 6  # Exclusive
SSX_MODE = 5  # Shared Sub-Exclusive
S_MODE = 4  # Shared
SX_MODE = 3  # Sub-Exclusive
SS_MODE = 2  # Sub-Shared
NL_MODE = 1  # Null

# Maximum timeout value (32767 seconds = ~9 hours)
MAXWAIT = 32767

# REQUEST: Acquire lock by lock ID (integer)
# Returns: 0=Success, 1=Timeout, 2=Deadlock, 3=Parameter error, 4=Already own, 5=Illegal ID
# Uses SELECT with FROM DUAL to return result (compatible with scalar_one())
REQUEST: Final = text("""
    SELECT DBMS_LOCK.REQUEST(
        id => :lock_id,
        lockmode => :lockmode,
        timeout => :timeout,
        release_on_commit => :release_on_commit
    ) AS result FROM DUAL
""")

# RELEASE: Release lock by lock ID
# Returns: 0=Success, 3=Parameter error, 4=Don't own lock, 5=Illegal ID
RELEASE: Final = text("""
    SELECT DBMS_LOCK.RELEASE(id => :lock_id) AS result FROM DUAL
""")
