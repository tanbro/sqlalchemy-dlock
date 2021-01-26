from threading import local
from typing import Optional, Union

from sqlalchemy.engine import Connection  # noqa


class AbstractSessionLevelLock(local):
    """Base class of database session level lock implementation

    .. note::

        - It's Thread-Local (:class:`threading.local`)
        - It's an abstract class, do not manual instantiate

    .. attention::

        The *session* here means that of Database,
        **NOT** SQLAlchemy's :class:`sqlalchemy.orm.session.Session`,
        which is more like a transaction.
        Here we roughly take :class:`sqlalchemy.engine.Connection` as database's session.

    The lock's :meth:`acquire` and :meth:`release` methods can be used as context managers for a with statement.
    The :meth:`acquire` method will be called when the block is entered,
    and :meth:`release` will be called when the block is exited.
    Hence, the following snippet::

        with some_lock:
            # do something...

    is equivalent to::

        some_lock.acquire()
        try:
            # do something...
        finally:
            some_lock.release()
    """

    def __init__(self,
                 connection: Connection,
                 key,
                 **kwargs  # noqa
                 ):
        """
        Parameters
        ----------
        connection : sqlalchemy.engine.Connection
            SQL locking functions will be invoked on it
        key
            ID or name used as SQL locking function's key
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
        return '<{} {} key={} at 0x{:x}>'.format(
            'locked' if self._acquired else 'unlocked',
            self.__class__.__name__,
            self._key, id(self)
        )

    @property
    def connection(self) -> Connection:
        """Returns `connection` parameter of the constructor
        """
        return self._connection

    @property
    def key(self):
        """Returns `key` parameter of the constructor
        """
        return self._key

    @property
    def acquired(self) -> bool:
        return self._acquired

    def acquire(self,
                blocking: Optional[bool] = None,
                timeout: Union[float, int, None] = None,
                **kwargs  # noqa
                ) -> bool:
        """
        Acquire a lock, blocking or non-blocking.

        - When invoked with the `blocking` argument set to ``True`` (the default),
          block until the lock is unlocked, then set it to locked and return ``True``.

        - When invoked with the `blocking` argument set to ``False``, do not block.
          If a call with blocking set to ``True`` would block, return ``False`` immediately;
          otherwise, set the lock to locked and return ``True``.

        - When invoked with the floating-point `timeout` argument set to ``None`` or a positive value,
          block for at most the number of seconds specified by `timeout` and as long as the lock cannot be acquired.
          A negative or ``None`` `timeout` argument specifies an unbounded wait.
          It has no effect to specify a `timeout` when `blocking` is ``False``.

        The return value is ``True`` if the lock is acquired successfully,
        ``False`` if not (for example if the timeout expired).
        """
        raise NotImplementedError()

    def release(self, **kwargs):
        """Release a lock. This can be called from any thread, not only the thread which has acquired the lock.

        When the lock is locked, reset it to unlocked, and return.
        If any other threads are blocked waiting for the lock to become unlocked, allow exactly one of them to proceed.

        When invoked on an unlocked lock, a :class:`RuntimeError` is raised.

        There is no return value.
        """
        raise NotImplementedError()

    def close(self, **kwargs):
        """Same as :meth:`release`

        Except that a :class:`RuntimeError` is **NOT** raised when invoked on an unlocked lock.

        This method is equivalent to::

            if not lock.acquired:
                lock.release()

        The method maybe useful together with :func:`contextlib.closing`,
        when we need with statement, but don't want it acquire at the begin of the block.

        eg::

            # ...

            from contextlib import closing
            from sqlalchemy_dlock import make_sa_dlock

            # ...

            with engine.connect() as conn:
                with closing(make_sa_dlock(conn, k)) as lock:
                    # not acquired at the begin of with block
                    assert not lock.acquired
                    # ...
                    # lock when need
                    lock.acquire()
                    assert lock.acquired
                    # ...
                  # auto invoke `close()` at the end with block
                assert not lock.acquired
        """
        if self._acquired:
            self.release(**kwargs)
