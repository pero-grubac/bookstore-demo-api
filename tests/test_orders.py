from tests.conftest import register


def place_order(client, headers, book_id, quantity):
    return client.post(
        "/orders",
        json={"items": [{"book_id": book_id, "quantity": quantity}]},
        headers=headers,
    )


def stock(client, headers, book_id):
    return client.get(f"/books/{book_id}", headers=headers).json()["stock"]


def test_order_reserves_stock_and_computes_total(client, customer_headers, book):
    response = place_order(client, customer_headers, book["id"], 2)

    assert response.status_code == 201, response.text
    order = response.json()
    assert order["status"] == "pending"
    assert order["total"] == "29.80"
    assert order["items"][0]["book"]["title"] == book["title"]
    assert stock(client, customer_headers, book["id"]) == 3


def test_order_fails_when_out_of_stock(client, customer_headers, book):
    response = place_order(client, customer_headers, book["id"], 6)

    assert response.status_code == 409
    assert stock(client, customer_headers, book["id"]) == 5


def test_cancel_returns_stock(client, customer_headers, book):
    order = place_order(client, customer_headers, book["id"], 2).json()

    response = client.post(f"/orders/{order['id']}/cancel", headers=customer_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert stock(client, customer_headers, book["id"]) == 5


def test_status_flow_is_enforced(client, customer_headers, admin_headers, book):
    order = place_order(client, customer_headers, book["id"], 1).json()

    def set_status(status):
        url = f"/orders/{order['id']}/status"
        return client.patch(url, json={"status": status}, headers=admin_headers)

    assert set_status("shipped").status_code == 409  # must be paid first
    assert set_status("paid").status_code == 200
    assert set_status("shipped").status_code == 200
    # Customers can only cancel pending orders.
    cancel = client.post(f"/orders/{order['id']}/cancel", headers=customer_headers)
    assert cancel.status_code == 409


def test_customers_only_see_their_own_orders(
    client, customer_headers, admin_headers, book
):
    order = place_order(client, customer_headers, book["id"], 1).json()
    other_headers = register(client, "other@example.com")

    assert client.get("/orders", headers=other_headers).json() == []
    assert (
        client.get(f"/orders/{order['id']}", headers=other_headers).status_code == 404
    )
    assert len(client.get("/orders", headers=admin_headers).json()) == 1
