from unittest import TestCase
from uuid import uuid4

from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy_dlock import sadlock
from .engines import ENGINES


class ScopedSessionTestCase(TestCase):

    def setUpClass(self):
        self.Sessions = []
        self.sessions = []
        for engine in ENGINES:
            factory = sessionmaker(bind=engine)
            Session = scoped_session(factory)
            self.Sessions.append(Session)
            self.sessions.append(Session())

    def tearDownClass(self):
        for Session in self.Sessions:
            Session.remove()

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_once(self):
        key = uuid4().hex
        for session in self.sessions:
            with sadlock(session, key) as lock:
                self.assertTrue(lock.acquired)
            self.assertFalse(lock.acquired)

    def test_twice(self):
        key = uuid4().hex
        for session in self.sessions:
            for _ in range(2):
                with sadlock(session, key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_separated_connection(self):
        key = uuid4().hex
        for session in self.sessions:
            session.commit()
            lock = sadlock(session, key)
            session.rollback()
            self.assertTrue(lock.acquire())
            session.close()
            lock.release()
            self.assertFalse(lock.acquired)
