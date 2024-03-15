from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, scoped_session

type TConnectionOrSession = Connection | Session | scoped_session
