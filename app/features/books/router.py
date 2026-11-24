from fastapi import APIRouter, Depends, Query, status

from app.core.database import DbSession
from app.core.pagination import Limit, Skip
from app.features.auth.dependencies import AdminUser, get_current_customer
from app.features.books import service
from app.features.books.schemas import BookCreate, BookRead, BookUpdate

router = APIRouter(
    prefix="/books",
    tags=["Books"],
    dependencies=[Depends(get_current_customer)],
)


@router.get("", response_model=list[BookRead])
def list_books(
    db: DbSession,
    skip: Skip = 0,
    limit: Limit = 20,
    author_id: int | None = None,
    category_id: int | None = None,
    search: str | None = Query(None, description="Case-insensitive title search"),
):
    return service.list_books(db, skip, limit, author_id, category_id, search)


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: int, db: DbSession):
    return service.get_book_details(db, book_id)


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
def create_book(data: BookCreate, db: DbSession, _: AdminUser):
    return service.create_book(db, data)


@router.patch("/{book_id}", response_model=BookRead)
def update_book(book_id: int, data: BookUpdate, db: DbSession, _: AdminUser):
    return service.update_book(db, book_id, data)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: DbSession, _: AdminUser):
    service.delete_book(db, book_id)
