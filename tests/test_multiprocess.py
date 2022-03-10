import sys
from contextlib import closing
from multiprocessing import Barrier, Process
from time import sleep, time
from unittest import TestCase
from uuid import uuid4
from warnings import warn

from sqlalchemy_dlock import create_sadlock

from .engines import ENGINES

if not sys.platform.startswith('linux'):
    warn(
        'The test module will not run on {}, because it need sub-process fork feature'
        .format(sys.platform)
    )

    class DummyMultiProcessTestCase(TestCase):
        pass

else:

    class MultiProcessTestCase(TestCase):

        def test_non_blocking_success(self):
            key = uuid4().hex
            for i in range(len(ENGINES)):
                bar = Barrier(2)

                def fn1(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with create_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)
                        b.wait()

                def fn2(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with closing(create_sadlock(conn, key)) as lock:
                            b.wait()
                            self.assertTrue(lock.acquire(False))

                p1 = Process(target=fn1, args=(i, bar))
                p2 = Process(target=fn2, args=(i, bar))

                p1.start()
                p2.start()

                p1.join()
                p2.join()

                self.assertEqual(p1.exitcode, 0)
                self.assertEqual(p2.exitcode, 0)

        def test_non_blocking_fail(self):
            key = uuid4().hex
            delay = 1
            for i in range(len(ENGINES)):
                bar = Barrier(2)

                def fn1(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with create_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                            b.wait()
                            sleep(delay)
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

                def fn2(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with closing(create_sadlock(conn, key)) as lock:
                            b.wait()
                            self.assertFalse(lock.acquire(False))

                p1 = Process(target=fn1, args=(i, bar))
                p2 = Process(target=fn2, args=(i, bar))

                p1.start()
                p2.start()

                p1.join()
                p2.join()

                self.assertEqual(p1.exitcode, 0)
                self.assertEqual(p2.exitcode, 0)

        def test_timeout_success(self):
            key = uuid4().hex
            delay = 1
            timeout = 3

            for i in range(len(ENGINES)):
                bar = Barrier(2)

                def fn1(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with create_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                            b.wait()
                            sleep(delay)
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

                def fn2(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with closing(create_sadlock(conn, key)) as lock:
                            b.wait()
                            ts = time()
                            self.assertTrue(lock.acquire(timeout=timeout))
                            self.assertGreaterEqual(time() - ts, delay)
                            self.assertGreaterEqual(timeout, time() - ts)
                            self.assertTrue(lock.acquired)

                p1 = Process(target=fn1, args=(i, bar))
                p2 = Process(target=fn2, args=(i, bar))

                p1.start()
                p2.start()

                p1.join()
                p2.join()

                self.assertEqual(p1.exitcode, 0)
                self.assertEqual(p2.exitcode, 0)

        def test_timeout_fail(self):
            key = uuid4().hex
            delay = 3
            timeout = 1
            for i in range(len(ENGINES)):
                bar = Barrier(2)

                def fn1(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with create_sadlock(conn, key) as lock:
                            self.assertTrue(lock.acquired)
                            b.wait()
                            sleep(delay)
                            self.assertTrue(lock.acquired)
                        self.assertFalse(lock.acquired)

                def fn2(engine_index, b):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with closing(create_sadlock(conn, key)) as lock:
                            b.wait()
                            ts = time()
                            self.assertFalse(lock.acquire(timeout=timeout))
                            self.assertGreaterEqual(time() - ts, timeout)
                            self.assertFalse(lock.acquired)

                p1 = Process(target=fn1, args=(i, bar))
                p2 = Process(target=fn2, args=(i, bar))

                p1.start()
                p2.start()

                p1.join()
                p2.join()

                self.assertEqual(p1.exitcode, 0)
                self.assertEqual(p2.exitcode, 0)

        def test_release_omitted(self):
            key = uuid4().hex

            for i in range(len(ENGINES)):
                def fn1(engine_index):
                    engine = ENGINES[engine_index]
                    lock = create_sadlock(engine.connect(), key)
                    self.assertTrue(lock.acquire(False))

                def fn2(engine_index):
                    engine = ENGINES[engine_index]
                    with engine.connect() as conn:
                        with closing(create_sadlock(conn, key)) as lock:
                            self.assertTrue(lock.acquire(False))

                p1 = Process(target=fn1, args=(i,))
                p2 = Process(target=fn2, args=(i,))

                p1.start()
                p1.join()

                p2.start()
                p2.join()

                self.assertEqual(p1.exitcode, 0)
                self.assertEqual(p2.exitcode, 0)
