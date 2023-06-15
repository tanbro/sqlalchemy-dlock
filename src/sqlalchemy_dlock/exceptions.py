__all__ = ["SqlAlchemyDLockBaseException", "SqlAlchemyDLockDatabaseError"]


class SqlAlchemyDLockBaseException(Exception):
    pass


class SqlAlchemyDLockDatabaseError(SqlAlchemyDLockBaseException):
    pass
