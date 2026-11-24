from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.features.customers.models import Customer
from app.features.customers.schemas import CustomerCreate, CustomerUpdate

# Verifying against a dummy hash keeps login timing the same for unknown emails.
_DUMMY_HASH = hash_password("dummy-password")


def get_by_email(db: Session, email: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.email == email.lower()))


def list_customers(db: Session, skip: int, limit: int) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return customer


def create_customer(
    db: Session, data: CustomerCreate, is_admin: bool = False
) -> Customer:
    if get_by_email(db, data.email):
        raise ConflictError("Email is already registered")
    customer = Customer(
        email=data.email.lower(),
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_admin=is_admin,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(db: Session, customer: Customer, data: CustomerUpdate) -> Customer:
    changes = data.model_dump(exclude_unset=True)
    if "password" in changes:
        customer.hashed_password = hash_password(changes.pop("password"))
    for field, value in changes.items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def authenticate(db: Session, email: str, password: str) -> Customer | None:
    customer = get_by_email(db, email)
    if customer is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, customer.hashed_password):
        return None
    return customer
