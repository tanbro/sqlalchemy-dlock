from os import environ, getenv

from dotenv import load_dotenv

__all__ = ['create_engines', 'dispose_engins', 'get_engins']


_ENGINES = []


def create_engines():
    global _ENGINES

    load_dotenv()

    if getenv('NO_ASYNCIO'):
        return []

    from sqlalchemy.ext.asyncio import create_async_engine

    urls = environ['TEST_ASYNC_URLS'].split()

    for url in urls:
        engine = create_async_engine(url)
        _ENGINES.append(engine)

    return _ENGINES


async def dispose_engins():
    for engine in _ENGINES:
        await engine.dispose()


def get_engins():
    return _ENGINES
