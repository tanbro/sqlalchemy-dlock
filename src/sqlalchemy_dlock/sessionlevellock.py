from threading import local

from sqlalchemy.engine import Connection


class AbstractSessionLevelLock(local):
    """Base class of database session level lock implementation

    .. note::

        - It's Thread-Local (:class:`threading.local`)
        - Do not manual instantiate

    .. attention::

        The **session** here means session of Database, **NOT** SQLAlchemy's.

        :class:`sqlalchemy.orm.session.Session` is more like transaction.

        Database's sessions are usually managed as connections in SQLAlchemy
    """

    def __init__(self,
                 connection: Connection,
                 key,
                 *args, **kwargs
                 ):
        """
        Parameters
        ----------

        connection: sqlalchemy.engine.Connection
            Database Connection on which the SQL locking functions will be invoked.

        key
            Key/name or sth like that used as SQL locking function's ID
        """
        self._acquired = False
        self._connection = connection
        self._key = key

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __str__(self):
        name = '{} {} d-lock[{}]'.format(
            self.__class__.__name__, self._connection.engine.name, self._key)
        return '<{} {} at 0x{:x}>'.format(
            'locked' if self._acquired else 'unlocked', name, id(self))

    @property
    def connection(self) -> Connection:
        return self._connection

    @property
    def key(self):
        return self._key

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
        """Release a lock. This can be called from any thread, not only the thread which has acquired the lock.

        When the lock is locked, reset it to unlocked, and return. If any other threads are blocked waiting for the lock to become unlocked, allow exactly one of them to proceed.

        When invoked on an unlocked lock, a RuntimeError is raised.

        There is no return value.
        """
        raise NotImplementedError()

    def close(self, *args, **kwargs):
        """Same like :meth:`release`, but won't raise a :class:`RuntimeError` when the object is not acquired yet.
        """
        if self._acquired:
            self.release()
