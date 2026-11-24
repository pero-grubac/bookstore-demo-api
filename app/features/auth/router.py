from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import DbSession
from app.core.security import create_access_token
from app.features.auth.schemas import Token
from app.features.customers import service as customers
from app.features.customers.schemas import CustomerCreate, CustomerRead

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register", response_model=CustomerRead, status_code=status.HTTP_201_CREATED
)
def register(data: CustomerCreate, db: DbSession):
    return customers.create_customer(db, data)


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    """Log in with **email** (as `username`) and password to get a JWT."""
    customer = customers.authenticate(db, form.username, form.password)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(customer.id)))
