from multiprocessing import cpu_count
from random import choice
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4
from zlib import crc32

from sqlalchemy_dlock import create_async_sadlock
from sqlalchemy_dlock.lock.mysql import MYSQL_LOCK_NAME_MAX_LENGTH

from .engines import create_engines, dispose_engines, get_engines

CPU_COUNT = cpu_count()


class KeyConvertTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        create_engines()

    async def asyncTearDown(self):
        await dispose_engines()

    async def test_convert(self):
        for engine in get_engines():
            key = uuid4().hex

            if engine.name == "mysql":

                def _convert(k):  # type: ignore
                    return f"key is {k!r}"

            elif engine.name == "postgresql":

                def _convert(k):  # type: ignore
                    return crc32(str(k).encode())

            else:
                raise NotImplementedError()

            async with engine.connect() as conn:
                async with create_async_sadlock(conn, key, convert=_convert) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    async def test_mysql_key_max_length(self):
        for engine in get_engines():
            if engine.name != "mysql":
                continue
            key = "".join(choice([chr(n) for n in range(0x20, 0x7F)]) for _ in range(MYSQL_LOCK_NAME_MAX_LENGTH))
            async with engine.connect() as conn:
                async with create_async_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    async def test_mysql_key_gt_max_length(self):
        for engine in get_engines():
            if engine.name != "mysql":
                continue
            key = "".join(choice([chr(n) for n in range(0x20, 0x7F)]) for _ in range(MYSQL_LOCK_NAME_MAX_LENGTH + 1))
            async with engine.connect() as conn:
                with self.assertRaises(ValueError):
                    create_async_sadlock(conn, key)

    async def test_mysql_key_not_a_string(self):
        keys = None, 1, 0, -1, 0.1, True, False, (), [], set(), {}, object()
        for engine in get_engines():
            if engine.name != "mysql":
                continue
            async with engine.connect() as conn:
                for k in keys:
                    with self.assertRaises(TypeError):
                        create_async_sadlock(conn, k, convert=lambda x: x)

    async def test_postgresql_key_max(self):
        for engine in get_engines():
            if engine.name != "postgresql":
                continue
            key = 2**63 - 1
            async with engine.connect() as conn:
                async with create_async_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    async def test_postgresql_key_over_max(self):
        for engine in get_engines():
            if engine.name != "postgresql":
                continue
            key = 2**63
            async with engine.connect() as conn:
                with self.assertRaises(OverflowError):
                    create_async_sadlock(conn, key)

    async def test_postgresql_key_min(self):
        for engine in get_engines():
            if engine.name != "postgresql":
                continue
            key = -(2**63)
            async with engine.connect() as conn:
                async with create_async_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    async def test_postgresql_key_over_min(self):
        for engine in get_engines():
            if engine.name != "postgresql":
                continue
            key = -(2**63) - 1
            async with engine.connect() as conn:
                with self.assertRaises(OverflowError):
                    create_async_sadlock(conn, key)

    async def test_key_wrong_type(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                for k in ((), {}, set(), [], object()):
                    with self.assertRaises(TypeError):
                        create_async_sadlock(conn, k)
