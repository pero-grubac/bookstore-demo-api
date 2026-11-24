from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Numeric, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.features.authors.models import Author
from app.features.categories.models import Category

book_categories = Table(
    "book_categories",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "category_id",
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(default=0)
    published_year: Mapped[int | None]
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="RESTRICT"), index=True
    )

    author: Mapped[Author] = relationship(lazy="joined")
    categories: Mapped[list[Category]] = relationship(
        secondary=book_categories, lazy="selectin", order_by=Category.name
    )
