from unittest import TestCase
from uuid import uuid1

from sqlalchemy.orm import sessionmaker

from sqlalchemy_dlock import create_sadlock

from .engines import ENGINES


class SessionTestCase(TestCase):
    Sessions = []

    @classmethod
    def setUpClass(cls):
        for engine in ENGINES:
            Session = sessionmaker(bind=engine)
            cls.Sessions.append(Session)

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_once(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with Session() as session:
                with create_sadlock(session, key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_cross_transaction(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with Session() as session:
                session.commit()
                lock = create_sadlock(session, key)
                session.rollback()
                self.assertTrue(lock.acquire())
                session.close()
                lock.release()
                self.assertFalse(lock.acquired)
