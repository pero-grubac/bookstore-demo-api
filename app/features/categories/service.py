from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.features.categories.models import Category
from app.features.categories.schemas import CategoryCreate, CategoryUpdate


def list_categories(db: Session, skip: int, limit: int) -> list[Category]:
    stmt = select(Category).order_by(Category.name).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError(f"Category {category_id} not found")
    return category


def get_categories_by_ids(db: Session, ids: list[int]) -> list[Category]:
    """Load categories by id, failing if any of them does not exist."""
    unique_ids = set(ids)
    categories = list(db.scalars(select(Category).where(Category.id.in_(unique_ids))))
    missing = unique_ids - {c.id for c in categories}
    if missing:
        raise NotFoundError(f"Categories not found: {sorted(missing)}")
    return categories


def _ensure_name_is_free(db: Session, name: str) -> None:
    if db.scalar(select(Category.id).where(Category.name == name)):
        raise ConflictError(f"Category '{name}' already exists")


def create_category(db: Session, data: CategoryCreate) -> Category:
    _ensure_name_is_free(db, data.name)
    category = Category(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category(db, category_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] != category.name:
        _ensure_name_is_free(db, changes["name"])
    for field, value in changes.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    db.delete(category)
    db.commit()
