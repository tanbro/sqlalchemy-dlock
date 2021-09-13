from typing import Union

from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, scoped_session

TConnectionOrSession = Union[Connection, Session, scoped_session]
