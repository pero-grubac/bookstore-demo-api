from tests.conftest import PASSWORD, register


def test_register_and_get_profile(client):
    headers = register(client, "Ana@Example.com")

    response = client.get("/customers/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["is_admin"] is False
    assert "hashed_password" not in body


def test_register_duplicate_email_conflicts(client):
    register(client, "ana@example.com")
    payload = {"email": "ana@example.com", "full_name": "Ana", "password": PASSWORD}

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409


def test_login_with_wrong_password_fails(client):
    register(client, "ana@example.com")

    response = client.post(
        "/auth/login", data={"username": "ana@example.com", "password": "wrong-pass"}
    )

    assert response.status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get("/customers/me").status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert client.get("/customers/me", headers=bad).status_code == 401


def test_customer_cannot_list_customers(client, customer_headers):
    assert client.get("/customers", headers=customer_headers).status_code == 403
