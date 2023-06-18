# https://github.com/sqlalchemy/sqlalchemy/issues/5581
#
# Disable the test temporary

from sys import version_info

# if version_info >= (3, 8):
if False:
    import asyncio
    from logging import getLogger
    from time import time
    from unittest import IsolatedAsyncioTestCase
    from uuid import uuid4

    from sqlalchemy_dlock.asyncio import create_async_sadlock

    from .engines import create_engines, dispose_engines, get_engines

    class ConcurrencyTestCase(IsolatedAsyncioTestCase):
        def setUp(self):
            self.logger = getLogger(self.__class__.__name__)
            create_engines()

        async def asyncTearDown(self):
            await dispose_engines()

        async def test_timeout(self):
            self.logger.warning(">>>")

            key = uuid4().hex
            for engine in get_engines():
                event = asyncio.Event()

                async def coro1():
                    self.logger.info("coro1: %s connect() %s ...", engine, engine.url)
                    async with engine.connect() as conn:
                        self.logger.info("coro1: create_async_sadlock then lock ...")
                        async with create_async_sadlock(conn, key) as lck:
                            self.logger.info("coro1: acquired")
                            self.assertTrue(lck.locked)
                            self.logger.info("coro1: event.set()")
                            event.set()
                            self.logger.info("coro1: sleep")
                            await asyncio.sleep(3)
                        self.assertFalse(lck.locked)
                        self.logger.debug("coro1: end")

                async def coro2():
                    self.logger.info("coro2: %s connect() %s ...", engine, engine.url)
                    async with engine.connect() as conn:
                        timeout = 1
                        self.logger.info("coro2: create_async_sadlock()")
                        l1 = create_async_sadlock(conn, key)
                        self.logger.info("coro2: event.wait()")
                        await event.wait()
                        t0 = time()
                        self.logger.info("coro2: acquire ...")
                        is_ok = await l1.acquire(timeout=timeout)
                        self.logger.info("coro2: acquire -> %s", is_ok)
                        self.assertFalse(is_ok)
                        self.assertFalse(l1.locked)
                        self.assertGreaterEqual(time() - t0, timeout)

                aws = (
                    asyncio.create_task(coro1()),
                    asyncio.create_task(coro2()),
                )
                self.logger.warning("wait ...")
                await asyncio.wait(aws)
