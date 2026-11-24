import os
from unittest.mock import MagicMock

# Configure the app for tests before it is imported: in-memory DB, no Redis.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["REDIS_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.features.customers.schemas import CustomerCreate  # noqa: E402
from app.features.customers.service import create_customer  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "secret123"

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    with TestingSession() as session:
        yield session


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    with TestingSession() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def queued_emails(monkeypatch):
    """Replace the Celery queue: tests need no broker; tasks are recorded."""
    task = MagicMock()
    monkeypatch.setattr("app.features.orders.router.send_order_confirmation", task)
    return task.delay


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    response = client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register(client: TestClient, email: str) -> dict:
    payload = {"email": email, "full_name": "Test User", "password": PASSWORD}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return login(client, email)


@pytest.fixture
def customer_headers(client):
    return register(client, "customer@example.com")


@pytest.fixture
def admin_headers(client, db):
    data = CustomerCreate(
        email="admin@example.com", full_name="Admin", password=PASSWORD
    )
    create_customer(db, data, is_admin=True)
    return login(client, data.email)


@pytest.fixture
def book(client, admin_headers):
    author = client.post(
        "/authors", json={"name": "Ivo Andrić"}, headers=admin_headers
    ).json()
    category = client.post(
        "/categories", json={"name": "Classics"}, headers=admin_headers
    ).json()
    response = client.post(
        "/books",
        json={
            "title": "Na Drini ćuprija",
            "isbn": "9788652139601",
            "price": "14.90",
            "stock": 5,
            "author_id": author["id"],
            "category_ids": [category["id"]],
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
