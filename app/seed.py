"""Fill the database with demo data so every GET endpoint returns something.

Creates an admin, a few customers, 5 authors, 4 categories, 10 books and
some orders in different states.

Usage:  python -m app.seed
Safe to run more than once: if the catalog already has books, only missing
accounts are created.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.features.customers import service as customers
from app.features.customers.schemas import CustomerCreate
from app.features.orders import service as orders
from app.features.orders.models import OrderStatus
from app.features.orders.schemas import OrderCreate, OrderItemCreate
from app.models import Author, Book, Category, Customer

CUSTOMER_PASSWORD = "password123"

CUSTOMERS = [
    ("ana.petrovic@example.com", "Ana Petrović"),
    ("marko.jovanovic@example.com", "Marko Jovanović"),
    ("jelena.nikolic@example.com", "Jelena Nikolić"),
]

CATEGORIES = ["Classics", "Fantasy", "Historical Fiction", "Mystery"]

AUTHORS = {
    "Ivo Andrić": "Yugoslav novelist and Nobel Prize laureate in Literature (1961).",
    "Meša Selimović": "Bosnian writer best known for the novel Death and the Dervish.",
    "J. R. R. Tolkien": "English writer and philologist, author of Middle-earth.",
    "George Orwell": "English novelist and essayist known for his political fiction.",
    "Agatha Christie": "English crime novelist, creator of Hercule Poirot.",
}

# title, author, isbn, price, stock, year, categories, description
BOOKS = [
    (
        "Na Drini ćuprija",
        "Ivo Andrić",
        "9788652103119",
        "14.90",
        12,
        1945,
        ["Classics", "Historical Fiction"],
        "Four centuries of life around the bridge in Višegrad.",
    ),
    (
        "Prokleta avlija",
        "Ivo Andrić",
        "9788652104574",
        "9.90",
        8,
        1954,
        ["Classics"],
        "A short novel set in an Istanbul prison.",
    ),
    (
        "Derviš i smrt",
        "Meša Selimović",
        "9788652106820",
        "13.50",
        10,
        1966,
        ["Classics", "Historical Fiction"],
        "A dervish's crisis of faith after his brother is arrested.",
    ),
    (
        "Tvrđava",
        "Meša Selimović",
        "9788652107193",
        "12.90",
        6,
        1970,
        ["Historical Fiction"],
        "A soldier returns home from war to 18th-century Sarajevo.",
    ),
    (
        "The Hobbit",
        "J. R. R. Tolkien",
        "9780547928227",
        "12.50",
        20,
        1937,
        ["Fantasy", "Classics"],
        "Bilbo Baggins joins thirteen dwarves on a quest for treasure.",
    ),
    (
        "The Fellowship of the Ring",
        "J. R. R. Tolkien",
        "9780547928210",
        "15.00",
        15,
        1954,
        ["Fantasy"],
        "The first part of The Lord of the Rings.",
    ),
    (
        "1984",
        "George Orwell",
        "9780451524935",
        "10.99",
        25,
        1949,
        ["Classics"],
        "A dystopian novel about surveillance and totalitarianism.",
    ),
    (
        "Animal Farm",
        "George Orwell",
        "9780451526342",
        "8.99",
        18,
        1945,
        ["Classics"],
        "A satirical fable about a revolution on an English farm.",
    ),
    (
        "Murder on the Orient Express",
        "Agatha Christie",
        "9780062693662",
        "11.99",
        14,
        1934,
        ["Mystery", "Classics"],
        "Hercule Poirot investigates a murder aboard a snowbound train.",
    ),
    (
        "And Then There Were None",
        "Agatha Christie",
        "9780062073488",
        "10.50",
        9,
        1939,
        ["Mystery"],
        "Ten strangers are lured to an island and die one by one.",
    ),
]

# customer email, [(isbn, quantity)], final status
ORDERS = [
    (
        "ana.petrovic@example.com",
        [("9788652103119", 1), ("9788652106820", 1)],
        OrderStatus.SHIPPED,
    ),
    ("ana.petrovic@example.com", [("9780547928227", 2)], OrderStatus.PENDING),
    (
        "marko.jovanovic@example.com",
        [("9780451524935", 1), ("9780451526342", 1)],
        OrderStatus.PAID,
    ),
    ("jelena.nikolic@example.com", [("9780062693662", 1)], OrderStatus.CANCELLED),
    (
        "jelena.nikolic@example.com",
        [("9780062073488", 1), ("9780547928210", 1)],
        OrderStatus.PENDING,
    ),
]

# How to reach each final status from "pending".
STATUS_PATH = {
    OrderStatus.PENDING: [],
    OrderStatus.PAID: [OrderStatus.PAID],
    OrderStatus.SHIPPED: [OrderStatus.PAID, OrderStatus.SHIPPED],
    OrderStatus.CANCELLED: [OrderStatus.CANCELLED],
}


def seed_accounts(db: Session) -> None:
    accounts = [(settings.ADMIN_EMAIL, "Store Admin", settings.ADMIN_PASSWORD, True)]
    accounts += [(email, name, CUSTOMER_PASSWORD, False) for email, name in CUSTOMERS]
    for email, full_name, password, is_admin in accounts:
        if customers.get_by_email(db, email) is None:
            data = CustomerCreate(email=email, full_name=full_name, password=password)
            customers.create_customer(db, data, is_admin=is_admin)
            print(f"Created {'admin' if is_admin else 'customer'} {email}")


def seed_catalog(db: Session) -> None:
    categories = {c.name: c for c in db.scalars(select(Category))}
    for name in CATEGORIES:
        categories.setdefault(name, Category(name=name))
    authors = {name: Author(name=name, bio=bio) for name, bio in AUTHORS.items()}
    for title, author, isbn, price, stock, year, cats, description in BOOKS:
        db.add(
            Book(
                title=title,
                isbn=isbn,
                description=description,
                price=Decimal(price),
                stock=stock,
                published_year=year,
                author=authors[author],
                categories=[categories[c] for c in cats],
            )
        )
    db.commit()
    print(
        f"Created {len(authors)} authors, {len(categories)} categories "
        f"and {len(BOOKS)} books"
    )


def seed_orders(db: Session) -> None:
    book_ids = {
        isbn: book_id for isbn, book_id in db.execute(select(Book.isbn, Book.id))
    }
    for email, items, final_status in ORDERS:
        customer = db.scalar(select(Customer).where(Customer.email == email))
        data = OrderCreate(
            items=[
                OrderItemCreate(book_id=book_ids[isbn], quantity=quantity)
                for isbn, quantity in items
            ]
        )
        order = orders.create_order(db, customer, data)
        for status in STATUS_PATH[final_status]:
            order = orders.change_status(db, order, status)
    print(f"Created {len(ORDERS)} orders")


def seed() -> None:
    with SessionLocal() as db:
        seed_accounts(db)
        if db.scalar(select(Book.id).limit(1)):
            print("Catalog already has books, skipping catalog and orders")
            return
        seed_catalog(db)
        seed_orders(db)


if __name__ == "__main__":
    seed()
