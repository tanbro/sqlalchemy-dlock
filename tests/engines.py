from os import environ

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

__all__ = ['ENGINES']

ENGINES = [
    create_engine(v)
    for k, v in environ.items()
    if k.startswith('SQLALCHEMY_DLOCK_')
]
