
from threading import local

from sqlalchemy.engine import Connection


class AbstractSessionLevelLock(local):
    """Base class of a distributed lock implementation based on SQLAlchemy

    Database's session usually act as connection in SQLAlchemy

    It's Thread-Local!
    """

    def __init__(self,
                 connection: Connection,
                 key,
                 *args, **kwargs
                 ):
        self._acquired = False
        self._connection = connection
        self._key = key

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def key(self):
        return self._key

    @property
    def connection(self) -> Connection:
        return self._connection

    @property
    def acquired(self) -> bool:
        return self._acquired

    def acquire(self, blocking: bool = True, timeout: int = -1, *args, **kwargs) -> bool:
        """
        Acquire a lock, blocking or non-blocking.

        - When invoked with the blocking argument set to True (the default), 
          block until the lock is unlocked, then set it to locked and return True.

        - When invoked with the blocking argument set to False, do not block.
          If a call with blocking set to True would block, return False immediately; otherwise, set the lock to locked and return True.

        - When invoked with the floating-point timeout argument set to a positive value,
          block for at most the number of seconds specified by timeout and as long as the lock cannot be acquired.
          A negative timeout argument specifies an unbounded wait.
          It has no effect to specify a timeout when blocking is false.

        The return value is True if the lock is acquired successfully, False if not (for example if the timeout expired).
        """
        raise NotImplementedError()

    def release(self, *args, **kwargs):
        raise NotImplementedError()

    def close(self, *args, **kwargs):
        """Same as :method:`release`, but won't raise a :class:`RuntimeError` when the object is not acquired yet.
        """
        if self._acquired:
            self.release()
