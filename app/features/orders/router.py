import logging

from fastapi import APIRouter, status
from kombu.exceptions import OperationalError

from app.core.database import DbSession
from app.core.pagination import Limit, Skip
from app.features.auth.dependencies import AdminUser, CurrentCustomer
from app.features.orders import service
from app.features.orders.schemas import OrderCreate, OrderRead, OrderStatusUpdate
from app.features.orders.tasks import send_order_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=list[OrderRead])
def list_orders(
    db: DbSession, customer: CurrentCustomer, skip: Skip = 0, limit: Limit = 20
):
    """Your orders (admins see all orders)."""
    return service.list_orders(db, customer, skip, limit)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: DbSession, customer: CurrentCustomer):
    return service.get_order(db, order_id, customer)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: DbSession, customer: CurrentCustomer):
    """Place an order. Prices are taken from the catalog and stock is reserved.

    The confirmation email is sent in the background by the Celery worker.
    """
    order = service.create_order(db, customer, data)
    try:
        send_order_confirmation.delay(order.id)
    except OperationalError:
        # The order is already saved; a missing email must not fail the request.
        logger.exception("Could not queue confirmation email for order %s", order.id)
    return order


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(order_id: int, db: DbSession, customer: CurrentCustomer):
    """Cancel a pending order and return its items to stock."""
    return service.cancel_order(db, order_id, customer)


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_status(
    order_id: int, data: OrderStatusUpdate, db: DbSession, admin: AdminUser
):
    """Move an order through `pending → paid → shipped` (or cancel it)."""
    order = service.get_order(db, order_id, admin, for_update=True)
    return service.change_status(db, order, data.status)
