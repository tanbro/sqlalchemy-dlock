from os import getenv
from platform import python_version
from uuid import uuid1
from warnings import warn

from packaging.version import parse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_dlock.asyncio import create_async_sadlock

from .engines import dispose_engins, get_engins, create_engines


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
        from unittest import IsolatedAsyncioTestCase

        class SessionTestCase(IsolatedAsyncioTestCase):
            sessions = []

            def setUp(self):
                create_engines()

            async def asyncTearDown(self):
                await dispose_engins()

            async def test_once(self):
                key = uuid1().hex
                for engine in get_engins():
                    session = AsyncSession(engine)
                    async with session.begin():
                        async with create_async_sadlock(session, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)
