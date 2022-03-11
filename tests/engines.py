from os import environ

from dotenv import load_dotenv
from sqlalchemy import create_engine

__all__ = ['ENGINES']

load_dotenv()

URLS = environ['TEST_URLS'].split()

ENGINES = [
    create_engine(url)
    for url in URLS
]
