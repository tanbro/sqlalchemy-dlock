from sys import version_info

if version_info >= (3, 8):
    from contextlib import AsyncExitStack
    from multiprocessing import cpu_count
    from random import randint
    from secrets import token_bytes, token_hex
    from unittest import IsolatedAsyncioTestCase
    from uuid import uuid4

    from sqlalchemy_dlock.asyncio import create_async_sadlock

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

        async def test_pg_level_name(self):
            levels = "session", "shared", "xact"
            for engine in get_engines():
                if engine.name != "postgresql":
                    continue
                key = uuid4().hex
                async with engine.connect() as conn:
                    for level in levels:
                        lck = create_async_sadlock(conn, key, level=level)
                        self.assertEqual(lck.level, level)  # type: ignore
                    with self.assertRaises(ValueError):
                        create_async_sadlock(conn, key, level="invalid_level_name")

        async def test_pg_invalid_interval(self):
            for engine in get_engines():
                if engine.name != "postgresql":
                    continue
                key = uuid4().hex
                async with engine.connect() as conn:
                    lck = create_async_sadlock(conn, key)
                    with self.assertRaises(ValueError):
                        await lck.acquire(timeout=0, interval=-1)
