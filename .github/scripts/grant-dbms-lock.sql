-- Grant DBMS_LOCK permission to the test user for distributed locking
-- This script is run by gvenzl/setup-oracle-free action
ALTER SESSION SET "_ORACLE_SCRIPT"=TRUE;

-- Grant execute on DBMS_LOCK to the app user
GRANT EXECUTE ON SYS.DBMS_LOCK TO test;

-- Grant execute on DBMS_LOCK to PUBLIC (optional, for broader access)
-- COMMENT: Not granting to PUBLIC for security reasons

-- Verify the grant
SELECT * FROM dba_tab_privs WHERE table_name = 'DBMS_LOCK' AND grantee = 'TEST';
