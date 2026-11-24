from collections import Counter
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import cache
from app.core.exceptions import ConflictError, NotFoundError
from app.features.books.models import Book
from app.features.books.service import cache_key as book_cache_key
from app.features.customers.models import Customer
from app.features.orders.models import Order, OrderItem, OrderStatus
from app.features.orders.schemas import OrderCreate

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: set(),
    OrderStatus.CANCELLED: set(),
}


def list_orders(db: Session, customer: Customer, skip: int, limit: int) -> list[Order]:
    """Admins see all orders, customers only their own."""
    stmt = select(Order).order_by(Order.id.desc())
    if not customer.is_admin:
        stmt = stmt.where(Order.customer_id == customer.id)
    return list(db.scalars(stmt.offset(skip).limit(limit)))


def get_order(
    db: Session, order_id: int, customer: Customer, for_update: bool = False
) -> Order:
    order = db.get(Order, order_id, with_for_update=for_update)
    # Other customers' orders are reported as "not found" to avoid leaking ids.
    if order is None or (not customer.is_admin and order.customer_id != customer.id):
        raise NotFoundError(f"Order {order_id} not found")
    return order


def create_order(db: Session, customer: Customer, data: OrderCreate) -> Order:
    quantities: Counter[int] = Counter()
    for item in data.items:
        quantities[item.book_id] += item.quantity

    # Lock the rows so two concurrent orders cannot oversell the same book.
    stmt = (
        select(Book)
        .where(Book.id.in_(quantities))
        .order_by(Book.id)
        .with_for_update(of=Book)
    )
    books = {book.id: book for book in db.scalars(stmt)}
    missing = quantities.keys() - books.keys()
    if missing:
        raise NotFoundError(f"Books not found: {sorted(missing)}")

    order = Order(customer_id=customer.id, total=Decimal("0"))
    for book_id, quantity in quantities.items():
        book = books[book_id]
        if book.stock < quantity:
            raise ConflictError(
                f"Not enough stock for '{book.title}' (available: {book.stock})"
            )
        book.stock -= quantity
        order.items.append(
            OrderItem(book_id=book_id, quantity=quantity, unit_price=book.price)
        )
        order.total += book.price * quantity

    db.add(order)
    db.commit()
    db.refresh(order)
    cache.delete(*(book_cache_key(book_id) for book_id in quantities))
    return order


def change_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise ConflictError(
            f"Cannot change order status from '{order.status}' to '{new_status}'"
        )
    if new_status == OrderStatus.CANCELLED:
        for item in order.items:
            db.execute(
                update(Book)
                .where(Book.id == item.book_id)
                .values(stock=Book.stock + item.quantity)
            )
    order.status = new_status
    db.commit()
    db.refresh(order)
    if new_status == OrderStatus.CANCELLED:
        cache.delete(*(book_cache_key(item.book_id) for item in order.items))
    return order


def cancel_order(db: Session, order_id: int, customer: Customer) -> Order:
    order = get_order(db, order_id, customer, for_update=True)
    if not customer.is_admin and order.status != OrderStatus.PENDING:
        raise ConflictError("Only pending orders can be cancelled")
    return change_status(db, order, OrderStatus.CANCELLED)
