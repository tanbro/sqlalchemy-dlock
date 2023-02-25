from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine

__all__ = ['ENGINES']

load_dotenv()

URLS = getenv(
    'TEST_URLS',
    'mysql://test:test@localhost/test postgresql://postgres:test@localhost/'
).split()

ENGINES = [
    create_engine(url)
    for url in URLS
]
