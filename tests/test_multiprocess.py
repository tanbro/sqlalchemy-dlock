from contextlib import closing
from multiprocessing import Barrier, Process
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy_dlock import create_sadlock

from .engines import URLS


class MpNonBlockingSuccessTestCase(TestCase):

    @staticmethod
    def fn1(url, k, b):
        engine = create_engine(url)
        with engine.connect() as conn:
            with create_sadlock(conn, k) as lock:
                assert lock.acquired
            assert not lock.acquired
            b.wait()

    @staticmethod
    def fn2(url, k, b):
        engine = create_engine(url)
        with engine.connect() as conn:
            with closing(create_sadlock(conn, k)) as lock:
                b.wait()
                assert lock.acquire(False)

    def test(self):
        key = uuid4().hex
        for url in URLS:
            bar = Barrier(2)

            p1 = Process(target=self.__class__.fn1, args=(url, key, bar))
            p2 = Process(target=self.__class__.fn2, args=(url, key, bar))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

            self.assertEqual(p1.exitcode, 0)
            self.assertEqual(p2.exitcode, 0)


class MpNonBlockingFailTestCase(TestCase):
    @staticmethod
    def fn1(url, k, b, delay):
        engine = create_engine(url)
        with engine.connect() as conn:
            with create_sadlock(conn, k) as lock:
                assert lock.acquired
                b.wait()
                sleep(delay)
                assert lock.acquired
            assert not lock.acquired

    @staticmethod
    def fn2(url, k, b):
        engine = create_engine(url)
        with engine.connect() as conn:
            with closing(create_sadlock(conn, k)) as lock:
                b.wait()
                assert not lock.acquire(False)

    def test(self):
        key = uuid4().hex
        delay = 1
        cls = self.__class__
        for url in URLS:
            bar = Barrier(2)

            p1 = Process(target=cls.fn1, args=(url, key, bar, delay))
            p2 = Process(target=cls.fn2, args=(url, key, bar))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

            self.assertEqual(p1.exitcode, 0)
            self.assertEqual(p2.exitcode, 0)


class MpTimeoutSuccessTestCase(TestCase):
    @staticmethod
    def fn1(url, k, b, delay):
        engine = create_engine(url)
        with engine.connect() as conn:
            with create_sadlock(conn, k) as lock:
                assert lock.acquired
                b.wait()
                sleep(delay)
                assert lock.acquired
            assert not lock.acquired

    @staticmethod
    def fn2(url, k, b, delay, timeout):
        engine = create_engine(url)
        with engine.connect() as conn:
            with closing(create_sadlock(conn, k)) as lock:
                b.wait()
                ts = time()
                assert lock.acquire(timeout=timeout)
                assert time() - ts >= delay
                assert timeout >= time() - ts
                assert lock.acquired

    def test(self):
        key = uuid4().hex
        delay = 1
        timeout = 3
        cls = self.__class__

        for url in URLS:
            bar = Barrier(2)

            p1 = Process(target=cls.fn1, args=(url, key, bar, delay))
            p2 = Process(target=cls.fn2, args=(url, key, bar, delay, timeout))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

            self.assertEqual(p1.exitcode, 0)
            self.assertEqual(p2.exitcode, 0)


class MpTimtoutFailTestCase(TestCase):

    @staticmethod
    def fn1(url, k, b, delay):
        engine = create_engine(url)
        with engine.connect() as conn:
            with create_sadlock(conn, k) as lock:
                assert lock.acquired
                b.wait()
                sleep(delay)
                assert lock.acquired
            assert not lock.acquired

    @staticmethod
    def fn2(url, k, b, timeout):
        engine = create_engine(url)
        with engine.connect() as conn:
            with closing(create_sadlock(conn, k)) as lock:
                b.wait()
                ts = time()
                assert not lock.acquire(timeout=timeout)
                assert time() - ts >= timeout
                assert not lock.acquired

    def test(self):
        cls = self.__class__
        key = uuid4().hex
        delay = 3
        timeout = 1

        for url in URLS:
            bar = Barrier(2)

            p1 = Process(target=cls.fn1, args=(url, key, bar, delay))
            p2 = Process(target=cls.fn2, args=(url, key, bar, timeout))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

            self.assertEqual(p1.exitcode, 0)
            self.assertEqual(p2.exitcode, 0)


class MpReleaseOmitedTestCase(TestCase):

    @staticmethod
    def fn1(url, k):
        engine = create_engine(url)
        lock = create_sadlock(engine.connect(), k)
        assert lock.acquire(False)

    @staticmethod
    def fn2(url, k):
        engine = create_engine(url)
        with engine.connect() as conn:
            with closing(create_sadlock(conn, k)) as lock:
                assert lock.acquire(False)

    def test(self):
        cls = self.__class__
        key = uuid4().hex

        for url in URLS:

            p1 = Process(target=cls.fn1, args=(url, key))
            p2 = Process(target=cls.fn2, args=(url, key))

            p1.start()
            p1.join()

            p2.start()
            p2.join()

            self.assertEqual(p1.exitcode, 0)
            self.assertEqual(p2.exitcode, 0)
