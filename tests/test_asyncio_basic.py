from contextlib import AsyncExitStack
from os import cpu_count
from random import randint
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from sqlalchemy_dlock.asyncio import sadlock

from .async_engines import *

CPU_COUNT = cpu_count() or 1


class BasicTestCase(IsolatedAsyncioTestCase):

    def setUp(self):
        create_engins()

    async def asyncTearDown(self):
        await dispose_engins()

    async def test_enter_exit(self):
        for engine in get_engins():
            key = uuid4().hex
            async with engine.begin() as conn:
                assert conn is not None
                lock = sadlock(conn, key)
                self.assertFalse(lock.acquired)
                await lock.acquire()
                self.assertTrue(lock.acquired)
                await lock.release()
                self.assertFalse(lock.acquired)

    async def test_with_statement(self):
        for engine in get_engins():
            async with engine.begin() as conn:
                assert conn is not None
                key = uuid4().hex
                async with sadlock(conn, key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    async def test_many_str_key(self):
        for engine in get_engins():
            async with engine.begin() as conn:
                assert conn is not None
                for _ in range(100):
                    key = uuid4().hex + uuid4().hex
                    async with sadlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    async def test_many_int_key(self):
        for engine in get_engins():
            async with engine.begin() as conn:
                assert conn is not None
                for _ in range(100):
                    key = randint(-0x8000_0000_0000_0000,
                                  0x7fff_ffff_ffff_ffff)
                    async with sadlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    async def test_timeout_positive(self):
        for engine in get_engins():
            key = uuid4().hex
            for _ in range(CPU_COUNT + 1):
                async with engine.begin() as conn:
                    assert conn is not None
                    lock = sadlock(conn, key)
                    try:
                        self.assertFalse(lock.locked)
                        r = await lock.acquire(timeout=randint(1, 1024))
                        self.assertTrue(r)
                        self.assertTrue(lock.acquired)
                    finally:
                        await lock.release()
                    self.assertFalse(lock.acquired)

    async def test_timeout_zero(self):
        for engine in get_engins():
            async with engine.begin() as conn:
                assert conn is not None
                key = uuid4().hex
                lock = sadlock(conn, key)
                try:
                    self.assertFalse(lock.locked)
                    r = await lock.acquire(timeout=0)
                    self.assertTrue(r)
                    self.assertTrue(lock.acquired)
                finally:
                    await lock.release()
                self.assertFalse(lock.acquired)

    async def test_timeout_negative(self):
        for engine in get_engins():
            for _ in range(CPU_COUNT + 1):
                async with engine.begin() as conn:
                    assert conn is not None
                    key = uuid4().hex
                    lock = sadlock(conn, key)
                    try:
                        r = await lock.acquire(timeout=-1*randint(1, 1024))
                        self.assertTrue(r)
                    finally:
                        await lock.release()
                    self.assertFalse(lock.acquired)

    async def test_timeout_none(self):
        for engine in get_engins():
            for _ in range(CPU_COUNT + 1):
                async with engine.begin() as conn:
                    assert conn is not None
                    key = uuid4().hex
                    lock = sadlock(conn, key)
                    try:
                        r = await lock.acquire(timeout=None)
                        self.assertTrue(r)
                    finally:
                        await lock.release()
                    self.assertFalse(lock.acquired)

    async def test_enter_locked(self):
        for engine in get_engins():
            key = uuid4().hex
            async with AsyncExitStack() as stack:
                conn0, conn1 = [
                    await stack.enter_async_context(engine.begin())
                    for _ in range(2)
                ]

                lock0 = sadlock(conn0, key)
                self.assertFalse(lock0.acquired)
                r = await lock0.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock0.acquired)

                lock1 = sadlock(conn1, key)
                self.assertFalse(lock1.acquired)
                r = await lock1.acquire(block=False)
                self.assertFalse(r)
                self.assertFalse(lock1.acquired)

                self.assertTrue(lock0.acquired)
                await lock0.release()
                self.assertFalse(lock0.acquired)

                r = await lock1.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock1.acquired)
                await lock1.release()
                self.assertFalse(lock1.acquired)

    async def test_release_unlocked_error(self):
        for engine in get_engins():
            key = uuid4().hex
            async with AsyncExitStack() as stack:
                conn0, conn1 = [
                    await stack.enter_async_context(engine.begin())
                    for _ in range(2)
                ]

                lock0 = sadlock(conn0, key)
                r = await lock0.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock0.locked)

                lock1 = sadlock(conn1, key)
                with self.assertRaisesRegex(ValueError, 'invoked on an unlocked lock'):
                    await lock1.release()
