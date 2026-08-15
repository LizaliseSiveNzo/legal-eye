"""The one function that turns a paid order into a delivered report.

Kept separate from the web layer so the ordering rule is enforced in one place
and can be tested without a browser: confirm payment, then send, then record.
If sending fails the order stays PAID rather than DELIVERED, so a retry is
possible and the reader is not left having paid for nothing.
"""

from __future__ import annotations

from backend.mailer import EmailError, EmailSender, build_message
from backend.orders import Order, OrderError, OrderStore, mark_delivered, mark_failed
from backend.payments import PaymentError, PaymentProvider


def fulfil_order(
    store: OrderStore,
    order: Order,
    provider: PaymentProvider,
    sender: EmailSender,
    callback_payload: dict | None = None,
) -> Order:
    """Verify payment, email the report, and record the delivery.

    Raises rather than returning a half-finished state. The caller shows the
    message to the reader.
    """
    from backend.orders import mark_paid

    if order.status not in ("pending", "paid", "failed"):
        raise OrderError(f"Order {order.id} is already {order.status}.")

    if order.status != "paid":
        try:
            reference = provider.confirm(order, callback_payload or {})
        except PaymentError as exc:
            mark_failed(store, order.id, str(exc))
            raise
        order = mark_paid(store, order.id, provider.name, reference)

    if not order.is_deliverable():
        raise OrderError(
            "This order has no report attached, so there is nothing to send. "
            "Reports are cleared from delivered orders after the retention period."
        )

    message = build_message(
        to=order.email,
        report=order.report or "",
        document_names=order.document_names,
        risk_score=order.risk_score,
        risk_band=order.risk_band,
        order_reference=order.id[:12],
    )
    try:
        sender.send(message)
    except EmailError as exc:
        # Stay PAID, not DELIVERED. The reader has paid; a retry must remain possible.
        mark_failed(store, order.id, f"delivery failed: {exc}")
        raise

    return mark_delivered(store, order.id)
