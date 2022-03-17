from os import getenv
from platform import python_version
from unittest import IsolatedAsyncioTestCase
from uuid import uuid1
from warnings import warn

from dotenv import load_dotenv
from packaging.version import parse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_dlock.asyncio import create_async_sadlock

from .engines import dispose_engins, get_engins

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

        class SessionTestCase(IsolatedAsyncioTestCase):
            sessions = []

            @classmethod
            def setUp(cls):
                for engine in get_engins():
                    session = AsyncSession(bind=engine)
                    cls.sessions.append(session)

            @classmethod
            async def asyncTearDown(cls):
                await dispose_engins()

            async def test_once(self):
                key = uuid1().hex
                for session in self.sessions:
                    async with session.begin():
                        async with create_async_sadlock(session, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

            async def test_seprated_connection(self):
                key = uuid1().hex
                for session in self.sessions:
                    with session.begin():
                        session.commit()
                        lock = create_async_sadlock(session, key)
                        session.rollback()
                        r = await lock.acquire()
                        self.assertTrue(r)
                        session.close()
                        await lock.release()
                        self.assertFalse(lock.acquired)
