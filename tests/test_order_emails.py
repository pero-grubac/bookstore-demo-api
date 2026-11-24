from unittest.mock import MagicMock

import pytest

from app.features.orders import tasks
from tests.conftest import TestingSession


@pytest.fixture
def smtp(monkeypatch):
    """Mock SMTP server; returns the connection used inside `with SMTP(...)`."""
    smtp_class = MagicMock()
    monkeypatch.setattr("app.core.email.smtplib.SMTP", smtp_class)
    return smtp_class.return_value.__enter__.return_value


@pytest.fixture(autouse=True)
def task_uses_test_db(monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", TestingSession)


def place_order(client, headers, book_id, quantity=2):
    response = client.post(
        "/orders",
        json={"items": [{"book_id": book_id, "quantity": quantity}]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_creating_order_queues_confirmation(
    client, customer_headers, book, queued_emails
):
    order = place_order(client, customer_headers, book["id"])

    queued_emails.assert_called_once_with(order["id"])


def test_confirmation_task_sends_email(client, customer_headers, book, smtp):
    order = place_order(client, customer_headers, book["id"])

    # Run the task eagerly, the same way the worker would.
    result = tasks.send_order_confirmation.apply(args=[order["id"]])

    assert result.successful()
    smtp.send_message.assert_called_once()
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "customer@example.com"
    assert message["Subject"] == f"Order #{order['id']} confirmed"
    text = message.get_body(preferencelist=("plain",)).get_content()
    assert "2 x Na Drini ćuprija" in text
    assert "Total: 29.80" in text


def test_confirmation_task_skips_missing_order(db, smtp):
    result = tasks.send_order_confirmation.apply(args=[999])

    assert result.successful()
    smtp.send_message.assert_not_called()
