from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import Settings, load_settings


def make_engine(settings: Settings | None = None, *, connect_timeout: int | None = None) -> Engine:
    settings = settings or load_settings()
    options = {"connect_timeout": connect_timeout} if connect_timeout is not None else {}
    return create_engine(settings.database_url, future=True, pool_pre_ping=True, connect_args=options)


@contextmanager
def db_engine(settings: Settings | None = None) -> Iterator[Engine]:
    engine = make_engine(settings)
    try:
        yield engine
    finally:
        engine.dispose()
