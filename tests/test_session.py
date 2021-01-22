from unittest import TestCase
from uuid import uuid1

from sqlalchemy.orm import sessionmaker

from sqlalchemy_dlock import make_sa_dlock
from .engines import ENGINES
from .utils import session_scope


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
            with session_scope(Session) as session:
                with make_sa_dlock(session.connection(), key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_seprated_connection(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                with session.get_bind().connect() as conn:
                    session.commit()
                    lock = make_sa_dlock(conn, key)
                    session.rollback()
                    self.assertTrue(lock.acquire())
                    session.close()
                    lock.release()
                    self.assertFalse(lock.acquired)
