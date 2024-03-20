from threading import Barrier, Thread
from time import sleep
from unittest import TestCase
from uuid import uuid4

from sqlalchemy_dlock import create_sadlock

from .engines import ENGINES


class PgTestCase(TestCase):
    def tearDown(self):
        for engine in ENGINES:
            engine.dispose()

    def test_pg_invalid_interval(self):
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue
            key = uuid4().hex
            with engine.connect() as conn:
                lck = create_sadlock(conn, key)
                with self.assertRaises(ValueError):
                    lck.acquire(timeout=0, interval=-1)

    def test_simple_xact(self):
        key = uuid4().hex
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue
            with engine.connect() as conn:
                lck = create_sadlock(conn, key, xact=True)
                with conn.begin():
                    self.assertTrue(lck.acquire())

    def test_xact_thread(self):
        key = uuid4().hex
        for engine in ENGINES:
            if engine.name != "postgresql":
                continue

            trd_exc = None
            bar = Barrier(2)

            def fn_():
                nonlocal trd_exc
                try:
                    with engine.connect() as c_:
                        l_ = create_sadlock(c_, key, xact=True)
                        bar.wait(10)
                        with c_.begin():
                            self.assertFalse(l_.acquire(block=False))
                            sleep(3)
                            self.assertTrue(l_.acquire(block=False))
                except Exception as exc:
                    trd_exc = exc
                    raise exc

            trd = Thread(target=fn_)
            trd.start()

            with engine.connect() as conn:
                lck = create_sadlock(conn, key, xact=True)
                with conn.begin():
                    self.assertTrue(lck.acquire(block=False))
                    bar.wait(5)
                    sleep(3)

            trd.join()

            if trd_exc is not None:
                raise trd_exc  # type: ignore
