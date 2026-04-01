import sys
from contextlib import AsyncExitStack
from multiprocessing import cpu_count
from random import randint
from secrets import token_bytes, token_hex
from unittest import IsolatedAsyncioTestCase, skipIf
from uuid import uuid4
import warnings

from sqlalchemy_dlock import create_async_sadlock

from .engines import create_engines, dispose_engines, get_engines

CPU_COUNT = cpu_count()


class BasicTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        create_engines()

    async def asyncTearDown(self):
        await dispose_engines()

    async def test_enter_exit(self):
        for engine in get_engines():
            key = uuid4().hex
            async with engine.connect() as conn:
                assert conn is not None
                lock = create_async_sadlock(conn, key)
                self.assertFalse(lock.locked)
                await lock.acquire()
                self.assertTrue(lock.locked)
                await lock.release()
                self.assertFalse(lock.locked)

    async def test_with_statement(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                assert conn is not None
                key = uuid4().hex
                async with create_async_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                self.assertFalse(lock.locked)

    async def test_timeout_in_with_statement(self):
        for engine in get_engines():
            async with AsyncExitStack() as stack:
                conn0, conn1 = [await stack.enter_async_context(engine.connect()) for _ in range(2)]
                key = uuid4().hex
                lock0 = create_async_sadlock(conn0, key)
                self.assertFalse(lock0.locked)
                r = await lock0.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock0.locked)
                with self.assertRaises(TimeoutError):
                    async with create_async_sadlock(conn1, key, contextual_timeout=1):
                        pass
                self.assertTrue(lock0.locked)
                await lock0.release()
                self.assertFalse(lock0.locked)

    async def test_many_str_key(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                assert conn is not None
                for _ in range(100):
                    key = uuid4().hex + uuid4().hex
                    async with create_async_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

    async def test_many_int_key(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                assert conn is not None
                for _ in range(100):
                    key = randint(-0x8000_0000_0000_0000, 0x7FFF_FFFF_FFFF_FFFF)
                    async with create_async_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

    async def test_many_bytes_key(self):
        for engine in get_engines():
            for _ in range(100):
                async with engine.connect() as conn:
                    if engine.name == "mysql":
                        key = token_hex().encode()
                    elif engine.name == "postgresql":
                        key = token_bytes()
                    elif engine.name == "mssql":
                        # MSSQL sp_getapplock uses string lock names
                        key = token_hex().encode()
                    elif engine.name == "oracle":
                        # Oracle DBMS_LOCK uses integer IDs, bytes are hashed
                        key = token_bytes()
                    else:
                        raise NotImplementedError()
                    async with create_async_sadlock(conn, key) as lock:
                        self.assertTrue(lock.locked)
                    self.assertFalse(lock.locked)

    async def test_invoke_locked_lock(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                assert conn is not None
                key = uuid4().hex
                async with create_async_sadlock(conn, key) as lock:
                    self.assertTrue(lock.locked)
                    with self.assertRaisesRegex(ValueError, "invoked on a locked lock"):
                        await lock.acquire()
                self.assertFalse(lock.locked)

    async def test_invoke_unlocked_lock(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                assert conn is not None
                key = uuid4().hex
                lock = create_async_sadlock(conn, key)
                self.assertFalse(lock.locked)
                with self.assertRaisesRegex(ValueError, "invoked on an unlocked lock"):
                    await lock.release()
                self.assertFalse(lock.locked)

    async def test_timeout_positive(self):
        for engine in get_engines():
            key = uuid4().hex
            for _ in range(CPU_COUNT + 1):
                async with engine.connect() as conn:
                    assert conn is not None
                    lock = create_async_sadlock(conn, key)
                    try:
                        self.assertFalse(lock.locked)
                        r = await lock.acquire(timeout=randint(1, 1024))
                        self.assertTrue(r)
                        self.assertTrue(lock.locked)
                    finally:
                        await lock.release()
                    self.assertFalse(lock.locked)

    async def test_timeout_zero(self):
        for engine in get_engines():
            async with engine.connect() as conn:
                assert conn is not None
                key = uuid4().hex
                lock = create_async_sadlock(conn, key)
                try:
                    self.assertFalse(lock.locked)
                    r = await lock.acquire(timeout=0)
                    self.assertTrue(r)
                    self.assertTrue(lock.locked)
                finally:
                    await lock.release()
                self.assertFalse(lock.locked)

    async def test_timeout_negative(self):
        for engine in get_engines():
            for _ in range(CPU_COUNT + 1):
                async with engine.connect() as conn:
                    assert conn is not None
                    key = uuid4().hex
                    lock = create_async_sadlock(conn, key)
                    try:
                        r = await lock.acquire(timeout=-1 * randint(1, 1024))
                        self.assertTrue(r)
                    finally:
                        await lock.release()
                    self.assertFalse(lock.locked)

    async def test_timeout_none(self):
        for engine in get_engines():
            for _ in range(CPU_COUNT + 1):
                async with engine.connect() as conn:
                    assert conn is not None
                    key = uuid4().hex
                    lock = create_async_sadlock(conn, key)
                    try:
                        r = await lock.acquire(timeout=None)
                        self.assertTrue(r)
                    finally:
                        await lock.release()
                    self.assertFalse(lock.locked)

    async def test_enter_locked(self):
        for engine in get_engines():
            key = uuid4().hex
            async with AsyncExitStack() as stack:
                conn0, conn1 = [await stack.enter_async_context(engine.connect()) for _ in range(2)]

                lock0 = create_async_sadlock(conn0, key)
                self.assertFalse(lock0.locked)
                r = await lock0.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock0.locked)

                lock1 = create_async_sadlock(conn1, key)
                self.assertFalse(lock1.locked)
                r = await lock1.acquire(block=False)
                self.assertFalse(r)
                self.assertFalse(lock1.locked)

                self.assertTrue(lock0.locked)
                await lock0.release()
                self.assertFalse(lock0.locked)

                r = await lock1.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock1.locked)
                await lock1.release()
                self.assertFalse(lock1.locked)

    async def test_release_unlocked_error(self):
        for engine in get_engines():
            key = uuid4().hex
            async with AsyncExitStack() as stack:
                conn0, conn1 = [await stack.enter_async_context(engine.connect()) for _ in range(2)]

                lock0 = create_async_sadlock(conn0, key)
                r = await lock0.acquire(False)
                self.assertTrue(r)
                self.assertTrue(lock0.locked)

                lock1 = create_async_sadlock(conn1, key)
                with self.assertRaisesRegex(ValueError, "invoked on an unlocked lock"):
                    await lock1.release()

    async def test_aclose(self):
        """Test aclose() method."""
        for engine in get_engines():
            async with engine.connect() as conn:
                key = uuid4().hex
                lock = create_async_sadlock(conn, key)
                self.assertFalse(lock.locked)
                await lock.acquire()
                self.assertTrue(lock.locked)
                await lock.aclose()
                self.assertFalse(lock.locked)

    async def test_aclose_when_unlocked(self):
        """Test aclose() when lock is not acquired (should be no-op)."""
        for engine in get_engines():
            async with engine.connect() as conn:
                key = uuid4().hex
                lock = create_async_sadlock(conn, key)
                self.assertFalse(lock.locked)
                # aclose on unlocked lock should be no-op
                await lock.aclose()
                self.assertFalse(lock.locked)

    @skipIf(sys.version_info < (3, 10), "contextlib.aclosing: New in version 3.10")
    async def test_aclosing_context_manager(self):
        """Test aclose() with contextlib.aclosing (Python 3.10+)."""
        try:
            from contextlib import aclosing
        except ImportError:
            self.skipTest("contextlib.aclosing not available")

        for engine in get_engines():
            async with engine.connect() as conn:
                key = uuid4().hex
                async with aclosing(create_async_sadlock(conn, key)) as lock:
                    # will NOT acquire at the begin of with-block
                    self.assertFalse(lock.locked)
                    # lock when need
                    await lock.acquire()
                    self.assertTrue(lock.locked)
                # aclose will be called at the end with-block
                self.assertFalse(lock.locked)

    async def test_close_deprecated(self):
        """Test that close() is deprecated and calls aclose()."""
        for engine in get_engines():
            async with engine.connect() as conn:
                key = uuid4().hex
                lock = create_async_sadlock(conn, key)
                await lock.acquire()
                self.assertTrue(lock.locked)
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    await lock.close()
                    # Check that deprecation warning was raised
                    self.assertEqual(len(w), 1)
                    self.assertEqual(w[0].category, DeprecationWarning)
                    self.assertIn("deprecated", str(w[0].message).lower())
                    self.assertIn("aclose", str(w[0].message).lower())
                self.assertFalse(lock.locked)
