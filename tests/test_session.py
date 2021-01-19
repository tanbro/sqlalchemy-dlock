from contextlib import closing
from os import cpu_count
from threading import Thread, Event
from time import sleep, time
from unittest import TestCase
from uuid import uuid1
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ResourceClosedError, StatementError
from sqlalchemy_dlock import make_session_level_lock

from .engines import ENGINES
from .utils import session_scope


class SessionTestCase(TestCase):

    Sessions = []

    @classmethod
    def setUpClass(cls):
        for engine in ENGINES:
            Session = sessionmaker(bind=engine)
            cls.Sessions.append(Session)

    def test_once(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                with make_session_level_lock(session.connection(), key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_error_acquire_after_commit(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                with closing(make_session_level_lock(session.connection(), key)) as lock:
                    session.commit()
                    with self.assertRaisesRegex(StatementError, "ResourceClosedError"):
                        lock.acquire()
                    self.assertFalse(lock.acquired)

    def test_error_acquire_after_rollback(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                with closing(make_session_level_lock(session.connection(), key)) as lock:
                    session.rollback()
                    with self.assertRaisesRegex(StatementError, "ResourceClosedError"):
                        lock.acquire()
                    self.assertFalse(lock.acquired)

    def test_error_acquire_after_close(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                with closing(make_session_level_lock(session.connection(), key)) as lock:
                    session.close()
                    with self.assertRaisesRegex(StatementError, "ResourceClosedError"):
                        lock.acquire()
                    self.assertFalse(lock.acquired)

    def test_error_release_after_commit(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                lock = make_session_level_lock(session.connection(), key)
                self.assertTrue(lock.acquire())
                session.commit()
                with self.assertRaisesRegex(StatementError, "ResourceClosedError"):
                    lock.release()

    def test_error_release_after_rollback(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                lock = make_session_level_lock(session.connection(), key)
                self.assertTrue(lock.acquire())
                session.rollback()
                with self.assertRaisesRegex(StatementError, "ResourceClosedError"):
                    lock.release()

    def test_error_release_after_close(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                lock = make_session_level_lock(session.connection(), key)
                self.assertTrue(lock.acquire())
                session.close()
                with self.assertRaisesRegex(StatementError, "ResourceClosedError"):
                    lock.release()

    def test_seprated_connection(self):
        key = uuid1().hex
        for Session in self.Sessions:
            with session_scope(Session) as session:
                with session.get_bind().connect() as conn:
                    session.commit()
                    lock = make_session_level_lock(conn, key)
                    session.commit()
                    self.assertTrue(lock.acquire())
                    session.commit()
                    lock.release()
                    self.assertFalse(lock.acquired)
