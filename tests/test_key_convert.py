from os import cpu_count
from random import choice
from unittest import TestCase
from uuid import uuid4
from zlib import crc32

from sqlalchemy_dlock import create_sadlock
from sqlalchemy_dlock.lock.mysql import MYSQL_LOCK_NAME_MAX_LENGTH

from .engines import ENGINES

CPU_COUNT = cpu_count() or 1


class KeyConvertTestCase(TestCase):
    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_convert(self):
        for engine in ENGINES:
            key = uuid4().hex

            if engine.name == "mysql":

                def _convert(k):
                    return 'key is "{}"'.format(k)

            elif engine.name == "postgresql":

                def _convert(k):
                    return crc32(str(k).encode())

            else:
                raise NotImplementedError()

            with engine.connect() as conn:
                with create_sadlock(conn, key, convert=_convert) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_mysql_key_max_length(self):
        for engine in ENGINES:
            if engine.name != "mysql":
                continue
            key = "".join(choice([chr(n) for n in range(0x20, 0x7F)]) for _ in range(MYSQL_LOCK_NAME_MAX_LENGTH))
            with engine.connect() as conn:
                with create_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_mysql_key_gt_max_length(self):
        for engine in ENGINES:
            if engine.name != "mysql":
                continue
            key = "".join(choice([chr(n) for n in range(0x20, 0x7F)]) for _ in range(MYSQL_LOCK_NAME_MAX_LENGTH + 1))
            with engine.connect() as conn:
                with self.assertRaises(ValueError):
                    create_sadlock(conn, key)

    def test_postgresql_key_max(self):
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue
            key = 2**64 - 1
            with engine.connect() as conn:
                with create_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_postgresql_key_over_max(self):
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue
            key = 2**64
            with engine.connect() as conn:
                with self.assertRaises(OverflowError):
                    create_sadlock(conn, key)

    def test_postgresql_key_min(self):
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue
            key = -(2**63)
            with engine.connect() as conn:
                with create_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_postgresql_key_over_min(self):
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue
            key = -(2**63) - 1
            with engine.connect() as conn:
                with self.assertRaises(OverflowError):
                    create_sadlock(conn, key)

    def test_key_wrong_type(self):
        for engine in ENGINES:
            with engine.connect() as conn:
                for k in (tuple(), dict(), set(), list(), object()):
                    with self.assertRaises(TypeError):
                        create_sadlock(conn, k)
