from pathlib import Path
import json

from sqlalchemy import engine_from_config

__all__ = ['ENGINES']

with Path(__file__).parent.joinpath('engines.conf.json').open() as fp:
    data = json.load(fp)

ENGINES = [
    engine_from_config(cfg['configuration'], connect_args=cfg.get('args', {}))
    for cfg in data
]
