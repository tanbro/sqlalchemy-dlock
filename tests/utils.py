from contextlib import contextmanager


@contextmanager
def session_scope(Session):  # noqa
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
    except:  # noqa
        session.rollback()
        raise
    finally:
        session.close()
