from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, scoped_session

__all__ = ["TConnectionOrSession"]

type TConnectionOrSession = Connection | Session | scoped_session  # type: ignore[valid-type]
