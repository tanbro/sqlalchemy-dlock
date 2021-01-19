from contextlib import ExitStack, closing
from os import cpu_count
from threading import Event, Thread
from time import sleep, time
from unittest import TestCase
from uuid import uuid1

from sqlalchemy_dlock import make_session_level_lock

from .engines import ENGINES


class BasicTestCase(TestCase):

    def test_enter_exit(self):
        key = uuid1().hex
        for engine in ENGINES:
            conn = engine.connect()
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

    def test_closing(self):
        key = uuid1().hex
        for engine in ENGINES:
            with closing(make_session_level_lock(engine.connect(), key)) as lock:
                self.assertFalse(lock.acquired)
                lock.acquire()
                self.assertTrue(lock.acquired)
            self.assertFalse(lock.acquired)

    def test_enter_exit_may_times(self):
        key = uuid1().hex
        for engine in ENGINES:
            for _ in range(cpu_count()+1):
                with make_session_level_lock(engine.connect(), key) as lock:
                    self.assertTrue(lock.acquired)
                self.assertFalse(lock.acquired)

    def test_no_blocking(self):
        key = uuid1().hex
        for engine in ENGINES:
            with closing(make_session_level_lock(engine.connect(), key)) as lock:
                self.assertFalse(lock.acquired)
                acquired = lock.acquire(False)
                self.assertTrue(acquired)
                self.assertTrue(lock.acquired)
            self.assertFalse(lock.acquired)

    def test_enter_close_enter(self):
        key = uuid1().hex
        for engine in ENGINES:
            for _ in range(cpu_count()+1):
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

    def test_dual_connection_timeout(self):
        key = uuid1().hex
        for engine in ENGINES:
            conn0 = engine.connect()
            lock0 = make_session_level_lock(conn0, key)
            self.assertTrue(lock0.acquire())
            conn1 = engine.connect()
            lock1 = make_session_level_lock(conn1, key)
            self.assertFalse(lock1.acquire(timeout=0))
            lock0.release()
            self.assertFalse(lock0.acquired)
            self.assertTrue(lock1.acquire())
            lock1.release()
            self.assertFalse(lock1.acquired)

    def test_dual_connection_release_omitted(self):
        key = uuid1().hex
        for engine in ENGINES:
            with engine.connect() as conn:
                lock = make_session_level_lock(conn, key)
                self.assertTrue(lock.acquire())
            with engine.connect() as conn:
                lock2 = make_session_level_lock(conn, key)
                self.assertTrue(lock2.acquire())

    def test_dual_connection_close(self):
        key = uuid1().hex
        for engine in ENGINES:
            conn0 = engine.connect()
            lock0 = make_session_level_lock(conn0, key)
            self.assertTrue(lock0.acquire())
            conn0.close()
            conn1 = engine.connect()
            lock1 = make_session_level_lock(conn1, key)
            self.assertTrue(lock1.acquire(timeout=0))

    def test_thread_timeout_failure(self):
        key = uuid1().hex
        delay = 3
        timeout = 1
        for engine in ENGINES:
            evt_start = Event()
            evt_start.clear()
            evt_start.clear()

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        evt_start.set()
                        self.assertTrue(lock.acquired)
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        evt_start.wait(delay*2)
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

    def test_thread_timeout_success(self):
        key = uuid1().hex
        delay = 1
        timeout = 3

        for engine in ENGINES:

            evt_start = Event()
            evt_start.clear()

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        evt_start.set()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        evt_start.wait(delay*2)
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

            evt_start = Event()
            evt_start.clear()

            def fn1():
                with engine.connect() as conn:
                    with make_session_level_lock(conn, key) as lock:
                        self.assertTrue(lock.acquired)
                        evt_start.set()
                        sleep(delay)
                        self.assertTrue(lock.acquired)
                    self.assertFalse(lock.acquired)

            def fn2():
                with engine.connect() as conn:
                    with closing(make_session_level_lock(conn, key)) as lock:
                        evt_start.wait(delay*2)
                        self.assertFalse(lock.acquire(False))

            trd1 = Thread(target=fn1)
            trd2 = Thread(target=fn2)

            trd1.start()
            trd2.start()

            trd1.join()
            trd2.join()
