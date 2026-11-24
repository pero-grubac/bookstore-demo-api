from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200, examples=["Petar Petrović"])
    password: str = Field(min_length=8, max_length=128)


class CustomerUpdate(BaseModel):
    full_name: str = Field(default=None, min_length=1, max_length=200)
    password: str = Field(default=None, min_length=8, max_length=128)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_admin: bool
    created_at: datetime
