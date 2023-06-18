from sys import version_info

if version_info >= (3, 8):
    import asyncio
    from logging import getLogger
    from multiprocessing import cpu_count
    from time import time
    from unittest import IsolatedAsyncioTestCase
    from uuid import uuid4

    from sqlalchemy_dlock.asyncio import create_async_sadlock

    from .engines import create_engines, dispose_engines, get_engines

    CPU_COUNT = cpu_count()

    class ConcurrencyTestCase(IsolatedAsyncioTestCase):
        def setUp(self):
            create_engines()

        async def asyncTearDown(self):
            await dispose_engines()

        async def test_timeout(self):
            logger = getLogger(__name__)

            key = uuid4().hex
            for engine in get_engines():
                event = asyncio.Event()

                async def coro1():
                    async with engine.begin() as conn:
                        async with create_async_sadlock(conn, key) as lck:
                            logger.debug("coro1: acquired")
                            self.assertTrue(lck.locked)
                            logger.debug("coro1: barrier.wait()")
                            event.set()
                            logger.debug("coro1: sleep")
                            await asyncio.sleep(3)
                        self.assertFalse(lck.locked)
                        logger.debug("coro1: end")

                async def coro2():
                    async with engine.begin() as conn:
                        timeout = 1
                        l1 = create_async_sadlock(conn, key)
                        logger.debug("coro2: barrier.wait()")
                        await event.wait()
                        t0 = time()
                        logger.debug("coro2: acquire ...")
                        is_ok = await l1.acquire(timeout=timeout)
                        logger.debug("coro2: acquire -> %s", is_ok)
                        self.assertFalse(is_ok)
                        self.assertFalse(l1.locked)
                        self.assertGreaterEqual(time() - t0, timeout)

                aws = (
                    asyncio.create_task(coro1()),
                    asyncio.create_task(coro2()),
                )
                await asyncio.wait(aws)
