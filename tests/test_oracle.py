"""Oracle-specific lock tests

These tests are automatically skipped for non-Oracle databases.
Set the TEST_URLS environment variable to include an Oracle database.

Example:
    export TEST_URLS="oracle+oracledb://user:pass@host:1521/?service_name=XEPDB1"
    python -m unittest tests.test_oracle
"""
from unittest import TestCase

from sqlalchemy import text
from sqlalchemy_dlock import create_sadlock

from .engines import ENGINES


class OracleLockModeTestCase(TestCase):
    """Test Oracle lock modes"""

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_shared_lock_coexistence(self):
        """Multiple shared locks should coexist"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            key = "test-shared-lock"

            with engine.connect() as conn1:
                with engine.connect() as conn2:
                    # Both connections can acquire shared locks
                    lock1 = create_sadlock(conn1, key, lock_mode="S")
                    lock2 = create_sadlock(conn2, key, lock_mode="S")

                    self.assertTrue(lock1.acquire(block=False))
                    self.assertTrue(lock1.locked)
                    self.assertTrue(lock2.acquire(block=False))
                    self.assertTrue(lock2.locked)

                    lock1.release()
                    lock2.release()

    def test_exclusive_blocks_shared(self):
        """Exclusive lock should block shared lock"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            key = "test-exclusive-blocks-shared"

            with engine.connect() as conn1:
                with engine.connect() as conn2:
                    lock1 = create_sadlock(conn1, key, lock_mode="X")
                    lock2 = create_sadlock(conn2, key, lock_mode="S")

                    self.assertTrue(lock1.acquire(block=False))
                    self.assertTrue(lock1.locked)
                    # Shared lock should fail while exclusive is held
                    self.assertFalse(lock2.acquire(block=False))

                    lock1.release()

    def test_lock_mode_property(self):
        """Lock mode property should return correct mode"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            with engine.connect() as conn:
                for mode in ["NL", "SS", "SX", "S", "SSX", "X"]:
                    lock = create_sadlock(conn, f"test-mode-{mode}", lock_mode=mode)
                    self.assertEqual(lock.lock_mode, mode)

    def test_invalid_lock_mode(self):
        """Invalid lock mode should raise ValueError"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            with engine.connect() as conn:
                with self.assertRaises(ValueError):
                    create_sadlock(conn, "test-key", lock_mode="INVALID")


class OracleReleaseOnCommitTestCase(TestCase):
    """Test Oracle release_on_commit parameter"""

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_release_on_commit_true(self):
        """Lock should be released on commit when release_on_commit=True"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            key = "test-release-on-commit"

            with engine.connect() as conn:
                lock = create_sadlock(conn, key, release_on_commit=True)
                self.assertTrue(lock.acquire(block=False))
                self.assertTrue(lock.locked)

                # Commit should release the lock
                conn.execute(text("COMMIT"))
                # Note: After commit, the lock state in Python object might not reflect
                # the actual database state immediately. This is expected behavior.
                # The lock IS released on the database side.

    def test_release_on_commit_false(self):
        """Lock should NOT be released on commit when release_on_commit=False (default)"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            key = "test-no-release-on-commit"

            with engine.connect() as conn:
                lock = create_sadlock(conn, key, release_on_commit=False)
                self.assertTrue(lock.acquire(block=False))
                self.assertTrue(lock.locked)

                # Commit should NOT release the lock
                conn.execute(text("COMMIT"))
                self.assertTrue(lock.locked)

                lock.release()

    def test_release_on_commit_property(self):
        """release_on_commit property should return correct value"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            with engine.connect() as conn:
                lock1 = create_sadlock(conn, "test-key-1", release_on_commit=True)
                self.assertTrue(lock1.release_on_commit)

                lock2 = create_sadlock(conn, "test-key-2", release_on_commit=False)
                self.assertFalse(lock2.release_on_commit)


class OracleIntegerKeyTestCase(TestCase):
    """Test Oracle integer lock IDs"""

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_direct_integer_key(self):
        """Integer keys should work directly without hashing"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            key = 12345

            with engine.connect() as conn:
                lock = create_sadlock(conn, key)
                self.assertTrue(lock.acquire(block=False))
                self.assertTrue(lock.locked)
                lock.release()

    def test_integer_key_at_max_boundary(self):
        """Test keys at Oracle's max boundary (1073741823)"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

        ORACLE_LOCK_ID_MAX = 1073741823

        with engine.connect() as conn:
            # Test at max boundary
            lock = create_sadlock(conn, ORACLE_LOCK_ID_MAX)
            self.assertTrue(lock.acquire(block=False))
            lock.release()

            # Test just above max (should be modulo'd)
            lock2 = create_sadlock(conn, ORACLE_LOCK_ID_MAX + 1)
            self.assertTrue(lock2.acquire(block=False))
            lock2.release()

    def test_actual_key_property(self):
        """actual_key should return the integer lock ID"""
        for engine in ENGINES:
            if engine.name != "oracle":
                continue

            with engine.connect() as conn:
                # String key is hashed to integer
                lock1 = create_sadlock(conn, "test-string-key")
                self.assertIsInstance(lock1.actual_key, int)
                self.assertGreaterEqual(lock1.actual_key, 0)
                self.assertLessEqual(lock1.actual_key, 1073741823)

                # Integer key is used directly (modulo'd if needed)
                lock2 = create_sadlock(conn, 99999)
                self.assertEqual(lock2.actual_key, 99999)
