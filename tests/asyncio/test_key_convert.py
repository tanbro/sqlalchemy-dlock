from multiprocessing import cpu_count
from os import getenv
from platform import python_version
from random import choice
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4
from warnings import warn
from zlib import crc32

from dotenv import load_dotenv
from packaging.version import parse
from sqlalchemy_dlock.asyncio import create_async_sadlock
from sqlalchemy_dlock.impl.mysql import MYSQL_LOCK_NAME_MAX_LENGTH

from .engines import create_engins, dispose_engins, get_engins

CPU_COUNT = cpu_count()


load_dotenv()

if getenv('NO_ASYNCIO'):
    warn('The test module will not run because environment vairable "NO_ASYNCIO" was set')

else:

    MIN_PYTHON_VERSION = '3.8'

    if parse(python_version()) < parse(MIN_PYTHON_VERSION):
        warn(
            'The test module can not run on python version earlier than {}'
            .format(MIN_PYTHON_VERSION)
        )

    else:

        class KeyConvertTestCase(IsolatedAsyncioTestCase):

            def setUp(self):
                create_engins()

            async def asyncTearDown(self):
                await dispose_engins()

            async def test_convert(self):
                for engine in get_engins():
                    key = uuid4().hex

                    if engine.name == 'mysql':
                        def _convert(k):  # type: ignore
                            return 'key is "{}"'.format(k)
                    elif engine.name == 'postgresql':
                        def _convert(k):  # type: ignore
                            return crc32(str(k).encode())
                    else:
                        raise NotImplementedError()

                    async with engine.connect() as conn:
                        async with create_async_sadlock(conn, key, convert=_convert) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

            async def test_mysql_key_max_length(self):
                for engine in get_engins():
                    if engine.name != 'mysql':
                        continue
                    key = ''.join(
                        choice([chr(n) for n in range(0x20, 0x7f)])
                        for _ in range(MYSQL_LOCK_NAME_MAX_LENGTH)
                    )
                    async with engine.connect() as conn:
                        async with create_async_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

            async def test_mysql_key_gt_max_length(self):
                for engine in get_engins():
                    if engine.name != 'mysql':
                        continue
                    key = ''.join(
                        choice([chr(n) for n in range(0x20, 0x7f)])
                        for _ in range(MYSQL_LOCK_NAME_MAX_LENGTH + 1)
                    )
                    async with engine.connect() as conn:
                        with self.assertRaises(ValueError):
                            create_async_sadlock(conn, key)

            async def test_postgresql_key_max(self):
                for engine in get_engins():
                    if engine.name != 'postgresql':
                        continue
                    key = 2**64-1
                    async with engine.connect() as conn:
                        async with create_async_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

            async def test_postgresql_key_over_max(self):
                for engine in get_engins():
                    if engine.name != 'postgresql':
                        continue
                    key = 2**64
                    async with engine.connect() as conn:
                        with self.assertRaises(OverflowError):
                            create_async_sadlock(conn, key)

            async def test_postgresql_key_min(self):
                for engine in get_engins():
                    if engine.name != 'postgresql':
                        continue
                    key = -2**63
                    async with engine.connect() as conn:
                        async with create_async_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

            async def test_postgresql_key_over_min(self):
                for engine in get_engins():
                    if engine.name != 'postgresql':
                        continue
                    key = -2**63 - 1
                    async with engine.connect() as conn:
                        with self.assertRaises(OverflowError):
                            create_async_sadlock(conn, key)

            async def test_key_wrong_type(self):
                for engine in get_engins():
                    async with engine.connect() as conn:
                        for k in (tuple(), dict(), set(), list(), object()):
                            with self.assertRaises(TypeError):
                                create_async_sadlock(conn, k)