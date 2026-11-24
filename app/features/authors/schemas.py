from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthorBase(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Ivo Andrić"])
    bio: str | None = None


class AuthorCreate(AuthorBase):
    pass


class AuthorUpdate(BaseModel):
    # Omitted fields stay unchanged; `name` may be omitted but not set to null.
    name: str = Field(default=None, min_length=1, max_length=200)
    bio: str | None = None


class AuthorRead(AuthorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
