from contextlib import ExitStack, closing
from os import cpu_count
from random import randint
from unittest import TestCase
from uuid import uuid4

from sqlalchemy_dlock import sadlock

from .engines import ENGINES

CPU_COUNT = cpu_count() or 1


class BasicTestCase(TestCase):

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_enter_exit(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                lock = sadlock(conn, key)
                self.assertFalse(lock.acquired)
                lock.acquire()
                self.assertTrue(lock.acquired)
                lock.release()
                self.assertFalse(lock.acquired)

    def test_with_statement(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with sadlock(conn, key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_many_str_key(self):
        for engine in ENGINES:
            for _ in range(100):
                with engine.connect() as conn:
                    key = uuid4().hex + uuid4().hex
                    with sadlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_many_int_key(self):
        for engine in ENGINES:
            for _ in range(100):
                with engine.connect() as conn:
                    key = randint(-0x8000_0000_0000_0000,
                                  0x7fff_ffff_ffff_ffff)
                    with sadlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_closing(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(sadlock(conn, key)) as lock:
                    self.assertFalse(lock.acquired)
                    self.assertTrue(lock.acquire())
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_no_blocking(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(sadlock(conn, key)) as lock:
                    self.assertFalse(lock.acquired)
                    acquired = lock.acquire(False)
                    self.assertTrue(acquired)
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_timeout_positive(self):
        for engine in ENGINES:
            key = uuid4().hex
            for _ in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=randint(1, 1024)))
                    self.assertFalse(lock.acquired)

    def test_timeout_zero(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(sadlock(conn, key)) as lock:
                    self.assertTrue(lock.acquire(timeout=0))
                self.assertFalse(lock.acquired)

    def test_timeout_negative(self):
        for engine in ENGINES:
            key = uuid4().hex
            for _ in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(
                            timeout=-1*randint(1, 1024)))
                    self.assertFalse(lock.acquired)

    def test_timeout_none(self):
        for engine in ENGINES:
            key = uuid4().hex
            for i in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=None))
                    self.assertFalse(lock.acquired)

    def test_acquired_property(self):
        for engine in ENGINES:
            key = uuid4().hex
            for i in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(sadlock(conn, key)) as lock:
                        self.assertFalse(lock.acquired)
                        lock.acquired = True
                        self.assertTrue(lock.acquired)
                        lock.acquired = False
                        self.assertFalse(lock.acquired)
                        lock.acquired = True
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_enter_locked(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [
                    stack.enter_context(engine.connect())
                    for _ in range(2)
                ]
                lock0 = sadlock(conn0, key)
                self.assertTrue(lock0.acquire(False))
                lock1 = sadlock(conn1, key)
                self.assertFalse(lock1.acquire(False))
                lock0.release()
                self.assertFalse(lock0.acquired)
                self.assertTrue(lock1.acquire(False))
                lock1.release()
                self.assertFalse(lock1.acquired)

    def test_release_unlocked_error(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [
                    stack.enter_context(engine.connect())
                    for _ in range(2)
                ]
                lock0 = sadlock(conn0, key)
                self.assertTrue(lock0.acquire(False))
                lock1 = sadlock(conn1, key)
                with self.assertRaisesRegex(ValueError, 'invoked on an unlocked lock'):
                    lock1.release()
