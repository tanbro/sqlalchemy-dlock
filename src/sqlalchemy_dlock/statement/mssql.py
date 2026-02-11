from typing import Final

from sqlalchemy import text

# Lock acquisition statements for different lock modes
# @LockTimeout is in milliseconds (0=no wait, -1=infinite)
# @LockOwner is 'Session' (locks are released when session ends)

# Exclusive lock (default) - full exclusive access
LOCK_EXCLUSIVE: Final = text("""
    DECLARE @result int
    EXEC @result = sp_getapplock
        @Resource = :resource,
        @LockMode = 'Exclusive',
        @LockTimeout = :timeout,
        @LockOwner = 'Session'
    SELECT @result
""")

# Shared lock - multiple readers can hold concurrently
LOCK_SHARED: Final = text("""
    DECLARE @result int
    EXEC @result = sp_getapplock
        @Resource = :resource,
        @LockMode = 'Shared',
        @LockTimeout = :timeout,
        @LockOwner = 'Session'
    SELECT @result
""")

# Update lock - intended for update operations, compatible with Shared locks
LOCK_UPDATE: Final = text("""
    DECLARE @result int
    EXEC @result = sp_getapplock
        @Resource = :resource,
        @LockMode = 'Update',
        @LockTimeout = :timeout,
        @LockOwner = 'Session'
    SELECT @result
""")

# Lock release statement (same for all lock modes)
UNLOCK: Final = text("""
    DECLARE @result int
    EXEC @result = sp_releaseapplock
        @Resource = :resource,
        @LockOwner = 'Session'
    SELECT @result
""")
