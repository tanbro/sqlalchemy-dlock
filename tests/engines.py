from os import environ

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

__all__ = ['ENGINES']

ENGINES = [
    create_engine(environ[k], echo=True)
    for k in [
        'SQLALCHEMY_DLOCK_MYSQL',
        'SQLALCHEMY_DLOCK_POSTGRESQL',
    ]
]
