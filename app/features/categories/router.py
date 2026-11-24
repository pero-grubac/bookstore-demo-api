from fastapi import APIRouter, Depends, status

from app.core.database import DbSession
from app.core.pagination import Limit, Skip
from app.features.auth.dependencies import AdminUser, get_current_customer
from app.features.categories import service
from app.features.categories.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    dependencies=[Depends(get_current_customer)],
)


@router.get("", response_model=list[CategoryRead])
def list_categories(db: DbSession, skip: Skip = 0, limit: Limit = 50):
    return service.list_categories(db, skip, limit)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: DbSession):
    return service.get_category(db, category_id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, _: AdminUser):
    return service.create_category(db, data)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, data: CategoryUpdate, db: DbSession, _: AdminUser
):
    return service.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession, _: AdminUser):
    service.delete_category(db, category_id)
