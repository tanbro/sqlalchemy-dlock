from os import environ, getenv

from dotenv import load_dotenv

__all__ = ['create_engines', 'dispose_engines', 'get_engines']


_ENGINES = []


def create_engines():
    global _ENGINES

    load_dotenv()

    if getenv('NO_ASYNCIO'):
        return []

    from sqlalchemy.ext.asyncio import create_async_engine

    urls = getenv('TEST_ASYNC_URLS',
                  'mysql+aiomysql://test:test@localhost/test postgresql+asyncpg://postgres:test@localhost/').split()

    for url in urls:
        engine = create_async_engine(url)
        _ENGINES.append(engine)

    return _ENGINES


async def dispose_engines():
    for engine in _ENGINES:
        await engine.dispose()


def get_engines():
    return _ENGINES
