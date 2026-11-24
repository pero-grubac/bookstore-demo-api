from fastapi import APIRouter

from app.core.database import DbSession
from app.core.pagination import Limit, Skip
from app.features.auth.dependencies import AdminUser, CurrentCustomer
from app.features.customers import service
from app.features.customers.schemas import CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/me", response_model=CustomerRead)
def get_me(customer: CurrentCustomer):
    return customer


@router.patch("/me", response_model=CustomerRead)
def update_me(data: CustomerUpdate, db: DbSession, customer: CurrentCustomer):
    return service.update_customer(db, customer, data)


@router.get("", response_model=list[CustomerRead])
def list_customers(db: DbSession, _: AdminUser, skip: Skip = 0, limit: Limit = 20):
    return service.list_customers(db, skip, limit)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: DbSession, _: AdminUser):
    return service.get_customer(db, customer_id)
