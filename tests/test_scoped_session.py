from contextlib import closing
from unittest import TestCase
import unittest
from uuid import uuid1
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.exc import StatementError, ResourceClosedError
from sqlalchemy_dlock import make_session_level_lock

from .engines import ENGINES
from .utils import session_scope

Session = None

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
        key = uuid1().hex
        for Session in self.Sessions:
            with make_session_level_lock(Session.connection(), key) as lock:
                self.assertTrue(lock.acquired)
            self.assertFalse(lock.acquired)

    def test_twice(self):
        key = uuid1().hex
        for Session in self.Sessions:
            for _ in range(2):
                with make_session_level_lock(Session.connection(), key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_seprated_connection(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with Session.get_bind().connect() as conn:
                Session.commit()
                lock = make_session_level_lock(conn, key)
                Session.rollback()
                self.assertTrue(lock.acquire())
                Session.close()
                lock.release()
                self.assertFalse(lock.acquired)
