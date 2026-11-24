from fastapi import APIRouter, Depends, status

from app.core.database import DbSession
from app.core.pagination import Limit, Skip
from app.features.auth.dependencies import AdminUser, get_current_customer
from app.features.authors import service
from app.features.authors.schemas import AuthorCreate, AuthorRead, AuthorUpdate

router = APIRouter(
    prefix="/authors",
    tags=["Authors"],
    dependencies=[Depends(get_current_customer)],
)


@router.get("", response_model=list[AuthorRead])
def list_authors(db: DbSession, skip: Skip = 0, limit: Limit = 20):
    return service.list_authors(db, skip, limit)


@router.get("/{author_id}", response_model=AuthorRead)
def get_author(author_id: int, db: DbSession):
    return service.get_author(db, author_id)


@router.post("", response_model=AuthorRead, status_code=status.HTTP_201_CREATED)
def create_author(data: AuthorCreate, db: DbSession, _: AdminUser):
    return service.create_author(db, data)


@router.patch("/{author_id}", response_model=AuthorRead)
def update_author(author_id: int, data: AuthorUpdate, db: DbSession, _: AdminUser):
    return service.update_author(db, author_id, data)


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_author(author_id: int, db: DbSession, _: AdminUser):
    service.delete_author(db, author_id)
