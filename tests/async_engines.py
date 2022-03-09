from os import environ

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

__all__ = ['create_engins', 'dispose_engins', 'get_engins']


_ENGINES = []


def create_engins():
    global _ENGINES

    load_dotenv()

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
