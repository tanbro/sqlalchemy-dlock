import sys
from typing import Union

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:  # pragma: no cover
    from typing import TypeAlias

from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, scoped_session

__all__ = ["TConnectionOrSession"]

TConnectionOrSession: TypeAlias = Union[Connection, Session, scoped_session]
