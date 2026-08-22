from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal


ADMIN_DATA = {
    "full_name": "Library Admin",
    "email": "admin@example.com",
    "password": "AdminPassword@123",
}

MEMBER_DATA = {
    "full_name": "Library Member",
    "email": "member@example.com",
    "password": "MemberPassword@123",
}

BOOK_DATA = {
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "9780132350884",
    "total_copies": 3,
}


def register_and_login(
    client: TestClient,
    user_data: dict[str, str],
    make_admin: bool = False,
) -> dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 201

    if make_admin:
        with TestingSessionLocal() as db:
            user = db.scalar(select(User).where(User.email == user_data["email"]))

            assert user is not None

            user.role = UserRole.ADMIN
            db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": user_data["email"],
            "password": user_data["password"],
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def create_admin_headers(
    client: TestClient,
) -> dict[str, str]:
    return register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )


def create_member_headers(
    client: TestClient,
) -> dict[str, str]:
    return register_and_login(
        client,
        MEMBER_DATA,
    )


def create_book(
    client: TestClient,
    headers: dict[str, str],
    book_data: dict | None = None,
):
    return client.post(
        "/api/v1/books",
        json=book_data or BOOK_DATA,
        headers=headers,
    )


def test_create_book_success(client: TestClient):
    headers = create_admin_headers(client)
    response = create_book(client, headers)
    body = response.json()

    assert response.status_code == 201
    assert body["title"] == BOOK_DATA["title"]
    assert body["author"] == BOOK_DATA["author"]
    assert body["isbn"] == BOOK_DATA["isbn"]
    assert body["total_copies"] == 3
    assert body["available_copies"] == 3


def test_create_book_without_token(
    client: TestClient,
):
    response = client.post(
        "/api/v1/books",
        json=BOOK_DATA,
    )

    assert response.status_code == 401


def test_member_cannot_create_book(
    client: TestClient,
):
    headers = create_member_headers(client)
    response = create_book(client, headers)

    assert response.status_code == 403
    assert response.json()["detail"] == ("Admin privileges required.")


def test_create_duplicate_isbn(
    client: TestClient,
):
    headers = create_admin_headers(client)

    create_book(client, headers)
    response = create_book(client, headers)

    assert response.status_code == 409
    assert response.json()["detail"] == ("A book with this ISBN already exists.")


def test_create_invalid_book(
    client: TestClient,
):
    headers = create_admin_headers(client)

    response = create_book(
        client,
        headers,
        {
            "title": "",
            "author": "",
            "isbn": "123",
            "total_copies": 0,
        },
    )

    assert response.status_code == 422


def test_list_books(client: TestClient):
    headers = create_admin_headers(client)

    create_book(client, headers)

    response = client.get(
        "/api/v1/books",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["isbn"] == (BOOK_DATA["isbn"])


def test_get_book_by_id(client: TestClient):
    headers = create_admin_headers(client)

    created_book = create_book(
        client,
        headers,
    ).json()

    response = client.get(
        f"/api/v1/books/{created_book['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == (created_book["id"])


def test_get_missing_book(client: TestClient):
    headers = create_admin_headers(client)

    response = client.get(
        "/api/v1/books/999",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == ("Book not found.")


def test_update_book_success(
    client: TestClient,
):
    headers = create_admin_headers(client)

    created_book = create_book(
        client,
        headers,
    ).json()

    response = client.put(
        f"/api/v1/books/{created_book['id']}",
        json={
            "title": "Clean Code Updated",
            "total_copies": 5,
        },
        headers=headers,
    )

    body = response.json()

    assert response.status_code == 200
    assert body["title"] == "Clean Code Updated"
    assert body["total_copies"] == 5
    assert body["available_copies"] == 5


def test_member_cannot_update_book(
    client: TestClient,
):
    admin_headers = create_admin_headers(client)

    created_book = create_book(
        client,
        admin_headers,
    ).json()

    member_headers = create_member_headers(client)

    response = client.put(
        f"/api/v1/books/{created_book['id']}",
        json={"title": "Unauthorized Update"},
        headers=member_headers,
    )

    assert response.status_code == 403


def test_update_to_duplicate_isbn(
    client: TestClient,
):
    headers = create_admin_headers(client)

    first_book = create_book(
        client,
        headers,
    ).json()

    second_book = create_book(
        client,
        headers,
        {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt",
            "isbn": "9780135957059",
            "total_copies": 2,
        },
    ).json()

    response = client.put(
        f"/api/v1/books/{second_book['id']}",
        json={"isbn": first_book["isbn"]},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("A book with this ISBN already exists.")


def test_delete_book_success(
    client: TestClient,
):
    headers = create_admin_headers(client)

    created_book = create_book(
        client,
        headers,
    ).json()

    response = client.delete(
        f"/api/v1/books/{created_book['id']}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(
        f"/api/v1/books/{created_book['id']}",
        headers=headers,
    )

    assert get_response.status_code == 404


def test_delete_missing_book(
    client: TestClient,
):
    headers = create_admin_headers(client)

    response = client.delete(
        "/api/v1/books/999",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == ("Book not found.")


def test_list_books_pagination(client: TestClient):
    headers = create_admin_headers(client)

    books_data = [
        {
            "title": "First Book",
            "author": "First Author",
            "isbn": "9780000000001",
            "total_copies": 1,
        },
        {
            "title": "Second Book",
            "author": "Second Author",
            "isbn": "9780000000002",
            "total_copies": 1,
        },
        {
            "title": "Third Book",
            "author": "Third Author",
            "isbn": "9780000000003",
            "total_copies": 1,
        },
    ]

    for book_data in books_data:
        response = create_book(
            client,
            headers,
            book_data,
        )
        assert response.status_code == 201

    response = client.get(
        "/api/v1/books",
        params={
            "skip": 1,
            "limit": 1,
        },
        headers=headers,
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["isbn"] == books_data[1]["isbn"]


def test_search_books_by_title_case_insensitive(
    client: TestClient,
):
    headers = create_admin_headers(client)
    create_book(client, headers)

    response = client.get(
        "/api/v1/books/search",
        params={"query": "clean"},
        headers=headers,
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["title"] == BOOK_DATA["title"]


def test_search_books_by_author(
    client: TestClient,
):
    headers = create_admin_headers(client)
    create_book(client, headers)

    response = client.get(
        "/api/v1/books/search",
        params={"query": "robert"},
        headers=headers,
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["author"] == BOOK_DATA["author"]


def test_search_books_by_isbn(
    client: TestClient,
):
    headers = create_admin_headers(client)
    create_book(client, headers)

    response = client.get(
        "/api/v1/books/search",
        params={"query": BOOK_DATA["isbn"]},
        headers=headers,
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body) == 1
    assert body[0]["isbn"] == BOOK_DATA["isbn"]


def test_search_books_returns_empty_list_when_no_match(
    client: TestClient,
):
    headers = create_admin_headers(client)
    create_book(client, headers)

    response = client.get(
        "/api/v1/books/search",
        params={"query": "nonexistent book"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []
