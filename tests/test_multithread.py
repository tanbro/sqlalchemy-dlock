from contextlib import closing
from threading import Barrier, Thread
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from sqlalchemy_dlock import create_sadlock

from .engines import ENGINES


class MultiThreadTestCase(TestCase):
    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_non_blocking_success(self):
        key = uuid4().hex
        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)
                    b.wait()

            def fn2(b):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        b.wait()
                        self.assertTrue(lock.acquire(False))

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_non_blocking_fail(self):
        key = uuid4().hex
        delay = 1.0

        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                        b.wait()
                        sleep(delay)
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        b.wait()
                        self.assertFalse(lock.acquire(False))

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_timeout_fail(self):
        key = uuid4().hex
        delay = 3.0
        timeout = 1.0
        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                        b.wait()
                        self.assertTrue(lock.locked)
                        sleep(delay)
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        b.wait()
                        ts = time()
                        self.assertFalse(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time() - ts, timeout)
                        self.assertFalse(lock.locked)

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_timeout_success(self):
        key = uuid4().hex
        delay = 1.0
        timeout = 3.0

        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with create_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                        b.wait()
                        sleep(delay)
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        b.wait()
                        ts = time()
                        self.assertTrue(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time() - ts, delay)
                        self.assertGreaterEqual(timeout, time() - ts)
                        self.assertTrue(lock.locked)

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_connection_released(self):
        key = uuid4().hex

        for engine in ENGINES:

            def fn1():
                with engine.connect() as conn:
                    lock = create_sadlock(conn, key)
                    self.assertTrue(lock.acquire(False))

            def fn2():
                with engine.connect() as conn:
                    with closing(create_sadlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(False))

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd1.join()

            trd2.start()
            trd2.join()
