from contextlib import closing
from threading import Barrier, Thread
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from sqlalchemy_dlock import make_sa_dlock
from .engines import ENGINES


class MutliThreadTestCase(TestCase):

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_non_blocking(self):
        key = uuid4().hex
        delay = 1
        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with make_sa_dlock(conn, key) as lock:
                        b.wait()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
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
        delay = 3
        timeout = 1
        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with make_sa_dlock(conn, key) as lock:
                        b.wait()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
                        b.wait()
                        ts = time()
                        self.assertFalse(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time() - ts, timeout)
                        self.assertFalse(lock.acquired)

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_timeout_success(self):
        key = uuid4().hex
        delay = 1
        timeout = 3

        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with make_sa_dlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        b.wait()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
                        b.wait()
                        ts = time()
                        self.assertTrue(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time() - ts, delay)
                        self.assertGreaterEqual(timeout, time() - ts)
                        self.assertTrue(lock.acquired)

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_no_blocking_fail(self):
        key = uuid4().hex
        delay = 1

        for engine in ENGINES:
            bar = Barrier(2)

            def fn1(b):
                with engine.connect() as conn:
                    with make_sa_dlock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        b.wait()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(b):
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
                        b.wait()
                        self.assertFalse(lock.acquire(False))

            trd1 = Thread(target=fn1, args=(bar,))
            trd2 = Thread(target=fn2, args=(bar,))

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_release_omitted(self):
        key = uuid4().hex

        for engine in ENGINES:
            def fn1():
                conn = engine.connect()
                lock = make_sa_dlock(conn, key)
                self.assertTrue(lock.acquire(False))

            def fn2():
                with engine.connect() as conn:
                    with closing(make_sa_dlock(conn, key)) as lock:
                        self.assertTrue(lock.acquire(False))

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd1.join()

            trd2.start()
            trd2.join()
