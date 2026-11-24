"""Import every model so SQLAlchemy and Alembic see the full schema."""

from app.core.database import Base
from app.features.authors.models import Author
from app.features.books.models import Book, book_categories
from app.features.categories.models import Category
from app.features.customers.models import Customer
from app.features.orders.models import Order, OrderItem

__all__ = [
    "Base",
    "Author",
    "Book",
    "book_categories",
    "Category",
    "Customer",
    "Order",
    "OrderItem",
]
