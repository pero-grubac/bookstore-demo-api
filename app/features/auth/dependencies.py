from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.database import DbSession
from app.core.security import decode_access_token
from app.features.customers.models import Customer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_customer(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> Customer:
    subject = decode_access_token(token)
    customer = db.get(Customer, int(subject)) if subject and subject.isdigit() else None
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]


def require_admin(customer: CurrentCustomer) -> Customer:
    if not customer.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return customer


AdminUser = Annotated[Customer, Depends(require_admin)]
