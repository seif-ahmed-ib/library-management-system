from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.cache.redis_cache import redis_cache
from tests.test_books import (
    BOOK_DATA,
    create_admin_headers,
    create_book,
    create_member_headers,
)


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.storage.get(key)

    def setex(
        self,
        key: str,
        ttl_seconds: int,
        value: str,
    ) -> bool:
        assert ttl_seconds > 0
        self.storage[key] = value
        return True

    def delete(self, *keys: str) -> int:
        deleted_count = 0

        for key in keys:
            if key in self.storage:
                del self.storage[key]
                deleted_count += 1

        return deleted_count

    def scan_iter(self, match: str):
        prefix = match.removesuffix("*")
        return iter(key for key in list(self.storage) if key.startswith(prefix))

    @staticmethod
    def ping() -> bool:
        return True


@pytest.fixture
def fake_redis() -> Generator[FakeRedis, None, None]:
    client = FakeRedis()
    redis_cache.set_client(client)

    yield client

    redis_cache.reset_client()


def test_get_book_uses_cache_aside(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    headers = create_admin_headers(client)
    book = create_book(client, headers).json()
    url = f"/api/v1/books/{book['id']}"

    first_response = client.get(url, headers=headers)
    second_response = client.get(url, headers=headers)

    assert first_response.status_code == 200
    assert first_response.headers["X-Cache"] == "MISS"
    assert second_response.headers["X-Cache"] == "HIT"
    assert second_response.json() == first_response.json()
    assert fake_redis.storage


def test_update_invalidates_item_and_list_cache(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    headers = create_admin_headers(client)
    book = create_book(client, headers).json()
    item_url = f"/api/v1/books/{book['id']}"

    assert client.get(item_url, headers=headers).headers["X-Cache"] == "MISS"
    assert client.get(item_url, headers=headers).headers["X-Cache"] == "HIT"
    assert client.get("/api/v1/books", headers=headers).headers["X-Cache"] == "MISS"

    update_response = client.put(
        item_url,
        headers=headers,
        json={"title": "Cache Invalidation Verified"},
    )
    refreshed_response = client.get(item_url, headers=headers)
    refreshed_list = client.get("/api/v1/books", headers=headers)

    assert update_response.status_code == 200
    assert refreshed_response.headers["X-Cache"] == "MISS"
    assert refreshed_response.json()["title"] == ("Cache Invalidation Verified")
    assert refreshed_list.headers["X-Cache"] == "MISS"


def test_create_invalidates_cached_book_list(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    headers = create_admin_headers(client)
    create_book(client, headers)

    assert client.get("/api/v1/books", headers=headers).headers["X-Cache"] == "MISS"
    assert client.get("/api/v1/books", headers=headers).headers["X-Cache"] == "HIT"

    second_book = {
        **BOOK_DATA,
        "title": "Second Book",
        "isbn": "9780135957059",
    }
    assert (
        create_book(
            client,
            headers,
            second_book,
        ).status_code
        == 201
    )

    response = client.get("/api/v1/books", headers=headers)

    assert response.headers["X-Cache"] == "MISS"
    assert len(response.json()) == 2


def test_borrow_invalidates_cached_availability(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    admin_headers = create_admin_headers(client)
    member_headers = create_member_headers(client)
    book = create_book(
        client,
        admin_headers,
        {**BOOK_DATA, "total_copies": 2},
    ).json()
    item_url = f"/api/v1/books/{book['id']}"

    client.get(item_url, headers=member_headers)
    assert client.get(item_url, headers=member_headers).headers["X-Cache"] == "HIT"

    borrow_response = client.post(
        "/api/v1/borrows",
        headers=member_headers,
        json={"book_id": book["id"]},
    )
    refreshed_book = client.get(item_url, headers=member_headers)

    assert borrow_response.status_code == 201
    assert refreshed_book.headers["X-Cache"] == "MISS"
    assert refreshed_book.json()["available_copies"] == 1


def test_monitoring_dashboard_reports_required_metrics(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/missing-route").status_code == 404

    data_response = client.get("/monitoring/data")
    dashboard_response = client.get("/monitoring")
    data = data_response.json()

    assert data_response.status_code == 200
    assert data["health"] == {
        "status": "healthy",
        "application": "healthy",
        "database": "healthy",
        "redis": "healthy",
    }
    assert data["requests"]["total"] >= 2
    assert data["requests"]["errors"] >= 1
    assert "average_response_ms" in data["requests"]
    assert "hit_rate_percent" in data["cache"]
    assert data["recent_errors"]

    assert dashboard_response.status_code == 200
    assert "Library API Monitoring" in dashboard_response.text


def test_health_endpoint_degrades_when_redis_is_unavailable(
    client: TestClient,
) -> None:
    redis_cache.set_client(None)

    try:
        response = client.get("/health")
    finally:
        redis_cache.reset_client()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "healthy"
    assert response.json()["redis"] == "unavailable"


def test_frontend_page_is_available(client: TestClient) -> None:
    response = client.get("/app")

    assert response.status_code == 200
    assert "Library Management System" in response.text
    assert "Create member account" in response.text

    stylesheet_response = client.get("/app/assets/css/styles.css")
    script_response = client.get("/app/assets/js/app.js")

    assert stylesheet_response.status_code == 200
    assert script_response.status_code == 200
    assert "text/css" in stylesheet_response.headers["content-type"]
    assert "javascript" in script_response.headers["content-type"]
