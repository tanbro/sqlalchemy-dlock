from threading import local
from typing import Union

from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, scoped_session

TConnectionOrSession = Union[Connection, Session, scoped_session]


class BaseSadLock(local):
    """Base class of database lock implementation

    .. note::

        - It's Thread-Local (:class:`threading.local`)
        - It's an abstract class, do not manual instantiate

    The :meth:`acquire` and :meth:`release` methods can be used as context managers for a :keyword:`with` statement.
    :meth:`acquire` will be called when the block is entered, and :meth:`release` will be called when the block is exited.
    Hence, the following snippet::

        with some_lock:
            # do something...
            pass

    is equivalent to::

        some_lock.acquire()
        try:
            # do something...
            pass
        finally:
            some_lock.release()
    """

    def __init__(self,
                 connection_or_session: TConnectionOrSession,
                 key,
                 *args, **kwargs
                 ):
        """
        Parameters
        ----------
        connection_or_session : sqlalchemy Connection or orm Session/ScopedSession object
            SQL locking functions will be invoked on it

        key
            ID or name of the SQL locking function
        """
        self._acquired = False
        self._connection_or_session = connection_or_session
        self._key = key

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __str__(self):  # pragma: no cover
        return '<{} {} key={} at 0x{:x}>'.format(
            'locked' if self._acquired else 'unlocked',
            self.__class__.__name__,
            self._key, id(self)
        )

    @property
    def connection_or_session(self) -> TConnectionOrSession:
        """Returns `connection_or_session` parameter of the constructor
        """
        return self._connection_or_session

    @property
    def key(self):
        """Returns `key` parameter of the constructor
        """
        return self._key

    @property
    def acquired(self) -> bool:
        """locked/unlocked state property

        As a `Getter`:

        - It returns ``True`` if the lock has been acquired, ``False`` otherwise.

        As a `Setter`:

        - Set to ``True`` is equivalent to call :meth:`acquire`
        - Set to ``False`` is equivalent to call :meth:`release`
        """
        return self._acquired

    @acquired.setter
    def acquired(self, value: bool):
        if value:
            self.acquire()
        else:
            self.release()

    @property
    def locked(self) -> bool:
        """Alias of :data:`acquired`
        """
        return self.acquired

    @locked.setter
    def locked(self, value: bool):
        self.acquired = value

    def acquire(self,
                block: bool = True,
                timeout: Union[float, int, None] = None,
                *args,
                **kwargs
                ) -> bool:
        """
        Acquire a lock, blocking or non-blocking.

        - With the `block` argument set to ``True`` (the default),
          the method call will block until the lock is in an unlocked state,
          then set it to locked and return ``True``.

        - With the `block` argument set to ``False``,
          the method call does not block.
          If the lock is currently in a locked state, return ``False``;
          otherwise set the lock to a locked state and return ``True``.

        - When invoked with a positive, floating-point value for `timeout`,
          block for at most the number of seconds specified by timeout as long as the lock can not be acquired.
          Invocations with a negative value for `timeout` are equivalent to a `timeout` of zero.
          Invocations with a `timeout` value of ``None`` (the default) set the timeout period to infinite.
          The `timeout` argument has no practical implications
          if the `block` argument is set to ``False`` and is thus ignored.
          Returns ``True`` if the lock has been acquired or ``False`` if the timeout period has elapsed.
        """
        raise NotImplementedError()

    def release(self, *args, **kwargs):
        """Release a lock.

        Since the class is thread-local, this cannot be called from other thread or process,
        and also can not be called from other connection.
        (Although PostgreSQL's shared advisory lock supports so).

        When the lock is locked, reset it to unlocked, and return.
        If any other threads are blocked waiting for the lock to become unlocked, allow exactly one of them to proceed.

        When invoked on an unlocked lock, a :class:`ValueError` is raised.

        There is no return value.
        """
        raise NotImplementedError()

    def close(self, *args, **kwargs):
        """Same as :meth:`release`

        Except that the :class:`ValueError` is **NOT** raised when invoked on an unlocked lock.

        An invocation of this method is equivalent to::

            if not some_lock.acquired:
                some_lock.release()

        This method maybe useful together with :func:`contextlib.closing`,
        when we need a :keyword:`with` statement, but don't want it to acquire at the beginning of the block.

        eg::

            # ...

            from contextlib import closing
            from sqlalchemy_dlock import create_sadlock

            # ...

            with closing(create_sadlock(some_connection, some_key)) as lock:
                # will not acquire at the begin of with-block
                assert not lock.acquired
                # ...
                # lock when need
                lock.acquire()
                assert lock.acquired
                # ...
            # `close` will be called at the end with-block
            assert not lock.acquired
        """
        if self._acquired:
            self.release(*args, **kwargs)
