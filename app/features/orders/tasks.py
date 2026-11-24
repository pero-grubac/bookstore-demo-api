import logging
import smtplib
from html import escape

from app.core.database import SessionLocal
from app.core.email import send_email
from app.features.customers.models import Customer
from app.features.orders.models import Order
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    max_retries=3,
)
def send_order_confirmation(order_id: int) -> None:
    """Email the customer a summary of their new order."""
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        if order is None:
            logger.warning("Order %s not found, confirmation not sent", order_id)
            return
        customer = db.get(Customer, order.customer_id)
        subject, text, html = render_confirmation(order, customer)

    send_email(customer.email, subject, text, html)
    logger.info("Sent confirmation for order %s to %s", order_id, customer.email)


def render_confirmation(order: Order, customer: Customer) -> tuple[str, str, str]:
    """Return (subject, plain-text body, HTML body)."""
    subject = f"Order #{order.id} confirmed"
    rows = [
        (
            item.book.title,
            item.quantity,
            item.unit_price,
            item.unit_price * item.quantity,
        )
        for item in order.items
    ]

    text_lines = [
        f"Hi {customer.full_name},",
        "",
        f"Thank you for your order! Here is a summary of order #{order.id}:",
        "",
        *(
            f"  {qty} x {title}  @ {price}  = {subtotal}"
            for title, qty, price, subtotal in rows
        ),
        "",
        f"Total: {order.total}",
        f"Status: {order.status}",
        "",
        "We will let you know when it ships.",
        "Bookstore",
    ]

    cell = 'style="padding:6px 12px;border-bottom:1px solid #eee"'
    html_rows = "".join(
        f"<tr><td {cell}>{escape(title)}</td>"
        f"<td {cell} align='center'>{qty}</td>"
        f"<td {cell} align='right'>{price}</td>"
        f"<td {cell} align='right'>{subtotal}</td></tr>"
        for title, qty, price, subtotal in rows
    )
    html = f"""\
<div style="font-family:Arial,sans-serif;color:#222;max-width:560px">
  <h2 style="margin-bottom:4px">Thank you for your order!</h2>
  <p>Hi {escape(customer.full_name)}, we have received order
     <b>#{order.id}</b> (status: {order.status}).</p>
  <table style="border-collapse:collapse;width:100%">
    <tr style="background:#f5f5f5;text-align:left">
      <th {cell}>Book</th><th {cell}>Qty</th>
      <th {cell} align='right'>Price</th><th {cell} align='right'>Subtotal</th>
    </tr>
    {html_rows}
    <tr><td colspan="3" align="right" style="padding:8px 12px"><b>Total</b></td>
        <td align="right" style="padding:8px 12px"><b>{order.total}</b></td></tr>
  </table>
  <p>We will let you know when it ships.<br>Bookstore</p>
</div>"""
    return subject, "\n".join(text_lines), html
