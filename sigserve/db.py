from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from sigserve.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url)


def open_session() -> Session:
    return Session(get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with open_session() as session:
        yield session
