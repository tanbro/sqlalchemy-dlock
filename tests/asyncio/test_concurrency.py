# https://github.com/sqlalchemy/sqlalchemy/issues/5581
#
# Multiple Co-routines of SQL executions on a same Engine's Connection/Session will case a dead-lock.
# So we shall do that on different Engine objects!


import asyncio
from time import time
from unittest import IsolatedAsyncioTestCase
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine

from sqlalchemy_dlock import create_async_sadlock

from .engines import create_engines, dispose_engines, get_engines


class ConcurrencyTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        create_engines()

    async def asyncTearDown(self):
        await dispose_engines()

    async def test_timeout(self):
        key = uuid4().hex
        for engine in get_engines():
            delay = 3
            timeout = 1
            event = asyncio.Event()
            engine1 = create_async_engine(engine.url)
            engine2 = create_async_engine(engine.url)
            try:

                async def coro1():
                    async with engine1.connect() as conn:
                        async with create_async_sadlock(conn, key) as lck:
                            self.assertTrue(lck.locked)
                            event.set()
                            await asyncio.sleep(delay)
                        self.assertFalse(lck.locked)

                async def coro2():
                    async with engine2.connect() as conn:
                        lck = create_async_sadlock(conn, key)
                        await event.wait()
                        t0 = time()
                        is_ok = await lck.acquire(timeout=timeout)
                        self.assertFalse(is_ok)
                        self.assertFalse(lck.locked)
                        self.assertGreaterEqual(time() - t0, timeout)

                aws = (
                    asyncio.create_task(coro1()),
                    asyncio.create_task(coro2()),
                )
                await asyncio.wait(aws, timeout=delay * 2)
            finally:
                aws = (
                    asyncio.create_task(engine1.dispose()),
                    asyncio.create_task(engine2.dispose()),
                )
                await asyncio.wait(aws, timeout=delay * 2)
