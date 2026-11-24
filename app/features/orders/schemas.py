from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.features.orders.models import OrderStatus


class OrderItemCreate(BaseModel):
    book_id: int
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class BookSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book: BookSummary
    quantity: int
    unit_price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    status: OrderStatus
    total: Decimal
    created_at: datetime
    items: list[OrderItemRead]
