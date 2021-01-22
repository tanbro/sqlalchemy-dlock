from contextlib import ExitStack, closing
from os import cpu_count
from random import randint
from unittest import TestCase
from uuid import uuid4

from sqlalchemy_dlock import make_sa_dlock
from .engines import ENGINES


class BasicTestCase(TestCase):

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_enter_exit(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                lock = make_sa_dlock(conn, key)
                self.assertFalse(lock.acquired)
                lock.acquire()
                self.assertTrue(lock.acquired)
                lock.release()
                self.assertFalse(lock.acquired)

    def test_with_statement(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with make_sa_dlock(conn, key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_int_key(self):
        for engine in ENGINES:
            for _ in range(10):
                with engine.connect() as conn:
                    key = randint(-0x8000_0000_0000_0000, 0x7fff_ffff_ffff_ffff)
                    with make_sa_dlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_closing(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(make_sa_dlock(conn, key)) as lock:
                    self.assertFalse(lock.acquired)
                    lock.acquire()
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_enter_exit_may_times(self):
        for engine in ENGINES:
            key = uuid4().hex
            for _ in range(cpu_count() + 1):
                with engine.connect() as conn:
                    with make_sa_dlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_no_blocking(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(make_sa_dlock(conn, key)) as lock:
                    self.assertFalse(lock.acquired)
                    acquired = lock.acquire(False)
                    self.assertTrue(acquired)
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_timeout_zero(self):
        for engine in ENGINES:
            key = uuid4().hex
            for _ in range(cpu_count() + 1):
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=0))
                    self.assertFalse(lock.acquired)

    def test_timeout_negative(self):
        for engine in ENGINES:
            key = uuid4().hex
            for i in range(cpu_count() + 1):
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=-1 * (i + 1)))
                    self.assertFalse(lock.acquired)

    def test_acquire_locked(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [
                    stack.enter_context(engine.connect())
                    for _ in range(2)
                ]
                lock0 = make_sa_dlock(conn0, key)
                self.assertTrue(lock0.acquire(timeout=0))
                lock1 = make_sa_dlock(conn1, key)
                self.assertFalse(lock1.acquire(timeout=0))
                lock0.release()
                self.assertFalse(lock0.acquired)
                self.assertTrue(lock1.acquire())
                lock1.release()
                self.assertFalse(lock1.acquired)

    def test_release_unlocked(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [
                    stack.enter_context(engine.connect())
                    for _ in range(2)
                ]
                lock0 = make_sa_dlock(conn0, key)
                self.assertTrue(lock0.acquire())
                lock1 = make_sa_dlock(conn1, key)
                with self.assertRaisesRegex(RuntimeError, 'invoked on an unlocked lock'):
                    lock1.release()
