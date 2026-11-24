def test_catalog_requires_login(client):
    for path in ("/books", "/authors", "/categories"):
        assert client.get(path).status_code == 401


def test_customer_can_read_book(client, customer_headers, book):
    response = client.get(f"/books/{book['id']}", headers=customer_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Na Drini ćuprija"
    assert body["price"] == "14.90"
    assert body["author"]["name"] == "Ivo Andrić"
    assert [c["name"] for c in body["categories"]] == ["Classics"]


def test_customer_cannot_modify_catalog(client, customer_headers):
    response = client.post("/authors", json={"name": "X"}, headers=customer_headers)

    assert response.status_code == 403


def test_filter_books(client, customer_headers, book):
    def count(**params):
        return len(client.get("/books", params=params, headers=customer_headers).json())

    assert count(search="drini") == 1
    assert count(search="dune") == 0
    assert count(category_id=book["categories"][0]["id"]) == 1
    assert count(author_id=999) == 0


def test_duplicate_isbn_conflicts(client, admin_headers, book):
    payload = {
        "title": "Copy",
        "isbn": book["isbn"],
        "price": "1.00",
        "author_id": book["author"]["id"],
    }

    response = client.post("/books", json=payload, headers=admin_headers)

    assert response.status_code == 409


def test_update_book_partially(client, admin_headers, book):
    response = client.patch(
        f"/books/{book['id']}",
        json={"price": "9.99", "category_ids": []},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == "9.99"
    assert body["title"] == book["title"]
    assert body["categories"] == []


def test_cannot_null_required_field(client, admin_headers, book):
    response = client.patch(
        f"/books/{book['id']}", json={"title": None}, headers=admin_headers
    )

    assert response.status_code == 422


def test_cannot_delete_author_with_books(client, admin_headers, book):
    response = client.delete(f"/authors/{book['author']['id']}", headers=admin_headers)

    assert response.status_code == 409


def test_unknown_book_returns_404(client, customer_headers):
    assert client.get("/books/12345", headers=customer_headers).status_code == 404


def test_update_category(client, admin_headers, book):
    category_id = book["categories"][0]["id"]
    url = f"/categories/{category_id}"

    response = client.patch(url, json={"name": "World Classics"}, headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "World Classics"
    assert client.patch(url, json={}, headers=admin_headers).status_code == 200
    assert client.put(url, json={"name": "X"}, headers=admin_headers).status_code == 405
