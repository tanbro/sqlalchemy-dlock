from contextlib import ExitStack, closing
from os import cpu_count
from random import randint
from unittest import TestCase
from uuid import uuid1

from sqlalchemy_dlock import make_session_level_lock

from .engines import ENGINES


class BasicTestCase(TestCase):

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_enter_exit(self):
        key = uuid1().hex
        for engine in ENGINES:
            with engine.connect() as conn:
                lock = make_session_level_lock(conn, key)
                self.assertFalse(lock.acquired)
                lock.acquire()
                self.assertTrue(lock.acquired)
                lock.release()
                self.assertFalse(lock.acquired)

    def test_with_statement(self):
        key = uuid1().hex
        for engine in ENGINES:
            with engine.connect() as conn:
                with make_session_level_lock(conn, key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_int_key(self):
        for engine in ENGINES:
            for _ in range(10):
                with engine.connect() as conn:
                    key = randint(-0x8000_0000_0000_0000, 0x7fff_ffff_ffff_ffff)
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_closing(self):
        key = uuid1().hex
        for engine in ENGINES:
            with engine.connect() as conn:
                with closing(make_session_level_lock(conn, key)) as lock:
                    self.assertFalse(lock.acquired)
                    lock.acquire()
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_enter_exit_may_times(self):
        key = uuid1().hex
        for engine in ENGINES:
            for _ in range(cpu_count()+1):
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_no_blocking(self):
        key = uuid1().hex
        for engine in ENGINES:
            with engine.connect() as conn:
                with closing(make_session_level_lock(conn, key)) as lock:
                    self.assertFalse(lock.acquired)
                    acquired = lock.acquire(False)
                    self.assertTrue(acquired)
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_timeout_zero(self):
        key = uuid1().hex
        for engine in ENGINES:
            for _ in range(cpu_count()+1):
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=0))
                    self.assertFalse(lock.acquired)

    def test_timeout_negative(self):
        key = uuid1().hex
        for engine in ENGINES:
            for i in range(cpu_count()+1):
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=-1*(i+1)))
                    self.assertFalse(lock.acquired)

    def test_acquire_locked(self):
        key = uuid1().hex
        for engine in ENGINES:
            with ExitStack() as stack:
                conn0, conn1 = [
                    stack.enter_context(engine.connect())
                    for _ in range(2)
                ]
                lock0 = make_session_level_lock(conn0, key)
                self.assertTrue(lock0.acquire(timeout=0))
                lock1 = make_session_level_lock(conn1, key)
                self.assertFalse(lock1.acquire(timeout=0))
                lock0.release()
                self.assertFalse(lock0.acquired)
                self.assertTrue(lock1.acquire())
                lock1.release()
                self.assertFalse(lock1.acquired)

    def test_release_unlocked(self):
        key = uuid1().hex
        for engine in ENGINES:
            with ExitStack() as stack:
                conn0, conn1 = [
                    stack.enter_context(engine.connect())
                    for _ in range(2)
                ]
                lock0 = make_session_level_lock(conn0, key)
                self.assertTrue(lock0.acquire())
                lock1 = make_session_level_lock(conn1, key)
                with self.assertRaisesRegex(RuntimeError, 'invoked on an unlocked lock'):
                    lock1.release()
