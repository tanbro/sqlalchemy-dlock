from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine

__all__ = ["ENGINES"]

load_dotenv()

URLS = (getenv("TEST_URLS") or "mysql://test:test@127.0.0.1/test postgresql://postgres:test@127.0.0.1/").split()

ENGINES = [create_engine(url) for url in URLS]
