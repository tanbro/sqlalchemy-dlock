import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine

__all__ = ['create_engins', 'dispose_engins', 'get_engins']


_ENGINES = []
_PREFIX = 'sqlalchemy.'


def create_engins():
    global _ENGINES

    with Path(__file__).parent.joinpath('async_engines.conf.json').open() as fp:
        data = json.load(fp)

    for cfg in data:
        url = cfg['configuration'][_PREFIX + 'url']
        kwds = {
            k[len(_PREFIX):]: v for k, v in cfg['configuration'].items()
            if k.startswith(_PREFIX) and k != _PREFIX + 'url'
        }
        connect_args = cfg.get('args', {})
        engine = create_async_engine(url, connect_args=connect_args, **kwds)
        _ENGINES.append(engine)

    return _ENGINES


async def dispose_engins():
    for engine in _ENGINES:
        await engine.dispose()


def get_engins():
    return _ENGINES
