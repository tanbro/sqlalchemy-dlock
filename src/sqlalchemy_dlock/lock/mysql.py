import sys
from typing import Any, Callable, Optional, Union

from ..exceptions import SqlAlchemyDLockDatabaseError
from ..statement.mysql import LOCK, UNLOCK
from .base import BaseSadLock

if sys.version_info < (3, 12):  # pragma: no cover
    from .._sa_types_backward import TConnectionOrSession
else:  # pragma: no cover
    from .._sa_types import TConnectionOrSession

MYSQL_LOCK_NAME_MAX_LENGTH = 64


def default_convert(key: Union[bytearray, bytes, int, float]) -> str:
    if isinstance(key, (bytearray, bytes)):
        result = key.decode()
    elif isinstance(key, (int, float)):
        result = str(key)
    else:
        raise TypeError(f"{type(key)}")
    return result


class MysqlSadLockMixin:
    """A Mix-in class for MySQL named lock"""

    def __init__(self, *, key, convert: Optional[Callable[[Any], str]] = None, **kwargs):
        """
        Args:
            key: MySQL named lock requires the key given by string.

                If ``key`` is not a :class:`str`:

                - When :class:`bytes` or alike, the constructor tries to decode it with default encoding::

                    key = key.decode()

                - Otherwise the constructor force convert it to :class:`str`::

                    key = str(key)

                - Or you can specify a ``convert`` function to that argument

            convert: Custom function to covert ``key`` to required data type.

                Example:
                    ::

                        def convert(value) -> str:
                            # get a string key by `value`
                            return the_string_covert_from_value
        """  # noqa: E501
        if convert:
            key = convert(key)
        elif not isinstance(key, str):
            key = default_convert(key)
        if not isinstance(key, str):
            raise TypeError("MySQL named lock requires the key given by string")
        if len(key) > MYSQL_LOCK_NAME_MAX_LENGTH:
            raise ValueError(f"MySQL enforces a maximum length on lock names of {MYSQL_LOCK_NAME_MAX_LENGTH} characters.")
        self._actual_key = key


class MysqlSadLock(BaseSadLock, MysqlSadLockMixin):
    """A distributed lock implemented by MySQL named-lock

    See Also:
        https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html

    Caution:
        To MySQL locking function, it is even possible for a given session to acquire multiple locks for the same name.
        Other sessions cannot acquire a lock with that name until the acquiring session releases all its locks for the name.
        When perform multiple :meth:`.acquire` for a key on the **same** SQLAlchemy connection, latter :meth:`.acquire` will success immediately no wait and never block, it causes cascade lock instead!
    """  # noqa: E501

    def __init__(self, connection_or_session: TConnectionOrSession, key, **kwargs):
        """
        Args:
            connection_or_session: see :attr:`.BaseSadLock.connection_or_session`
            key: see :attr:`.BaseSadLock.key`
            **kwargs: other named parameters pass to :class:`.BaseSadLock` and :class:`.MysqlSadLockMixin`
        """
        MysqlSadLockMixin.__init__(self, key=key, **kwargs)
        BaseSadLock.__init__(self, connection_or_session, self._actual_key, **kwargs)

    def acquire(self, block: bool = True, timeout: Union[float, int, None] = None) -> bool:
        if self._acquired:
            raise ValueError("invoked on a locked lock")
        if block:
            # None: set the timeout period to infinite.
            if timeout is None:
                timeout = -1
            # negative value for `timeout` are equivalent to a `timeout` of zero
            elif timeout < 0:
                timeout = 0
        else:
            timeout = 0
        stmt = LOCK.params(str=self.key, timeout=timeout)
        ret_val = self.connection_or_session.execute(stmt).scalar_one()
        if ret_val == 1:
            self._acquired = True
        elif ret_val == 0:
            pass  # 直到超时也没有成功锁定
        elif ret_val is None:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"An error occurred while attempting to obtain the lock {self.key!r}")
        else:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"GET_LOCK({self.key!r}, {timeout}) returns {ret_val}")
        return self._acquired

    def release(self):
        if not self._acquired:
            raise ValueError("invoked on an unlocked lock")
        stmt = UNLOCK.params(str=self.key)
        ret_val = self.connection_or_session.execute(stmt).scalar_one()
        if ret_val == 1:
            self._acquired = False
        elif ret_val == 0:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                f"The named lock {self.key!r} was not established by this thread, and the lock is not released."
            )
        elif ret_val is None:  # pragma: no cover
            self._acquired = False
            raise SqlAlchemyDLockDatabaseError(
                f"The named lock {self.key!r} did not exist, "
                "was never obtained by a call to GET_LOCK(), "
                "or has previously been released."
            )
        else:  # pragma: no cover
            raise SqlAlchemyDLockDatabaseError(f"RELEASE_LOCK({self.key!r}) returns {ret_val}")
