from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlmodel import Session, create_engine

from app.core.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

