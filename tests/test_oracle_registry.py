"""Test Oracle registry entries"""
from unittest import TestCase

from sqlalchemy_dlock.registry import ASYNCIO_REGISTRY, REGISTRY, find_lock_class


class OracleRegistryTestCase(TestCase):
    """Test that Oracle registry entries exist and are correctly configured"""

    def test_oracle_sync_registry_exists(self):
        """Oracle should have a sync registry entry"""
        self.assertIn("oracle", REGISTRY)
        self.assertEqual(REGISTRY["oracle"]["module"], ".lock.oracle")
        self.assertEqual(REGISTRY["oracle"]["class"], "OracleSadLock")

    def test_oracle_async_registry_exists(self):
        """Oracle should have an async registry entry"""
        self.assertIn("oracle", ASYNCIO_REGISTRY)
        self.assertEqual(ASYNCIO_REGISTRY["oracle"]["module"], ".lock.oracle")
        self.assertEqual(ASYNCIO_REGISTRY["oracle"]["class"], "OracleAsyncSadLock")

    def test_oracle_sync_lock_class(self):
        """Should be able to get Oracle sync lock class"""
        lock_class = find_lock_class("oracle", is_asyncio=False)
        self.assertEqual(lock_class.__name__, "OracleSadLock")

    def test_oracle_async_lock_class(self):
        """Should be able to get Oracle async lock class"""
        lock_class = find_lock_class("oracle", is_asyncio=True)
        self.assertEqual(lock_class.__name__, "OracleAsyncSadLock")
