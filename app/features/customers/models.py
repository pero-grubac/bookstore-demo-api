from datetime import datetime

from sqlalchemy import DateTime, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Customer(Base):
    """A registered user of the store. Admins manage the catalog and orders."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
