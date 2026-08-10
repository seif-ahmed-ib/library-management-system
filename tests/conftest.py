from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache.redis_cache import redis_cache
from app.core.logging_config import clear_recent_logs
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import book, borrow_record, user  # noqa: F401
from app.monitoring.metrics import metrics


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    metrics.reset()
    clear_recent_logs()
    redis_cache.set_client(None)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    redis_cache.reset_client()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
