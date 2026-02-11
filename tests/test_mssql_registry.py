"""Test MSSQL registry entries"""
from unittest import TestCase

from sqlalchemy_dlock.registry import ASYNCIO_REGISTRY, REGISTRY, find_lock_class


class MSSQLRegistryTestCase(TestCase):
    """Test that MSSQL registry entries exist and are correctly configured"""

    def test_mssql_sync_registry_exists(self):
        """MSSQL should have a sync registry entry"""
        self.assertIn("mssql", REGISTRY)
        self.assertEqual(REGISTRY["mssql"]["module"], ".lock.mssql")
        self.assertEqual(REGISTRY["mssql"]["class"], "MssqlSadLock")

    def test_mssql_async_registry_exists(self):
        """MSSQL should have an async registry entry"""
        self.assertIn("mssql", ASYNCIO_REGISTRY)
        self.assertEqual(ASYNCIO_REGISTRY["mssql"]["module"], ".lock.mssql")
        self.assertEqual(ASYNCIO_REGISTRY["mssql"]["class"], "MssqlAsyncSadLock")

    def test_mssql_sync_lock_class(self):
        """Should be able to get MSSQL sync lock class"""
        lock_class = find_lock_class("mssql", is_asyncio=False)
        self.assertEqual(lock_class.__name__, "MssqlSadLock")

    def test_mssql_async_lock_class(self):
        """Should be able to get MSSQL async lock class"""
        lock_class = find_lock_class("mssql", is_asyncio=True)
        self.assertEqual(lock_class.__name__, "MssqlAsyncSadLock")
