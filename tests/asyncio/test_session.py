from sys import platform, version_info

if version_info >= (3, 8):
    if platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    from os import getenv
    from unittest import IsolatedAsyncioTestCase
    from uuid import uuid1
    from warnings import warn

    from sqlalchemy.ext.asyncio import AsyncSession

    from sqlalchemy_dlock.asyncio import create_async_sadlock

    from .engines import create_engines, dispose_engines, get_engines

    if getenv("NO_ASYNCIO"):
        warn('The test module will not run because environment variable "NO_ASYNCIO" was set')

    else:

        class SessionTestCase(IsolatedAsyncioTestCase):
            sessions = []

            def setUp(self):
                create_engines()

            async def asyncTearDown(self):
                await dispose_engines()

            async def test_once(self):
                key = uuid1().hex
                for engine in get_engines():
                    session = AsyncSession(engine)
                    async with session.begin():
                        async with create_async_sadlock(session, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)
