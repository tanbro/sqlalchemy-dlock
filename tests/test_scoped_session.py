from unittest import TestCase
from uuid import uuid4

from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy_dlock import sadlock
from .engines import ENGINES


class ScopedSessionTestCase(TestCase):
    Sessions = []

    @classmethod
    def setUpClass(cls):
        for engine in ENGINES:
            factory = sessionmaker(bind=engine)
            Session = scoped_session(factory)
            Session()
            cls.Sessions.append(Session)

    @classmethod
    def tearDownClass(cls):
        for Session in cls.Sessions:
            Session.remove()

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_once(self):
        key = uuid4().hex
        for Session in self.Sessions:
            with sadlock(Session.connection(), key) as lock:
                self.assertTrue(lock.acquired)
            self.assertFalse(lock.acquired)

    def test_twice(self):
        key = uuid4().hex
        for Session in self.Sessions:
            for _ in range(2):
                with sadlock(Session.connection(), key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_separated_connection(self):
        key = uuid4().hex
        for Session in self.Sessions:
            with Session.get_bind().connect() as conn:
                Session.commit()
                lock = sadlock(conn, key)
                Session.rollback()
                self.assertTrue(lock.acquire())
                Session.close()
                lock.release()
                self.assertFalse(lock.acquired)
