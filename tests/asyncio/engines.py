from os import getenv
from typing import List

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine

__all__ = ["create_engines", "dispose_engines", "get_engines"]


_ENGINES: List[AsyncEngine] = []


def create_engines():
    global _ENGINES

    load_dotenv()

    from sqlalchemy.ext.asyncio import create_async_engine

    urls = (
        getenv("TEST_ASYNC_URLS") or "mysql+aiomysql://test:test@127.0.0.1/test postgresql+asyncpg://postgres:test@127.0.0.1/"
    ).split()

    for url in urls:
        engine = create_async_engine(url)
        _ENGINES.append(engine)

    return _ENGINES


async def dispose_engines():
    for engine in _ENGINES:
        await engine.dispose()


def get_engines():
    return _ENGINES
