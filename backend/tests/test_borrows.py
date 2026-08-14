from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal


ADMIN_DATA = {
    "full_name": "Library Admin",
    "email": "borrow.admin@example.com",
    "password": "AdminPassword@123",
}

MEMBER_DATA = {
    "full_name": "First Member",
    "email": "first.member@example.com",
    "password": "MemberPassword@123",
}

SECOND_MEMBER_DATA = {
    "full_name": "Second Member",
    "email": "second.member@example.com",
    "password": "MemberPassword@456",
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

    return {"Authorization": (f"Bearer {login_response.json()['access_token']}")}


def create_book(
    client: TestClient,
    admin_headers: dict[str, str],
    index: int = 1,
    total_copies: int = 1,
) -> dict:
    response = client.post(
        "/api/v1/books",
        headers=admin_headers,
        json={
            "title": f"Test Book {index}",
            "author": f"Test Author {index}",
            "isbn": f"978000000{index:04d}",
            "total_copies": total_copies,
        },
    )
    assert response.status_code == 201
    return response.json()


def borrow_book(
    client: TestClient,
    member_headers: dict[str, str],
    book_id: int,
):
    return client.post(
        "/api/v1/borrows",
        headers=member_headers,
        json={"book_id": book_id},
    )


def test_borrow_book_success(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    book = create_book(client, admin_headers, total_copies=2)

    response = borrow_book(client, member_headers, book["id"])

    assert response.status_code == 201
    assert response.json()["book_id"] == book["id"]
    assert response.json()["returned_at"] is None

    book_response = client.get(
        f"/api/v1/books/{book['id']}",
        headers=member_headers,
    )
    assert book_response.json()["available_copies"] == 1


def test_borrow_without_token(client: TestClient):
    response = client.post(
        "/api/v1/borrows",
        json={"book_id": 1},
    )

    assert response.status_code == 401


def test_admin_cannot_borrow(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    book = create_book(client, admin_headers)

    response = borrow_book(client, admin_headers, book["id"])

    assert response.status_code == 403
    assert response.json()["detail"] == ("Member privileges required.")


def test_borrow_missing_book(client: TestClient):
    member_headers = register_and_login(client, MEMBER_DATA)

    response = borrow_book(client, member_headers, 999)

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found."


def test_cannot_borrow_unavailable_book(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    first_headers = register_and_login(client, MEMBER_DATA)
    second_headers = register_and_login(
        client,
        SECOND_MEMBER_DATA,
    )
    book = create_book(client, admin_headers)
    assert (
        borrow_book(
            client,
            first_headers,
            book["id"],
        ).status_code
        == 201
    )

    response = borrow_book(client, second_headers, book["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == ("No available copies of this book.")


def test_cannot_borrow_same_book_twice(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    book = create_book(client, admin_headers, total_copies=2)
    assert (
        borrow_book(
            client,
            member_headers,
            book["id"],
        ).status_code
        == 201
    )

    response = borrow_book(client, member_headers, book["id"])

    assert response.status_code == 409
    assert response.json()["detail"] == ("You have already borrowed this book.")


def test_borrow_limit_is_three_books(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    books = [create_book(client, admin_headers, index=index) for index in range(1, 5)]

    for book in books[:3]:
        assert (
            borrow_book(
                client,
                member_headers,
                book["id"],
            ).status_code
            == 201
        )

    response = borrow_book(
        client,
        member_headers,
        books[3]["id"],
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("You cannot borrow more than 3 books.")


def test_invalid_book_id_is_rejected(client: TestClient):
    member_headers = register_and_login(client, MEMBER_DATA)

    response = borrow_book(client, member_headers, 0)

    assert response.status_code == 422


def test_return_book_success(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    book = create_book(client, admin_headers)
    record = borrow_book(
        client,
        member_headers,
        book["id"],
    ).json()

    response = client.post(
        f"/api/v1/borrows/{record['id']}/return",
        headers=member_headers,
    )

    assert response.status_code == 200
    assert response.json()["returned_at"] is not None

    book_response = client.get(
        f"/api/v1/books/{book['id']}",
        headers=member_headers,
    )
    assert book_response.json()["available_copies"] == 1


def test_return_missing_record(client: TestClient):
    member_headers = register_and_login(client, MEMBER_DATA)

    response = client.post(
        "/api/v1/borrows/999/return",
        headers=member_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == ("Borrow record not found.")


def test_member_cannot_return_another_members_book(
    client: TestClient,
):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    first_headers = register_and_login(client, MEMBER_DATA)
    second_headers = register_and_login(
        client,
        SECOND_MEMBER_DATA,
    )
    book = create_book(client, admin_headers)
    record = borrow_book(
        client,
        first_headers,
        book["id"],
    ).json()

    response = client.post(
        f"/api/v1/borrows/{record['id']}/return",
        headers=second_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == ("You cannot return another user's book.")


def test_cannot_return_same_record_twice(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    book = create_book(client, admin_headers)
    record = borrow_book(
        client,
        member_headers,
        book["id"],
    ).json()
    return_url = f"/api/v1/borrows/{record['id']}/return"
    assert (
        client.post(
            return_url,
            headers=member_headers,
        ).status_code
        == 200
    )

    response = client.post(return_url, headers=member_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == ("This book has already been returned.")


def test_member_can_reborrow_after_return(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    book = create_book(client, admin_headers)
    first_record = borrow_book(
        client,
        member_headers,
        book["id"],
    ).json()
    assert (
        client.post(
            f"/api/v1/borrows/{first_record['id']}/return",
            headers=member_headers,
        ).status_code
        == 200
    )

    response = borrow_book(client, member_headers, book["id"])

    assert response.status_code == 201
    assert response.json()["id"] != first_record["id"]


def test_personal_history_contains_only_current_members_records(
    client: TestClient,
):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    first_headers = register_and_login(client, MEMBER_DATA)
    second_headers = register_and_login(
        client,
        SECOND_MEMBER_DATA,
    )
    first_book = create_book(client, admin_headers, index=1)
    second_book = create_book(client, admin_headers, index=2)
    first_record = borrow_book(
        client,
        first_headers,
        first_book["id"],
    ).json()
    borrow_book(client, second_headers, second_book["id"])

    response = client.get(
        "/api/v1/borrows/me/history",
        headers=first_headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first_record["id"]]


def test_admin_can_view_all_borrow_records(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    first_headers = register_and_login(client, MEMBER_DATA)
    second_headers = register_and_login(
        client,
        SECOND_MEMBER_DATA,
    )
    first_book = create_book(client, admin_headers, index=1)
    second_book = create_book(client, admin_headers, index=2)
    borrow_book(client, first_headers, first_book["id"])
    borrow_book(client, second_headers, second_book["id"])

    response = client.get(
        "/api/v1/borrows",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_member_cannot_view_all_borrow_records(client: TestClient):
    member_headers = register_and_login(client, MEMBER_DATA)

    response = client.get(
        "/api/v1/borrows",
        headers=member_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == ("Admin privileges required.")


def test_borrowed_book_cannot_be_deleted(client: TestClient):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    member_headers = register_and_login(client, MEMBER_DATA)
    book = create_book(client, admin_headers)
    borrow_book(client, member_headers, book["id"])

    response = client.delete(
        f"/api/v1/books/{book['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("A borrowed book cannot be deleted.")


def test_total_copies_cannot_drop_below_borrowed_count(
    client: TestClient,
):
    admin_headers = register_and_login(
        client,
        ADMIN_DATA,
        make_admin=True,
    )
    first_headers = register_and_login(client, MEMBER_DATA)
    second_headers = register_and_login(
        client,
        SECOND_MEMBER_DATA,
    )
    book = create_book(client, admin_headers, total_copies=2)
    borrow_book(client, first_headers, book["id"])
    borrow_book(client, second_headers, book["id"])

    response = client.put(
        f"/api/v1/books/{book['id']}",
        headers=admin_headers,
        json={"total_copies": 1},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Total copies cannot be less than borrowed copies."
    )
