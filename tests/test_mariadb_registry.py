"""Test MariaDB registry entries"""
from unittest import TestCase

from sqlalchemy_dlock.registry import ASYNCIO_REGISTRY, REGISTRY, find_lock_class


class MariaDBRegistryTestCase(TestCase):
    """Test that MariaDB is properly aliased to MySQL implementation"""

    def test_mariadb_sync_registry_exists(self):
        """MariaDB should have a sync registry entry"""
        self.assertIn("mariadb", REGISTRY)
        self.assertEqual(REGISTRY["mariadb"]["module"], ".lock.mysql")
        self.assertEqual(REGISTRY["mariadb"]["class"], "MysqlSadLock")

    def test_mariadb_async_registry_exists(self):
        """MariaDB should have an async registry entry"""
        self.assertIn("mariadb", ASYNCIO_REGISTRY)
        self.assertEqual(ASYNCIO_REGISTRY["mariadb"]["module"], ".lock.mysql")
        self.assertEqual(ASYNCIO_REGISTRY["mariadb"]["class"], "MysqlAsyncSadLock")

    def test_mariadb_sync_lock_class(self):
        """Should be able to get MariaDB sync lock class"""
        lock_class = find_lock_class("mariadb", is_asyncio=False)
        self.assertEqual(lock_class.__name__, "MysqlSadLock")

    def test_mariadb_async_lock_class(self):
        """Should be able to get MariaDB async lock class"""
        lock_class = find_lock_class("mariadb", is_asyncio=True)
        self.assertEqual(lock_class.__name__, "MysqlAsyncSadLock")

    def test_mariadb_same_as_mysql(self):
        """MariaDB and MySQL should use the same lock implementation"""
        mysql_sync = find_lock_class("mysql", is_asyncio=False)
        mariadb_sync = find_lock_class("mariadb", is_asyncio=False)
        self.assertIs(mysql_sync, mariadb_sync)

        mysql_async = find_lock_class("mysql", is_asyncio=True)
        mariadb_async = find_lock_class("mariadb", is_asyncio=True)
        self.assertIs(mysql_async, mariadb_async)
