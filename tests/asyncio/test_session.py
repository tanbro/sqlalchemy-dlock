from unittest import IsolatedAsyncioTestCase
from uuid import uuid1

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy_dlock.asyncio import create_async_sadlock

from .engines import create_engines, dispose_engines, get_engines


class SessionTestCase(IsolatedAsyncioTestCase):
    sessions = []  # type: ignore[var-annotated]

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
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)
