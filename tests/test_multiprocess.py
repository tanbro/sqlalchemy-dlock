from contextlib import closing
from time import sleep, time
from unittest import TestCase
from uuid import uuid1
from multiprocessing import Barrier, Process

from sqlalchemy_dlock import make_session_level_lock

from .engines import ENGINES


class MutliProcessTestCase(TestCase):

    def test_non_blocking(self):
        key = uuid1().hex
        delay = 1
        for i in range(len(ENGINES)):
            bar = Barrier(2, timeout=delay*3)

            def fn1(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        b.wait()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        b.wait()
                        self.assertFalse(lock.acquire(False))

            p1 = Process(target=fn1, args=(i, bar))
            p2 = Process(target=fn2, args=(i, bar))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

    def test_timeout_fail(self):
        key = uuid1().hex
        delay = 3
        timeout = 1
        for i in range(len(ENGINES)):
            bar = Barrier(2, timeout=delay*3)

            def fn1(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        b.wait()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        b.wait()
                        ts = time()
                        self.assertFalse(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time()-ts, timeout)
                        self.assertFalse(lock.acquired)

            p1 = Process(target=fn1, args=(i, bar))
            p2 = Process(target=fn2, args=(i, bar))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

    def test_timeout_success(self):
        key = uuid1().hex
        delay = 1
        timeout = 3

        for i in range(len(ENGINES)):

            bar = Barrier(2, timeout=delay*3)

            def fn1(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        b.wait()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        b.wait()
                        ts = time()
                        self.assertTrue(lock.acquire(timeout=timeout))
                        self.assertGreaterEqual(time()-ts, delay)
                        self.assertGreaterEqual(timeout, time()-ts)
                        self.assertTrue(lock.acquired)

            p1 = Process(target=fn1, args=(i, bar))
            p2 = Process(target=fn2, args=(i, bar))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

    def test_Process_no_blocking_fail(self):
        key = uuid1().hex
        delay = 1

        for i in range(len(ENGINES)):

            bar = Barrier(2, timeout=delay*3)

            def fn1(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        b.wait()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2(engine_index, b):
                engine = ENGINES[engine_index]
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        b.wait()
                        self.assertFalse(lock.acquire(False))

            p1 = Process(target=fn1, args=(i, bar))
            p2 = Process(target=fn2, args=(i, bar))

            p1.start()
            p2.start()

            p1.join()
            p2.join()
