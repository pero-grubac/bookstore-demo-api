from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.features.authors.models import Author
from app.features.authors.schemas import AuthorCreate, AuthorUpdate
from app.features.books.models import Book


def list_authors(db: Session, skip: int, limit: int) -> list[Author]:
    stmt = select(Author).order_by(Author.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_author(db: Session, author_id: int) -> Author:
    author = db.get(Author, author_id)
    if author is None:
        raise NotFoundError(f"Author {author_id} not found")
    return author


def create_author(db: Session, data: AuthorCreate) -> Author:
    author = Author(**data.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


def update_author(db: Session, author_id: int, data: AuthorUpdate) -> Author:
    author = get_author(db, author_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(author, field, value)
    db.commit()
    db.refresh(author)
    return author


def delete_author(db: Session, author_id: int) -> None:
    author = get_author(db, author_id)
    if db.scalar(select(exists().where(Book.author_id == author_id))):
        raise ConflictError("Author has books and cannot be deleted")
    db.delete(author)
    db.commit()
