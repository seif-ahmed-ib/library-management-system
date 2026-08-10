from fastapi.testclient import TestClient


USER_DATA = {
    "full_name": "Seif Ahmed",
    "email": "seif.test@example.com",
    "password": "TestPassword@123",
}


def register_user(client: TestClient):
    return client.post(
        "/api/v1/auth/register",
        json=USER_DATA,
    )


def login_user(
    client: TestClient,
    password: str = USER_DATA["password"],
):
    return client.post(
        "/api/v1/auth/login",
        data={
            "username": USER_DATA["email"],
            "password": password,
        },
    )


def get_access_token(client: TestClient) -> str:
    register_user(client)
    response = login_user(client)
    return response.json()["access_token"]


def test_health_endpoint(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Library Management System API is running"
    }


def test_register_user_success(client: TestClient):
    response = register_user(client)
    body = response.json()

    assert response.status_code == 201
    assert body["full_name"] == USER_DATA["full_name"]
    assert body["email"] == USER_DATA["email"]
    assert body["role"] == "member"
    assert body["is_active"] is True
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email(client: TestClient):
    register_user(client)
    response = register_user(client)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A user with this email already exists."
    )


def test_register_invalid_data(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "S",
            "email": "invalid-email",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_login_success(client: TestClient):
    register_user(client)
    response = login_user(client)
    body = response.json()

    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_login_wrong_password(client: TestClient):
    register_user(client)
    response = login_user(
        client,
        password="WrongPassword123",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Incorrect email or password."
    }


def test_me_with_valid_token(client: TestClient):
    token = get_access_token(client)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == USER_DATA["email"]
    assert response.json()["full_name"] == USER_DATA["full_name"]


def test_me_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_with_invalid_token(client: TestClient):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials."
    }