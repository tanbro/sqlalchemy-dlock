from os import environ

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

__all__ = ['create_engins', 'dispose_engins', 'get_engins']


_ENGINES = []

def create_engins():
    global _ENGINES
    load_dotenv()
    _ENGINES = [
        create_async_engine(v)
        for k, v in environ.items()
        if k.startswith('SQLALCHEMY_DLOCK_ASYNCIO_')
    ]
    return _ENGINES

async def dispose_engins():
    for engine in _ENGINES:
        await engine.dispose()


def get_engins():
    return _ENGINES