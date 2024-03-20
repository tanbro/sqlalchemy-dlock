import asyncio
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from sqlalchemy_dlock.asyncio import create_async_sadlock

from .engines import create_engines, dispose_engines, get_engines


class PgTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        create_engines()

    async def asyncTearDown(self):
        await dispose_engines()

    async def test_pg_invalid_interval(self):
        for engine in get_engines():
            if engine.name != "postgresql":
                continue
            key = uuid4().hex
            async with engine.connect() as conn:
                lck = create_async_sadlock(conn, key)
                with self.assertRaises(ValueError):
                    await lck.acquire(timeout=0, interval=-1)

    async def test_simple_xact(self):
        key = uuid4().hex
        for engine in get_engines():
            if engine.name != "postgresql":
                continue
            async with engine.connect() as conn:
                lck = create_async_sadlock(conn, key, xact=True)
                async with conn.begin():
                    self.assertTrue(await lck.acquire())

    async def test_xact_coro(self):
        key = uuid4().hex
        for engine in get_engines():
            if engine.name != "postgresql":
                continue

            bar = asyncio.Barrier(2)

            async def coro():
                async with engine.connect() as c_:
                    l_ = create_async_sadlock(c_, key, xact=True)
                    await asyncio.wait_for(bar.wait(), 10)
                    async with c_.begin():
                        self.assertFalse(await l_.acquire(block=False))
                        await asyncio.sleep(3)
                        self.assertTrue(await l_.acquire(block=False))

            task = asyncio.create_task(coro())

            async with engine.connect() as conn:
                lck = create_async_sadlock(conn, key, xact=True)
                async with conn.begin():
                    self.assertTrue(await lck.acquire(block=False))
                    await asyncio.wait_for(bar.wait(), 5)
                    await asyncio.sleep(3)

            await asyncio.wait_for(task, 10)
