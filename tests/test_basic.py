from contextlib import ExitStack, closing
from multiprocessing import cpu_count
from random import randint
from secrets import token_bytes, token_hex
from unittest import TestCase
from uuid import uuid4

from sqlalchemy_dlock import create_sadlock

from .engines import ENGINES

CPU_COUNT = cpu_count()


class BasicTestCase(TestCase):
    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_enter_exit(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                lock = create_sadlock(conn, key)
                self.assertFalse(lock.locked)
                lock.acquire()
                self.assertTrue(lock.locked)
                lock.release()
                self.assertFalse(lock.locked)

    def test_with_statement(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with create_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_timeout_with_statement(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [stack.enter_context(engine.connect()) for _ in range(2)]
                lock0 = create_sadlock(conn0, key)
                self.assertTrue(lock0.acquire(False))
                with self.assertRaises(TimeoutError):
                    with create_sadlock(conn1, key, contextual_timeout=1):
                        pass
                lock0.release()
                self.assertFalse(lock0.locked)

    def test_many_str_key(self):
        for engine in ENGINES:
            for _ in range(100):
                with engine.connect() as conn:
                    key = uuid4().hex + uuid4().hex
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

    def test_many_int_key(self):
        for engine in ENGINES:
            for _ in range(100):
                with engine.connect() as conn:
                    key = randint(-0x8000_0000_0000_0000, 0x7FFF_FFFF_FFFF_FFFF)
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

    def test_many_bytes_key(self):
        for engine in ENGINES:
            for _ in range(100):
                with engine.connect() as conn:
                    if engine.name == "mysql":
                        key = token_hex().encode()
                    elif engine.name == "postgresql":
                        key = token_bytes()
                    else:
                        raise NotImplementedError()
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

    def test_closing(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(create_sadlock(conn, key)) as lock:
                    self.assertFalse(lock.locked)
                    self.assertTrue(lock.acquire())
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_no_blocking(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(create_sadlock(conn, key)) as lock:
                    self.assertFalse(lock.locked)
                    acquired = lock.acquire(False)
                    self.assertTrue(acquired)
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    def test_invoke_locked_lock(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with create_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                    self.assertRaisesRegex(ValueError, "invoked on a locked lock", lock.acquire)
                self.assertFalse(lock.locked)

    def test_invoke_unlocked_lock(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(create_sadlock(conn, key)) as lock:
                    self.assertFalse(lock.locked)
                    self.assertRaisesRegex(ValueError, "invoked on an unlocked lock", lock.release)
                self.assertFalse(lock.locked)

    def test_timeout_positive(self):
        for engine in ENGINES:
            key = uuid4().hex
            for _ in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=randint(1, 1024)))
                    self.assertFalse(lock.locked)

    def test_timeout_zero(self):
        for engine in ENGINES:
            key = uuid4().hex
            with engine.connect() as conn:
                with closing(create_sadlock(conn, key)) as lock:
                    self.assertTrue(lock.acquire(timeout=0))
                self.assertFalse(lock.locked)

    def test_timeout_negative(self):
        for engine in ENGINES:
            key = uuid4().hex
            for _ in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=-1 * randint(1, 1024)))
                    self.assertFalse(lock.locked)

    def test_timeout_none(self):
        for engine in ENGINES:
            key = uuid4().hex
            for i in range(CPU_COUNT + 1):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(timeout=None))
                    self.assertFalse(lock.locked)

    def test_enter_locked(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [stack.enter_context(engine.connect()) for _ in range(2)]
                lock0 = create_sadlock(conn0, key)
                self.assertTrue(lock0.acquire(False))
                lock1 = create_sadlock(conn1, key)
                self.assertFalse(lock1.acquire(False))
                lock0.release()
                self.assertFalse(lock0.locked)
                self.assertTrue(lock1.acquire(False))
                lock1.release()
                self.assertFalse(lock1.locked)

    def test_release_unlocked_error(self):
        for engine in ENGINES:
            key = uuid4().hex
            with ExitStack() as stack:
                conn0, conn1 = [stack.enter_context(engine.connect()) for _ in range(2)]
                lock0 = create_sadlock(conn0, key)
                self.assertTrue(lock0.acquire(False))
                lock1 = create_sadlock(conn1, key)
                with self.assertRaisesRegex(ValueError, "invoked on an unlocked lock"):
                    lock1.release()
