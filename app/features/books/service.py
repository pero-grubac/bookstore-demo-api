from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core import cache
from app.core.exceptions import ConflictError, NotFoundError
from app.features.authors.service import get_author
from app.features.books.models import Book
from app.features.books.schemas import BookCreate, BookRead, BookUpdate
from app.features.categories.models import Category
from app.features.categories.service import get_categories_by_ids
from app.features.orders.models import OrderItem


def cache_key(book_id: int) -> str:
    return f"books:{book_id}"


def list_books(
    db: Session,
    skip: int,
    limit: int,
    author_id: int | None = None,
    category_id: int | None = None,
    search: str | None = None,
) -> list[Book]:
    stmt = select(Book).order_by(Book.id)
    if author_id is not None:
        stmt = stmt.where(Book.author_id == author_id)
    if category_id is not None:
        stmt = stmt.where(Book.categories.any(Category.id == category_id))
    if search:
        stmt = stmt.where(Book.title.ilike(f"%{search}%"))
    return list(db.scalars(stmt.offset(skip).limit(limit)))


def get_book(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise NotFoundError(f"Book {book_id} not found")
    return book


def get_book_details(db: Session, book_id: int) -> BookRead:
    """Read-through cache for a single book (served from Redis when possible)."""
    if cached := cache.get(cache_key(book_id)):
        return BookRead.model_validate(cached)
    book = BookRead.model_validate(get_book(db, book_id))
    cache.set(cache_key(book_id), book.model_dump(mode="json"))
    return book


def _ensure_isbn_is_free(db: Session, isbn: str) -> None:
    if db.scalar(select(Book.id).where(Book.isbn == isbn)):
        raise ConflictError(f"Book with ISBN {isbn} already exists")


def create_book(db: Session, data: BookCreate) -> Book:
    get_author(db, data.author_id)
    _ensure_isbn_is_free(db, data.isbn)
    book = Book(
        **data.model_dump(exclude={"category_ids"}),
        categories=get_categories_by_ids(db, data.category_ids),
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(db: Session, book_id: int, data: BookUpdate) -> Book:
    book = get_book(db, book_id)
    changes = data.model_dump(exclude_unset=True)

    if "author_id" in changes:
        get_author(db, changes["author_id"])
    if "isbn" in changes and changes["isbn"] != book.isbn:
        _ensure_isbn_is_free(db, changes["isbn"])
    if "category_ids" in changes:
        book.categories = get_categories_by_ids(db, changes.pop("category_ids"))

    for field, value in changes.items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    cache.delete(cache_key(book_id))
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book(db, book_id)
    if db.scalar(select(exists().where(OrderItem.book_id == book_id))):
        raise ConflictError("Book is part of existing orders and cannot be deleted")
    db.delete(book)
    db.commit()
    cache.delete(cache_key(book_id))
