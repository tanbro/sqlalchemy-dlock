from os import getenv

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

__all__ = ["create_engines", "dispose_engines", "get_engines"]


_ENGINES: list[AsyncEngine] = []


def create_engines():
    load_dotenv()

    urls = (
        getenv("TEST_ASYNC_URLS") or "mysql+aiomysql://test:test@127.0.0.1/test postgresql+asyncpg://postgres:test@127.0.0.1/"
    ).split()

    for url in urls:
        engine = create_async_engine(url)
        _ENGINES.append(engine)

    return _ENGINES


async def dispose_engines():
    engines = tuple(_ENGINES)
    _ENGINES.clear()
    for engine in engines:
        await engine.dispose()


def get_engines():
    return _ENGINES
