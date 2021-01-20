from contextlib import closing
from threading import Barrier, Thread
from time import sleep, time
from unittest import TestCase
from uuid import uuid1

from sqlalchemy_dlock import make_session_level_lock

from .engines import ENGINES


class MutliThreadTestCase(TestCase):

    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_non_blocking(self):
        key = uuid1().hex
        delay = 1
        for engine in ENGINES:
            bar = Barrier(2, timeout=delay*3)

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        bar.wait()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        bar.wait()
                        self.assertFalse(lock.acquire(False))

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_timeout_fail(self):
        key = uuid1().hex
        delay = 3
        timeout = 1
        for engine in ENGINES:
            bar = Barrier(2, timeout=delay*3)

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        bar.wait()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        bar.wait()
                        ts = time()
                        self.assertFalse(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time()-ts, timeout)
                        self.assertFalse(lock.acquired)

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_timeout_success(self):
        key = uuid1().hex
        delay = 1
        timeout = 3

        for engine in ENGINES:

            bar = Barrier(2, timeout=delay*3)

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        bar.wait()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        bar.wait()
                        ts = time()
                        self.assertTrue(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time()-ts, delay)
                        self.assertGreaterEqual(timeout, time()-ts)
                        self.assertTrue(lock.acquired)

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()

    def test_thread_no_blocking_fail(self):
        key = uuid1().hex
        delay = 1

        for engine in ENGINES:

            bar = Barrier(2, timeout=delay*3)

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        bar.wait()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        bar.wait()
                        self.assertFalse(lock.acquire(False))

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()