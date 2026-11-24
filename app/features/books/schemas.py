from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.features.categories.schemas import CategoryRead

Title = Annotated[
    str, Field(min_length=1, max_length=300, examples=["Na Drini ćuprija"])
]
Isbn = Annotated[str, Field(pattern=r"^\d{10}(\d{3})?$", examples=["9788652139601"])]
Price = Annotated[
    Decimal, Field(gt=0, max_digits=10, decimal_places=2, examples=["19.99"])
]
Stock = Annotated[int, Field(ge=0)]
Year = Annotated[int, Field(ge=0, le=2100)]


class BookBase(BaseModel):
    title: Title
    isbn: Isbn
    description: str | None = None
    price: Price
    stock: Stock = 0
    published_year: Year | None = None


class BookCreate(BookBase):
    author_id: int
    category_ids: list[int] = []


class BookUpdate(BaseModel):
    # Omitted fields stay unchanged; required columns cannot be set to null.
    title: Title = None
    isbn: Isbn = None
    description: str | None = None
    price: Price = None
    stock: Stock = None
    published_year: Year | None = None
    author_id: int = None
    category_ids: list[int] = None


class AuthorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BookRead(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: AuthorSummary
    categories: list[CategoryRead]
